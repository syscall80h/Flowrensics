"""
hayabusa_executor.py
================
Background runner for hayabusa.
"""
from __future__ import annotations
import threading
import subprocess
import zipfile
import urllib.error
import urllib.request
import re
from datetime import datetime
from pathlib import Path
from os import environ, fspath

# ─── GUI ──────────────────────────────────────────────────────────────────
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

# ─── local imports ────────────────────────────────────────────────────────
from logger_config import setup_logger
from utils import check_hayabusa_tool_dir, check_hayabusa_output_dir

# ─── logging ──────────────────────────────────────────────────────────────
logger = setup_logger()

# ─── Constants ────────────────────────────────────────────────────────────
ANSI_RE = re.compile(r'(?:\x9B|\x1B\[)[0-?]*[ -/]*[@-~]') 
PCT_RE = re.compile(r'(\\d{1,3})%') 


class HayabusaExecutor:
    """Download (if needed) and run Hayabusa with a live output window."""

    def __init__(self, parent: ctk.CTk, triage_dir: str | Path) -> None:
        self.parent = parent
        self.triage_dir: Path = Path(triage_dir)

        # GUI widgets created in _create_dialog()
        self._dlg: ctk.CTkToplevel | None = None
        self._bar: ctk.CTkProgressBar | None = None
        self._status: ctk.CTkLabel | None = None
        self._outbox: ctk.CTkTextbox | None = None  

        # UTF‑8 environment to prevent cp‑1252 decode errors
        self.env = environ.copy()
        self.env["PYTHONIOENCODING"] = "utf-8"
        self.env["PYTHONUTF8"] = "1"

    # ─── public API ────────────────────────────────────────────────────────
    def start(self) -> None:
        """Starts create_dialog and _run function"""
        self._create_dialog()
        threading.Thread(target=self._run, daemon=True).start()

    # ─── GUI creation ──────────────────────────────────────────────────────
    def _create_dialog(self) -> None:
        self._dlg = ctk.CTkToplevel(self.parent)
        self._dlg.title("Hayabusa")
        self._dlg.geometry("1200x600")
        self._dlg.wm_attributes("-topmost", 1)

        self._bar = ctk.CTkProgressBar(self._dlg, mode="determinate")
        self._bar.pack(fill="x", padx=20, pady=10)
        self._bar.set(0.0)

        self._status = ctk.CTkLabel(self._dlg, text="Running …", anchor="w")
        self._status.pack(fill="x", padx=20)

        # scrollable output widget
        self._outbox = ctk.CTkTextbox(self._dlg, height=400, state="disabled")
        self._outbox.pack(fill="both", expand=True, padx=20, pady=10)

    # ─── thread‑safe helpers ───────────────────────────────────────────────
    def _safe_status(self, text: str) -> None:
        if self._status:
            self._status.after(0, lambda: self._status.configure(text=text))

    def _safe_append(self, line: str) -> None:
        if self._outbox:
            def _append() -> None:
                self._outbox.configure(state="normal")
                self._outbox.insert("end", line + "\n")
                self._outbox.yview_moveto(1.0)
                self._outbox.configure(state="disabled")
            self._outbox.after(0, _append)

    def _safe_set_bar(self, value: float) -> None:
        if self._bar:
            self._bar.after(0, self._bar.set, value)

    # ─── worker thread ─────────────────────────────────────────────────────
    def _run(self) -> None:
        hayabusa_dir: Path = check_hayabusa_tool_dir()
        self.hayabusa_exe = hayabusa_dir / "hayabusa-3.2.0-win-x64.exe"

        # ensure the binary exists
        if not self.hayabusa_exe.exists():
            logger.warning("[Flowrensics] Hayabusa executable not found.")
            if CTkMessagebox(
                title="Hayabusa",
                message="Executable not found - download now?",
                icon="warning",
                option_1="Yes",
                option_2="No",
                master=self._dlg,
            ).get() == "Yes":
                self._install(hayabusa_dir)
            else:
                self._dlg.destroy()
                return

        cmd = self._build_command()
        logger.info("[Flowrensics] Launching: %s", " ".join(map(fspath, cmd)))
        self._safe_status("Hayabusa is starting …")

        try:
            self._bar.after(0, lambda: (
                self._bar.configure(mode="indeterminate"),
                self._bar.start()
            ))
            with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=self.env,
        bufsize=0,
        text=True,
        encoding="utf-8",
        errors="replace",
            ) as proc:
                buf = []
                while True:
                    ch = proc.stdout.read(1)
                    if not ch:
                        if buf:
                            self._safe_append(ANSI_RE.sub("", "".join(buf)))
                        break

                    if ch in ("\r", "\n"):
                        clean = ANSI_RE.sub("", "".join(buf)).strip()
                        if clean:
                            self._safe_append(clean)
                        buf.clear()
                    else:
                        buf.append(ch)

                if proc.wait() != 0:
                    raise subprocess.CalledProcessError(proc.returncode, cmd)

            # success ----------------------------------------------------------------
            self._safe_set_bar(1.0)
            self._safe_status("Hayabusa finished ✔")
            logger.info("[Flowrensics] Hayabusa completed successfully.")
            CTkMessagebox(
                title="Hayabusa",
                message="Hayabusa completed successfully.\n"
                        "Results saved in Output\\Hayabusa",
                icon="info",
                option_1="Ok",
                master=self.parent,
            )

        # error handling -------------------------------------------------------------
        except subprocess.CalledProcessError as exc:
            logger.error("[Flowrensics] Command failed: %s", exc)
            self._safe_status(f"ERROR - {exc}")
            self._safe_append(f"ERROR - {exc}")
            CTkMessagebox(
                title="Hayabusa - Error",
                message=f"Hayabusa failed:\n{exc}",
                icon="warning",
                option_1="Ok",
                master=self.parent,
            )

        finally:
            if self._bar:
                self._bar.stop()                       
                self._bar.configure(mode="determinate")
                self._bar.set(1.0)   
                self._safe_status("Terminated.")                  
            if self._dlg:
                #self._dlg.after(1000, self._dlg.destroy)
                logger.info("[Flowrensics] End of hayabusa")
            

    # ─── auxiliary methods ─────────────────────────────────────────────────
    def _install(self, hayabusa_dir: Path) -> None:
        """Download and unzip Hayabusa; show progress in the dialog."""
        url = (
            "https://github.com/Yamato-Security/hayabusa/releases/download/"
            "v3.2.0/hayabusa-3.2.0-win-x64.zip"
        )
        zip_path = hayabusa_dir / url.split("/")[-1]

        try:
            self._safe_status("Downloading Hayabusa…")
            logger.info("[Flowrensics] Downloading Hayabusa.")
            urllib.request.urlretrieve(url, zip_path)

            self._safe_status("Extracting Hayabusa…")
            logger.info("[Flowrensics] Extracting ZIP file.")
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(hayabusa_dir)

            CTkMessagebox(
                title="Hayabusa",
                message="Hayabusa downloaded and extracted.",
                icon="info",
                option_1="Ok",
                master=self._dlg,
            )

        except (urllib.error.HTTPError, urllib.error.URLError, zipfile.BadZipFile) as exc:
            logger.error("[Flowrensics] Hayabusa download failed: %s", exc)
            CTkMessagebox(
                title="Hayabusa - Error",
                message=f"Download failed:\n{exc}",
                icon="warning",
                option_1="Ok",
                master=self._dlg,
            )

    def _build_log_path(self) -> Path:
        """Return the path of windows logs"""
        return Path(self.triage_dir) / "Windows" / "System32" / "winevt" / "logs"

    def _build_command(self) -> list[str]:
        """Build Hayabusa cmdline"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return [
            str(self.hayabusa_exe),
            "csv-timeline",
            "-d", str(self._build_log_path()),
            "--no-color",
            "--no-wizard",
            "-o", str(Path(check_hayabusa_output_dir()) / f"hayabusa_{timestamp}.csv"),
        ]
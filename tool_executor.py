"""
tool_executor.py
================
Background runner for EZ-Tools.
"""
# for python < 3.10
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import Final

# ─── GUI ──────────────────────────────────────────────────────────────────
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox

# ─── local imports ────────────────────────────────────────────────────────
from logger_config import setup_logger
from utils import (
    check_output_dir,
    check_registry_dir,
    check_shellbag_dir,
    check_userassist_dir,
    list_user_directories,
)

# ─── logging ──────────────────────────────────────────────────────────────
logger = setup_logger()

# ─── Constants ────────────────────────────────────────────────────────────
OUTPUT_DIR: Final[Path] = Path("Output")
OUTPUT_USERASSIST: Final[Path] = OUTPUT_DIR / "UserAssist"
OUTPUT_REGISTRY: Final[Path] = OUTPUT_DIR / "Registry"
OUTPUT_SHELLBAG: Final[Path] = OUTPUT_DIR / "ShellBag"


# ─── main application class ───────────────────────────────────────────────
class ToolExecutor:
    """Run selected EZ-Tools in a background thread."""
    def __init__(
        self,
        parent: ctk.CTk,
        tools: list[str],
        directory: str | Path,
        triage_dir: str | Path,
    ) -> None:
        self.parent: ctk.CTk = parent
        self.tools: list[str] = tools
        self.directory: Path = Path(directory)
        self.triage_dir: Path = Path(triage_dir)

        # GUI elements (created in _create_dialog)
        self._dlg: ctk.CTkToplevel | None = None
        self._bar: ctk.CTkProgressBar | None = None
        self._status: ctk.CTkLabel | None = None
        self._outbox: ctk.CTkTextbox | None = None   # ← NEW

        # internal state
        self._commands: list[list[str]] = []
        self._total_steps: int = 0
        self._current_step: int = 0

    # ─── public API ───────────────────────────────────────────────────────────
    def start(self) -> None:
        """Spawn the progress window and run tools in a background thread."""
        self._create_dialog()
        threading.Thread(target=self._run, daemon=True).start()

    # ─── GUI helpers ──────────────────────────────────────────────────────────
    def _create_dialog(self) -> None:
        """Build a non-blocking modal window with progress bar + output panel."""
        self._dlg = ctk.CTkToplevel(self.parent)
        self._dlg.title("Tool execution")
        self._dlg.geometry("1200x600")
        self._dlg.wm_attributes("-topmost", 1)

        # top progress bar
        self._bar = ctk.CTkProgressBar(self._dlg, mode="determinate")
        self._bar.pack(fill="x", padx=20, pady=10)
        self._bar.set(0.0)

        # single‑line status
        self._status = ctk.CTkLabel(self._dlg, text="Preparing …", anchor="w")
        self._status.pack(fill="x", padx=20)

        # multi‑line scrolling output box
        self._outbox = ctk.CTkTextbox(self._dlg, height=400, state="disabled")
        self._outbox.pack(fill="both", expand=True, padx=20, pady=10)

    # ─── thread‑safe updaters ───────────────────────────────────────────────────
    def _safe_status(self, text: str) -> None:
        """Update the label status"""
        if self._status:
            self._status.after(0, lambda: self._status.configure(text=text))

    def _safe_progress(self) -> None:
        """Update the progress bar"""
        if self._bar and self._total_steps:
            self._current_step += 1
            frac = self._current_step / self._total_steps
            self._bar.after(0, self._bar.set, frac)

    def _safe_append(self, line: str) -> None:
        """Append one line to the textbox and auto-scroll."""
        if self._outbox:
            def _append() -> None:
                self._outbox.configure(state="normal")
                self._outbox.insert("end", line + "\n")
                self._outbox.yview_moveto(1.0)
                self._outbox.configure(state="disabled")
            self._outbox.after(0, _append)

    # ─── worker thread ────────────────────────────────────────────────────────
    def _run(self) -> None:
        """Prepare commands then execute them sequentially with live output."""
        check_output_dir()
        self._commands = self._build_commands()
        self._total_steps = len(self._commands)

        for cmd in self._commands:
            logger.info("[Flowrensics] Launching: %s", " ".join(cmd))
            self._safe_status(f"Running …  {' '.join(cmd)}")
            self._execute(cmd)
            self._safe_progress()

        self._safe_status("All tools finished ✔")
        logger.info("[Flowrensics] All tools finished ✔")
        if self._dlg:
            self._dlg.after(1000, self._dlg.destroy)

        CTkMessagebox(
            title="Flowrensics",
            message="All tools finished ✔",
            icon="info",
            option_1="Ok",
            master=self.parent,
        )

    # ─── real‑time subprocess ─────────────────────────────────────────────────
    def _execute(self, cmd: list[str]) -> None:
        """Run one CLI command and stream stdout to the textbox."""
        try:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                text=True,
            ) as proc:
                for line in proc.stdout:
                    line = line.rstrip()
                    self._safe_append(line)
                if proc.wait() != 0:
                    raise subprocess.CalledProcessError(proc.returncode, cmd)

        except subprocess.CalledProcessError as exc:
            logger.error("[Flowrensics] Command failed: %s", exc)
            self._safe_status(f"ERROR: {exc!s}")
            self._safe_append(f"ERROR: {exc!s}")
            CTkMessagebox(
                title="Tool execution - Error",
                message=f"Command failed:\n{exc}",
                icon="warning",
                option_1="Ok",
                master=self.parent,
            )
        

    # ─── commands build ───────────────────────────────────────────────────────
    def _build_commands(self) -> list[list[str]]:
        """Translate the selected tool names into subprocess command lists."""
        root = self.triage_dir
        users = list_user_directories(root / "Users")

        # Ensure sub‑folders exist
        check_registry_dir()
        check_userassist_dir()
        check_shellbag_dir()

        build = {
            "AmcacheParser.exe": lambda: [
                [
                    self.directory / "AmcacheParser.exe",
                    "-f",
                    root / "Windows" / "AppCompat" / "Programs" / "Amcache.hve",
                    "--csv",
                    OUTPUT_DIR,
                    "--csvf",
                    "amcache_parsed.csv",
                ]
            ],
            "AppCompatCacheParser.exe": lambda: [
                [
                    self.directory / "AppCompatCacheParser.exe",
                    "-f",
                    root / "Windows" / "System32" / "config" / "SYSTEM",
                    "--csv",
                    OUTPUT_DIR,
                    "--csvf",
                    "shimcache_parsed.csv",
                ]
            ],
            "EvtxECmd\\EvtxECmd.exe": lambda: [
                [
                    self.directory / "EvtxECmd" / "EvtxECmd.exe",
                    "-d",
                    root / "Windows" / "System32" / "winevt" / "logs",
                    "--csv",
                    OUTPUT_DIR,
                    "--csvf",
                    "evtx_parsed.csv",
                    "--inc",
                    (
                        "4624,4625,4634,4647,4672,4676,4648,1024,1102,4778,4779,131,"
                        "98,1149,21,22,25,41,4768,4769,5140,5145,7045,4698,4702,4699,"
                        "4700,4701,106,140,141,200,201,7034,7035,7036,7040,5857,5860,"
                        "5861,4103,4104,53504,400,401,402,403,800,91,142,169"
                    ),
                ]
            ],
            "JLECmd.exe": lambda: [
                [
                    self.directory / "JLECmd.exe",
                    "-d",
                    root
                    / "Users"
                    / user
                    / "AppData"
                    / "Roaming"
                    / "Microsoft"
                    / "Windows"
                    / "Recent"
                    / "AutomaticDestinations",
                    "--csv",
                    OUTPUT_DIR,
                    "--csvf",
                    f"jumplist_{user}_parsed.csv",
                    "-q",
                ]
                for user in users
            ],
            "LECmd.exe": lambda: [
                [
                    self.directory / "LECmd.exe",
                    "-d",
                    root
                    / "Users"
                    / user
                    / "AppData"
                    / "Roaming"
                    / "Microsoft"
                    / "Windows"
                    / "Recent",
                    "--csv",
                    OUTPUT_DIR,
                    "--csvf",
                    f"lnk_{user}_parsed.csv",
                    "-q",
                ]
                for user in users
            ],
            "MFTECmd.exe": lambda: [
                [
                    self.directory / "MFTECmd.exe",
                    "-f",
                    root / "$MFT",
                    "--csv",
                    OUTPUT_DIR,
                    "--csvf",
                    "mft_parsed.csv",
                ],
                [
                    self.directory / "MFTECmd.exe",
                    "-f",
                    root / "$Extend" / "$J",
                    "-m",
                    root / "$MFT",
                    "--csv",
                    OUTPUT_DIR,
                    "--csvf",
                    "usn_parsed.csv",
                ],
            ],
            "PECmd.exe": lambda: [
                [
                    self.directory / "PECmd.exe",
                    "-d",
                    root / "Windows" / "prefetch",
                    "--csv",
                    OUTPUT_DIR,
                    "--csvf",
                    "prefetch_parsed.csv",
                    "-q",
                    "--vss",
                ]
            ],
            "RECmd\\RECmd.exe": lambda: [
                [
                    self.directory / "RECmd" / "RECmd.exe",
                    "-f",
                    root / "Users" / user / "NTUSER.DAT",
                    "--bn",
                    self.directory
                    / "RECmd"
                    / "BatchExamples"
                    / "BatchExampleUserAssist.reb",
                    "--csv",
                    OUTPUT_USERASSIST,
                    "--csvf",
                    f"userassist_{user}.csv",
                    "--nl",
                ]
                for user in users
            ]
            + [
                [
                    self.directory / "RECmd" / "RECmd.exe",
                    "-d",
                    root,
                    "--bn",
                    self.directory / "RECmd" / "BatchExamples" / "DFIRBatch.reb",
                    "--csv",
                    OUTPUT_REGISTRY,
                    "--nl",
                ]
            ],
            "SBECmd.exe": lambda: [
                [
                    self.directory / "SBECmd.exe",
                    "-d",
                    root / "Users" / user,
                    "--csv",
                    OUTPUT_SHELLBAG,
                ]
                for user in users
            ],
        }

        commands: list[list[str]] = []
        for tool in self.tools:
            builder = build.get(tool)
            if builder:
                commands.extend(builder())
            else:
                logger.warning("[Flowrensics] Unknown tool selected: %s", tool)
        return [[str(x) for x in cmd] for cmd in commands]
    

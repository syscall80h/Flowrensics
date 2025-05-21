"""
volatility_executor.py
================
Background runner for volatility.
"""
import subprocess
import threading
import queue
import urllib.request
from pathlib import Path
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
import os

# ─── local imports ────────────────────────────────────────────────────────
from utils import find_venv_folder
from logger_config import setup_logger

# ─── logging ──────────────────────────────────────────────────────────────
logger = setup_logger()

# ─── main application class ───────────────────────────────────────────────
class VolatilityRunner:
    """Run Volatility plugins"""
    def __init__(self, parent, mem_path: str, os_type: str = "windows") -> None:
        self.parent: ctk.CTk = parent  # CTk root
        self.mem_path: Path = Path(mem_path)
        self.os_type: str = os_type.lower()
        self.venv_path: Path = find_venv_folder()  # ./venv or ./.venv
        self.vol_exe: Path = Path(self.venv_path) / "Scripts" / "vol.exe"

        self.queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.PLUGINS: dict[str, str] = {
            "Pstree": [str(self.vol_exe),"-f",self.mem_path,"-r", "pretty", f"{self.os_type}.pstree"],
            "Pslist": [str(self.vol_exe),"-f",self.mem_path,"-r", "csv", f"{self.os_type}.pslist"],
            "Psscan": [str(self.vol_exe),"-f",self.mem_path,"-r", "csv", f"{self.os_type}.psscan"],
            "Netscan": [str(self.vol_exe),"-f",self.mem_path,"-r", "csv", f"{self.os_type}.netscan"],
            "Cmdline": [str(self.vol_exe),"-f",self.mem_path,"-r", "csv", f"{self.os_type}.cmdline"],
            "Getsids": [str(self.vol_exe),"-f",self.mem_path,"-r", "csv", f"{self.os_type}.getsids"],
            "Malfind": [str(self.vol_exe),"-f",self.mem_path,"-r", "csv", f"{self.os_type}.malfind"],
            "Ldrmodules": [str(self.vol_exe),"-f",self.mem_path,"-r", "csv", f"{self.os_type}.ldrmodules"],
            "Ssdt": [str(self.vol_exe),"-f",self.mem_path,"-r", "csv", f"{self.os_type}.ssdt"]
        }
        
        self.total_jobs = len(self.PLUGINS)
        self.status: dict[str, str] = {}

        # for non-unicode char
        self.env = os.environ.copy()                 
        self.env["PYTHONIOENCODING"] = "utf-8"       
        self.env["PYTHONUTF8"]       = "1"

        self.plugin_error: list[str] = []

    # ─────────────────────────────────────────────────────── installation V3
    def _install(self) -> None:
        scripts: Path = Path(self.venv_path) / "Scripts"
        if not scripts.is_dir():
            CTkMessagebox(title="Venv missing", message="Please create a working python venv.",
                  icon="warning", option_1="Ok")
            logger.warning("[Flowrensics] Venv is missing. Please create a working python venv.")
            return
        wheel_url: str = (
            "https://github.com/volatilityfoundation/volatility3/releases/download/v2.11.0/"
            "volatility3-2.11.0-py3-none-any.whl"
        )
        wheel = Path.cwd() / wheel_url.split("/")[-1]
        if not wheel.is_file():
            urllib.request.urlretrieve(wheel_url, wheel)
        pip_exe = scripts / "pip.exe"
        try:
            subprocess.check_call([str(pip_exe), "install", str(wheel)])
            logger.info("[Flowrensics] Volatility 3 has been installed.")
            CTkMessagebox(title="Venv install", message="Volatility 3 has been installed.",
                  icon="info", option_1="Ok")
        except subprocess.CalledProcessError as err:
            logger.warning("[Flowrensics] Installation of Volatility 3 has failed.")
            CTkMessagebox(title="Venv failed install", message="Installation of Volatility 3 has failed.",
                  icon="warning", option_1="Ok")

    # ─────────────────────────────────────────────────────────────── dialogue
    def _make_dialog(self) -> None:
        """Create the top level dialog"""
        dlg = ctk.CTkToplevel(self.parent)
        dlg.title("Volatility starts...")
        dlg.geometry("900x200")
        dlg.resizable(True, True)
        dlg.wm_attributes("-topmost", 1)
        #dlg.grab_set()

        self.pb = ctk.CTkProgressBar(dlg, mode="determinate")
        self.pb.pack(fill="x", padx=20, pady=20)
        self.pb.set(0)

        self.lbl = ctk.CTkLabel(dlg, text="Waiting…", anchor="w", justify="left")
        self.lbl.pack(fill="both", expand=True, padx=20)

        self.dlg = dlg
    
    def _is_symbole(self) -> bool:
        """Check if symboles are in the table, if not -> abandon"""
        logger.info("[Flowrensics] Starting image info for symboles.")
        try:
            subprocess.run(
                [
                    self.vol_exe,
                    "-f",
                    self.mem_path,
                    f"{self.os_type}.info"
                ],
                check=True
            )
            return True # The symboles are in the table
        except subprocess.CalledProcessError as exc:
            logger.warning(f"[Flowrensics] Error no symbole table for this image : {exc}")
            return False

    # ─────────────────────────────────────────────────────────── worker thread
    def _worker(self, plugin: str, cmd: list[str], out_file: Path) -> None:
        """Executes a plugin and updates GUI."""
        
        self.queue.put((plugin, "start"))
        try:
            logger.info(f"[Flowrensics] Start of plugin {plugin}")
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                env=self.env 
            ) as proc:
                out, err = proc.communicate()
                
                if proc.returncode != 0:
                    logger.warning(f"[Flowrensics] Error while executing {plugin} : {err}")
                    raise subprocess.CalledProcessError(proc.returncode, cmd, out, err)
                    
            
            out_file.write_text(out, encoding="utf-8")
            self.queue.put((plugin, "ok"))
            logger.info(f"[Flowrensics] {plugin} has terminated")
            self._poll_queue()
        except subprocess.CalledProcessError as err:
            self.queue.put((plugin, f"error: {err.stderr[:120]}…"))
            self.plugin_error.append(plugin)

    # ────────────────────────────────────────────────────────────── queue poll
    def _poll_queue(self) -> None:
        """Handle queue"""
        try:
            while True:
                plugin, status = self.queue.get_nowait()
                self.status[plugin] = status

                finished = sum(1 for s in self.status.values() if s in ("ok",) or s.startswith("error"))
                self.pb.set(finished / self.total_jobs)

                running = [p for p, s in self.status.items() if s == "start"]
                msg = [f"Running : {', '.join(running) if running else '-'}",
                       f"Terminated : {finished}/{self.total_jobs}"]
                self.lbl.configure(text="\n".join(msg))

                if finished == self.total_jobs:
                    if len(self.plugin_error) == 0:
                        self.lbl.configure(text="All plugins finished ✔")
                        CTkMessagebox(title="Flowrensics", message="All plugins finished ✔",
                                icon="info", option_1="Ok")
                    else:
                        error_plugins = ", ".join(self.plugin_error)
                        self.lbl.configure(text=f"{len(self.plugin_error)}/{len(self.PLUGINS)} error(s): {error_plugins}")
                        CTkMessagebox(title="Flowrensics", message=f"{len(self.plugin_error)}/{len(self.PLUGINS)}" 
                                      f" error(s): {error_plugins} see logs for more information.",
                                icon="info", option_1="Ok") 
                    self.dlg.grab_release()
                    self.dlg.destroy()
                    logger.info("[Flowrensics] All plugins finished ✔")
                    
        except queue.Empty:
            pass

        if len(self.status) < self.total_jobs:
            self.parent.after(200, self._poll_queue)

    # ─────────────────────────────────────────────────── helper lancement plugin
    def _start_plugin_thread(self, plugin: str) -> None:
        """Forges the cmdline and starts the plugin"""
        is_tree = "pstree" in plugin.lower()

        out_dir = Path("Output") / "volatility"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{plugin}.{ 'txt' if is_tree else 'csv'}"
        cmd = self.PLUGINS[plugin]

        threading.Thread(target=self._worker, args=(plugin, cmd, out_file), daemon=True).start()

    # ─────────────────────────────────────────────────────────────────── run
    def run(self) -> None:
        """Verify setup and starts thread"""
        if not self.venv_path or not Path(self.venv_path).is_dir():
            logger.warning("[Flowrensics] Venv not found.")
            CTkMessagebox(title="Venv not found", message="Python venv not found.",
                  icon="warning", option_1="Ok")
            return

        if not self.vol_exe.is_file():
            logger.warning("[Flowrensics] Volatility not found.")
            logger.info("[Flowrensics] Execution of self.install().")
            self._install()
            if not self.vol_exe.is_file():
                return

        # Create dialog
        self._make_dialog()
        
        if not self._is_symbole():
            self.dlg.grab_release()
            self.dlg.destroy()
            CTkMessagebox(title="Flowrensics", message="Error no symbole table for this image.",
                                icon="warning", option_1="Ok")
            return
        
        logger.info("[Flowrensics] End of image info.")
        
        for plugin in self.PLUGINS:
            self._start_plugin_thread(plugin)

        self.parent.after(200, self._poll_queue)

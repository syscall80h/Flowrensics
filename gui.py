"""
flowrensics_gui.py
==================
GUI front─end for Flowrensics.
"""
# for python < 3.10
from __future__ import annotations

from pathlib import Path
from typing import Final

# ─── GUI ──────────────────────────────────────────────────────────────────
import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from tkinter import filedialog
from CTkToolTip import CTkToolTip

# ─── third‑party / local imports ──────────────────────────────────────────
from logger_config import setup_logger
from utils import check_output_dir
from tool_executor import ToolExecutor
from hayabusa_executor import HayabusaExecutor
from volatility_executor import VolatilityRunner
from tool_descriptions import TOOL_DESCRIPTIONS

# ─── module‑level constants ───────────────────────────────────────────────
APP_TITLE: Final = "Flowrensics"
APP_VERSION: Final = "v1.0.0"
THEME_FILE: Final = Path("themes") / "silveros.json"
WINDOW_SIZE: Final = "1200x800"

ALERTS: Final[dict[str, str]] = {
    "missing_params": "Please fill out every required field.",
}

# ─── logging ───────────────────────────────────────────────────────────────
logger = setup_logger()

# ─── helper functions ──────────────────────────────────────────────────────
def get_ez_tools() -> list[str]:
    """Return the list of expected EZ─Tools executable names."""
    return list(TOOL_DESCRIPTIONS.keys())


def is_tool_present(directory: Path, tool_name: str) -> bool:
    """Check whether tool_name exists inside directory."""
    return (directory / tool_name).is_file()


# ─── main application class ───────────────────────────────────────────────
class FlowrensicsApp(ctk.CTk):
    """Dark─themed CustomTkinter GUI that orchestrates EZ─Tools & Volatility."""

    # ─── initialisation ────────────────────────────────────────────────────
    def __init__(self) -> None:
        super().__init__()

        logger.info("[Flowrensics] Initialisation...")

        # Initialise theme
        self._configure_appearance()

        # Verify the existence of Output dir
        check_output_dir()

        # ─── window meta ────────────────────────────────────────────────────
        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.resizable(True, True)

        # ─── instance attributes ───────────────────────────────────────────
        self.ez_tools: list[str] = get_ez_tools()
        self.checkbox_vars: dict[str, ctk.BooleanVar] = {}

        # ─── layout weight ──────────────────────────────────────────────────
        self.grid_columnconfigure((0, 1), weight=1)

        # ─── UI build ───────────────────────────────────────────────────────
        self._build_header()
        self._build_tool_section()
        self._build_memory_section()

        logger.info("[Flowrensics] GUI operational.")

    # ─── appearance ────────────────────────────────────────────────────────
    def _configure_appearance(self) -> None:
        """Initialise dark mode and colour theme."""
        ctk.set_appearance_mode("Dark")
        try:
            ctk.set_default_color_theme(str(THEME_FILE))
        except FileNotFoundError:
            logger.warning(f"[Flowrensics] Theme {THEME_FILE} not found; using built-in default")

    # ─── header ────────────────────────────────────────────────────────────
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(0, weight=2)
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text=f"{APP_TITLE} - Automate Windows-forensics artefact analysis",
            font=("Arial", 28, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=20)

        ctk.CTkLabel(
            header, text=APP_VERSION, font=("Arial", 16), anchor="e"
        ).grid(row=0, column=1, sticky="ew", padx=20)

    # ─── EZ‑Tools section ───────────────────────────────────────────────────
    def _build_tool_section(self) -> None:
        # left = EZ‑Tools; right = triage dir
        left = ctk.CTkFrame(self)
        right = ctk.CTkFrame(self)
        left.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        right.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")

        # ─── ez path chooser ────────────────────────────────────────────────
        ez_path_frame = ctk.CTkFrame(left)
        ez_path_frame.pack(padx=10, pady=10, fill="x")

        self.entry_ez_dir = ctk.CTkEntry(
            ez_path_frame, placeholder_text="Select EZ─Tools directory"
        )
        self.entry_ez_dir.pack(side="left", expand=True, fill="x", padx=(0, 10))
        ctk.CTkButton(
            ez_path_frame, text="Browse…", command=self._choose_ez_directory
        ).pack(side="left")

        # ─── checkboxes ─────────────────────────────────────────────────────
        self.chk_parent = ctk.CTkFrame(left)
        self.chk_parent.pack(padx=10, pady=10, fill="both", expand=True)

        # “Select All”
        self.var_select_all = ctk.BooleanVar(value=False)
        self.chk_select_all = ctk.CTkCheckBox(
            self.chk_parent,
            text="Select All",
            variable=self.var_select_all,
            command=self._toggle_all_tools,
        )
        self.chk_select_all.pack(anchor="w", padx=10, pady=(10, 10))

        # ─── path triage dir chooser ──────────────────────────────────────────
        triage_path_frame = ctk.CTkFrame(right)
        triage_path_frame.pack(padx=10, pady=10, fill="x")

        self.entry_triage_dir = ctk.CTkEntry(
            triage_path_frame, placeholder_text="Select triage directory (letter sector)"
        )
        self.entry_triage_dir.pack(side="left", expand=True, fill="x", padx=(0, 10))
        ctk.CTkButton(
            triage_path_frame, text="Browse…", command=self._choose_triage_directory
        ).pack(side="left")

        # ─── checkboxes «forensic tools» ─────────────────────────────────────────
        check_frame = ctk.CTkFrame(right)         
        check_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            check_frame,
            text="Select more tools (can be time-consuming):",
            ).pack(anchor="w", padx=10, pady=(10, 10))

        self.var_select_hayabusa = ctk.BooleanVar(value=False)
        self.chk_select_hayabusa = ctk.CTkCheckBox(
            check_frame,
            text="Hayabusa",
            variable=self.var_select_hayabusa,
        )
        self.chk_select_hayabusa.pack(side="left", padx=(75, 0), pady=(0,15))

        self.var_select_plaso = ctk.BooleanVar(value=False)
        self.chk_select_plaso = ctk.CTkCheckBox(
            check_frame,
            text="Plaso",
            variable=self.var_select_plaso,
        )
        self.chk_select_plaso.pack(side="right", padx=(0,75), pady=(0,15))
        

        # ─── main‑action button ────────────────────────────────────────────
        self.btn_run_tools = ctk.CTkButton(
            self,
            text="Run selected tools",
            command=self._run_selected_tools,
            state="disabled",
            fg_color="#262626",
        )
        self.btn_run_tools.grid(row=2, column=1, pady=(0, 20))

    # ─── memory section (Volatility) ──────────────────────────────────────
    def _build_memory_section(self) -> None:
        mem = ctk.CTkFrame(self)
        mem.grid(row=3, column=0, columnspan=2, padx=20, pady=20, sticky="nsew")
        mem.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(mem, text="Memory analysis", font=("Arial", 28)).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(10, 0)
        )

        row = ctk.CTkFrame(mem)
        row.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        row.grid_columnconfigure((0, 1, 2), weight=1)

        # dump file picker
        file_frame = ctk.CTkFrame(row)
        file_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry_mem = ctk.CTkEntry(
            file_frame, placeholder_text="Select .dump/.mem/.img/.raw file"
        )
        self.entry_mem.pack(side="left", expand=True, fill="x", padx=(0, 10))
        ctk.CTkButton(
            file_frame, text="Browse…", command=self._choose_memory_file
        ).pack(side="left")

        # OS picker
        self.var_os = ctk.StringVar(value="Windows")
        ctk.CTkOptionMenu(
            row, values=["Windows", "Linux"], variable=self.var_os, width=120
        ).grid(row=0, column=1, sticky="ew", padx=10)

        # volatility run
        self.btn_run_mem = ctk.CTkButton(
            row,
            text="Run Volatility",
            command=self._run_volatility,
            state="disabled",
            fg_color="#262626",
        )
        self.btn_run_mem.grid(row=0, column=2, sticky="e", padx=(10, 0))

    # ─── callbacks ─────────────────────────────────────────────────────────
    # EZ‑Tools picker
    def _choose_ez_directory(self) -> None:
        """Select the dir of the ez's tools set"""
        if (chosen := filedialog.askdirectory()):
            self.entry_ez_dir.delete(0, "end")
            self.entry_ez_dir.insert(0, chosen)
            self._populate_checkboxes(Path(chosen))
            logger.info(f"[Flowrensics] Path of the EZ's tools : {chosen}")
    
    # Triage dir picker
    def _choose_triage_directory(self) -> None:
        """Select the triage dir"""
        if (chosen := filedialog.askdirectory()):
            self.entry_triage_dir.delete(0, "end")
            self.entry_triage_dir.insert(0, chosen)
            self._validate_form()
            logger.info(f"[Flowrensics] Path of triage dir : {chosen}")

    def _populate_checkboxes(self, directory: Path) -> None:
        """Create one checkbox per tool found inside directory."""
        # clear previous boxes
        for widget in self.chk_parent.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox) and widget is not self.chk_select_all:
                widget.destroy()
        self.checkbox_vars.clear()

        # scan directory
        for tool in self.ez_tools:
            if is_tool_present(directory, tool):
                var = ctk.BooleanVar()
                chk = ctk.CTkCheckBox(
                    self.chk_parent,
                    text=tool,
                    variable=var,
                    command=self._sync_select_all,
                )
                chk.pack(anchor="w", padx=10, pady=5)
                CTkToolTip(chk, message=TOOL_DESCRIPTIONS.get(tool, "No description."))
                self.checkbox_vars[tool] = var

        self._sync_select_all()

    # Select‑All helper
    def _toggle_all_tools(self) -> None:
        """Select all the tools checkbox"""
        state: bool = self.var_select_all.get()
        for var in self.checkbox_vars.values():
            var.set(state)

    def _sync_select_all(self) -> None:
        """Select all the tools checkbox"""
        if self.checkbox_vars:
            self.var_select_all.set(all(var.get() for var in self.checkbox_vars.values()))
        else:
            self.var_select_all.set(False)

    # Memory‑dump picker
    def _choose_memory_file(self) -> None:
        """Select memory dump"""
        filetypes = [("Memory dumps", "*.dump *.mem *.img *.raw")]
        if (path := filedialog.askopenfilename(title="Select memory dump", filetypes=filetypes)):
            self.entry_mem.delete(0, "end")
            self.entry_mem.insert(0, path)
            self.btn_run_mem.configure(state="normal", fg_color="#99A5FF")

    # main‑form validation
    def _validate_form(self) -> None:
        """Validate the triage directory and enable/disable the *Run* button.
        """

        triage_str: str = self.entry_triage_dir.get().strip()
        triage_path = Path(triage_str) if triage_str else None

        valid = False
        if triage_path is not None and triage_path.is_dir():
            required = {"$Extend", "Users", "Windows", "$MFT"}
            present = {p.name for p in triage_path.iterdir()}
            valid = required.issubset(present)

        if valid:
            # enable button – matches other validators (blue tint)
            self.btn_run_tools.configure(state="normal", fg_color="#99A5FF")
        else:
            # disable button (dark grey)
            logger.info("[Flowrensics] Please select a valid triage dir")
            CTkMessagebox(
                title="Flowrensics",
                message="Please select a valid triage dir",
                icon="warning",
                option_1="Ok"
            )
            self.btn_run_tools.configure(state="disabled", fg_color="#262626")

    
    def _verif_tools_form(self, ez_tools, ez_dir) -> bool:
        return ((ez_tools and ez_dir) or self.var_select_hayabusa.get() or self.var_select_plaso.get())

    # ─── actions ───────────────────────────────────────────────────────────
    def _run_selected_tools(self) -> None:
        """Run the selected tools"""
        ez_tools: list[str] = [tool for tool, checked in self.checkbox_vars.items() if checked.get()]
        ez_dir: str = self.entry_ez_dir.get()
        triage_dir: str = self.entry_triage_dir.get()

        if not (self._verif_tools_form(ez_tools, ez_dir)):
            CTkMessagebox(title="Missing options", message=ALERTS["missing_params"],
                icon="warning", option_1="Ok")
            return
        
        if (self.var_select_hayabusa.get()):
            logger.info("[Flowrensics] Hayabusa module selected")
            HayabusaExecutor(
                parent=self,
                triage_dir=Path(triage_dir)
            ).start()
    
        
        if (self.var_select_plaso.get()):
            logger.warning("[Flowrensics] plaso module not implemented yet")
 
        if (ez_tools):
            ToolExecutor(
                    parent=self,
                    tools=ez_tools,
                    directory=Path(ez_dir),
                    triage_dir=Path(triage_dir)
                ).start()
        

    def _run_volatility(self) -> None:
        """Run the volatility modules"""
        dump_path: str = self.entry_mem.get()
        if not dump_path:
            CTkMessagebox(title="Missing file", message="You must pick a memory dump first.",
                  icon="warning", option_1="ok")
            return

        VolatilityRunner(
            parent=self,
            mem_path=Path(dump_path),
            os_type=self.var_os.get().lower(),
        ).run()


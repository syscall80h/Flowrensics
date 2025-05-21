import os
from pathlib import Path

def check_output_dir() -> None:
    """Mkdir the output dir if it doesn't exist"""
    out_dir = Path("Output")
    out_dir.mkdir(parents=True, exist_ok=True)

def list_user_directories(base_path) -> list[str]:
    excluded_dirs = {"Default", "Public"}
    try:
        return [
            entry.name
            for entry in os.scandir(base_path)
            if entry.is_dir() and entry.name not in excluded_dirs
        ]
    except FileNotFoundError:
        print(f"The directory {base_path} does not exist.")
        return []

def check_userassist_dir() -> None:
    """Mkdir the UserAssist dir if it doesn't exist"""
    userassist_dir = Path("Output") / "UserAssist"
    userassist_dir.mkdir(parents=True, exist_ok=True)

def check_registry_dir() -> None:
    """Mkdir the Registry dir if it doesn't exist"""
    registry_dir = Path("Output") / "Registry"
    registry_dir.mkdir(parents=True, exist_ok=True)

def check_shellbag_dir() -> None:
    """Mkdir the Shellbag dir if it doesn't exist"""
    shellbag_dir = Path("Output") / "ShellBag"
    shellbag_dir.mkdir(parents=True, exist_ok=True)

def check_hayabusa_tool_dir() -> Path:
    """Mkdir the Hayabusa tool dir if it doesn't exist"""
    hayabusa_dir = Path("tools") / "Hayabusa"
    hayabusa_dir.mkdir(parents=True, exist_ok=True)
    return hayabusa_dir

def check_hayabusa_output_dir() -> Path:
    """Mkdir the !hayabusa output dir if it doesn't exist"""
    hayabusa_dir = Path("Output") / "Hayabusa"
    hayabusa_dir.mkdir(parents=True, exist_ok=True)
    return hayabusa_dir

def find_venv_folder(path=".") -> Path | None:
    """Find Venv folder"""
    for name in ["venv", ".venv"]:
        full_path = os.path.join(path, name)
        if os.path.isdir(full_path):
            return full_path
    return None
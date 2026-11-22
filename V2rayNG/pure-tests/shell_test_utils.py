"""Cross-platform helper for locating Bash in pure-tests on Linux and Windows."""
from __future__ import annotations

import os
from pathlib import Path
import shutil


def find_bash() -> str:
    """Return an executable bash path, including Git Bash on Windows."""
    direct = shutil.which("bash")
    if direct:
        # Avoid Windows WSL stub if it points to System32/bash.exe without WSL.
        if os.name != "nt" or not direct.lower().endswith("\\system32\\bash.exe"):
            return direct
    if os.name == "nt":
        for candidate in (
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files\Git\usr\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
        ):
            if Path(candidate).is_file():
                return candidate
    return direct or "bash"

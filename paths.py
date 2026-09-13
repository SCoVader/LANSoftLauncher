import os
import sys
from pathlib import Path


def resource_path(relative_path: str) -> str:
    """Get the absolute path to a bundled resource in development or PyInstaller."""
    try:
        base_path = Path(sys._MEIPASS)  # type: ignore
    except AttributeError:
        base_path = Path(__file__).resolve().parent
    return os.path.join(base_path, relative_path)
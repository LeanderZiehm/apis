from pathlib import Path
from typing import Optional
import os

UPLOAD_DIR = Path("/data/uploads")


def list_files():
    files = []
    for path in UPLOAD_DIR.glob("*"):
        if path.is_file():
            file_id = path.stem
            files.append(
                {
                    "id": file_id,
                    "original_name": path.name,
                    "stored_name": path.name,
                    "size": path.stat().st_size,
                }
            )
    return files


def get_file_path(file_id: str) -> Optional[Path]:
    matches = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matches:
        return None
    return matches[0]


def safe_rename(path: Path, new_name: str) -> Path:
    """
    Rename file while preserving extension.
    """
    new_path = path.with_name(new_name + path.suffix)
    os.rename(path, new_path)
    return new_path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from uuid import uuid4
import shutil

from app.schemas import FileInfo, RenameRequest
from app.storage import (
    UPLOAD_DIR,
    list_files,
    get_file_path,
    safe_rename,
)

app = FastAPI(title="File API", version="1.0.0")


@app.post("/files", response_model=FileInfo)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload any file (binary-safe).
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid4())
    extension = Path(file.filename).suffix
    stored_name = f"{file_id}{extension}"
    destination = UPLOAD_DIR / stored_name

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return FileInfo(
        id=file_id,
        original_name=file.filename,
        stored_name=stored_name,
        size=destination.stat().st_size,
    )


@app.get("/files", response_model=list[FileInfo])
def get_files():
    """
    List all uploaded files.
    """
    return list_files()


@app.get("/files/{file_id}")
def download_file(file_id: str):
    """
    Download a file by ID.
    """
    path = get_file_path(file_id)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path,
        filename=path.name,
        media_type="application/octet-stream",
    )


@app.delete("/files/{file_id}")
def delete_file(file_id: str):
    """
    Delete a file by ID.
    """
    path = get_file_path(file_id)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")

    path.unlink()
    return {"status": "deleted"}


@app.patch("/files/{file_id}", response_model=FileInfo)
def rename_file(file_id: str, payload: RenameRequest):
    """
    Rename a file without changing its extension.
    """
    path = get_file_path(file_id)
    if not path:
        raise HTTPException(status_code=404, detail="File not found")

    new_path = safe_rename(path, payload.new_name)

    return FileInfo(
        id=file_id,
        original_name=payload.new_name + new_path.suffix,
        stored_name=new_path.name,
        size=new_path.stat().st_size,
    )

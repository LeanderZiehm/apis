import os
import hashlib
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from markitdown import MarkItDown
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(title="PPTX to Markdown API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class UploadResponse(BaseModel):
    filename: str
    markdown: str

@app.get("/", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="OCR API Docs")

@app.post("/upload", response_model=UploadResponse)
async def upload_pptx(file: UploadFile = File(...)):
    if not file.filename.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx files are allowed")
    
    contents = await file.read()

    # Generate a unique filename using SHA256 hash + timestamp
    file_hash = hashlib.sha256(contents).hexdigest()[:10]
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    filename = f"{file_hash}_{timestamp}.pptx"
    path_of_uploaded_file = os.path.join(UPLOAD_DIR, filename)

    # Save file to disk
    with open(path_of_uploaded_file, "wb") as f:
        f.write(contents)

    try:
        md = MarkItDown(enable_plugins=True)
        result = md.convert(path_of_uploaded_file)
        md_text = result.text_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert PPTX: {str(e)}")
    
    return UploadResponse(filename=file.filename, markdown=md_text)

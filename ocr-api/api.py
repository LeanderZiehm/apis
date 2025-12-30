from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
import pytesseract
import io
from fastapi.openapi.docs import get_swagger_ui_html

app = FastAPI(title="OCR API")

@app.post("/ocr/")
async def ocr_endpoint(file: UploadFile = File(...)):
    # Read uploaded file
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents))
    except Exception:
        return JSONResponse({"error": "Invalid image"}, status_code=400)

    # OCR
    text = pytesseract.image_to_string(img)
    return {"filename": file.filename, "text": text}

@app.get("/", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="OCR API Docs")

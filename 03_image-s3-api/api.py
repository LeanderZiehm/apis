import os
from uuid import uuid4

import boto3
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path


# ---------- S3 / R2 Client ----------
s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    region_name=os.environ.get("R2_REGION", "auto"),
)

BUCKET = os.environ["R2_BUCKET_NAME"]

# ---------- App ----------
app = FastAPI(title="Image Upload API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# from fastapi.staticfiles import StaticFiles

# app.mount("/static", StaticFiles(directory="static"), name="static") # for favicon and other static assets

@app.get("/")
def get_index_html():
    path = Path("./static/index.html")
    return FileResponse(path)



# ---------- Routes ----------
@app.post("/image/")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Unsupported file type")

    key = f"{uuid4()}-{file.filename}"

    try:
        s3.upload_fileobj(
            file.file,
            BUCKET,
            key,
            ExtraArgs={"ContentType": file.content_type},
        )
    except Exception as e:
        raise HTTPException(500, str(e))

    return {"key": key}


@app.get("/image/{key:path}")
def get_image(key: str):
    try:
        obj = s3.get_object(Bucket=BUCKET, Key=key)
    except Exception:
        raise HTTPException(404, "Image not found")

    return StreamingResponse(
        obj["Body"],
        media_type=obj["ContentType"],
    )

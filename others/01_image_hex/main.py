from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from PIL import Image
import numpy as np
import io
from sklearn.cluster import KMeans

import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class ExtractionLog(Base):
    __tablename__ = "extraction_logs"

    id = Column(Integer, primary_key=True, index=True)
    endpoint = Column(String, index=True)
    result = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)


def save_log(endpoint: str, result: dict):
    db = SessionLocal()
    try:
        log = ExtractionLog(endpoint=endpoint, result=result)
        db.add(log)
        db.commit()
    finally:
        db.close()


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
async def custom_swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title="OCR API Docs")




def load_image(contents: bytes):
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        return np.array(image)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file")



@app.post("/extract-hex")
async def extract_hex(file: UploadFile = File(...)):
    contents = await file.read()
    pixels = load_image(contents)

    pixels = pixels.reshape(-1, 3)
    unique_pixels = np.unique(pixels, axis=0)

    hex_values = [
        "#{:02x}{:02x}{:02x}".format(r, g, b)
        for (r, g, b) in unique_pixels
    ]

    response = {"hex_values": hex_values}

    save_log("extract-hex", response)

    return JSONResponse(content=response)


@app.post("/extract-clustered")
async def extract_clustered(
    file: UploadFile = File(...),
    k: int = Query(10, ge=1, le=50)
):
    contents = await file.read()
    pixels = load_image(contents)

    pixels = pixels.reshape(-1, 3)

    if len(pixels) > 100000:
        idx = np.random.choice(len(pixels), 100000, replace=False)
        pixels_sample = pixels[idx]
    else:
        pixels_sample = pixels

    kmeans = KMeans(n_clusters=k, n_init=10)
    labels = kmeans.fit_predict(pixels_sample)

    centroids = kmeans.cluster_centers_.astype(int)
    counts = np.bincount(labels)

    sorted_idx = np.argsort(-counts)

    result = []
    total = counts.sum()

    for i in sorted_idx:
        r, g, b = centroids[i]
        result.append({
            "hex": "#{:02x}{:02x}{:02x}".format(r, g, b),
            "count": int(counts[i]),
            "percentage": float(counts[i] / total)
        })

    response = {
        "k": k,
        "clusters": result
    }

    save_log("extract-clustered", response)

    return JSONResponse(content=response)
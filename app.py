from fastapi import FastAPI, UploadFile, File, Response
from ultralytics import YOLOWorld
import uvicorn
import io
import json
import os
import time
from PIL import Image
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

MODEL_PATH = os.environ.get("MODEL_PATH", "/mnt/shared-weights/yolov8l-world.pt")
DEPLOYMENT_MODE = os.environ.get("DEPLOYMENT_MODE", "optimized")

app = FastAPI(title=f"YOLO-World Serverless ({DEPLOYMENT_MODE})")

REQUEST_COUNT = Counter(
    "yolo_inference_requests_total",
    "Total inference requests",
    ["mode", "status"],
)
REQUEST_LATENCY = Histogram(
    "yolo_inference_request_duration_seconds",
    "End-to-end request latency",
    ["mode"],
    buckets=[0.5, 1, 2, 5, 10, 15, 30, 60, 120],
)
MODEL_LOAD_SECONDS = Gauge(
    "yolo_model_load_seconds",
    "Time to load model at container startup",
    ["mode"],
)

print(f"[{DEPLOYMENT_MODE}] Đang nạp model từ {MODEL_PATH}...")
load_start = time.time()
model = YOLOWorld(MODEL_PATH)
load_elapsed = time.time() - load_start
MODEL_LOAD_SECONDS.labels(mode=DEPLOYMENT_MODE).set(load_elapsed)
print(f"[{DEPLOYMENT_MODE}] Nạp model thành công trong {load_elapsed:.2f}s")


@app.get("/health")
async def health():
    return {"status": "ok", "mode": DEPLOYMENT_MODE, "model_path": MODEL_PATH}


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    start = time.time()
    status = "success"

    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        results = model.predict(image)
        detections = json.loads(results[0].to_json())
        return {"status": "success", "mode": DEPLOYMENT_MODE, "detections": detections}
    except Exception:
        status = "error"
        raise
    finally:
        elapsed = time.time() - start
        REQUEST_LATENCY.labels(mode=DEPLOYMENT_MODE).observe(elapsed)
        REQUEST_COUNT.labels(mode=DEPLOYMENT_MODE, status=status).inc()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

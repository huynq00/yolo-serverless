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
# Trên Minikube/Docker Desktop, đĩa ảo ~300–500MB/s nên đọc 90MB (~0.2s) không
# lộ bottleneck I/O. MODEL_IO_MBPS > 0 mô phỏng storage bị giới hạn băng thông
# (HDD lạnh / NFS / cloud volume) trước khi deserialize — chỉ dùng cho baseline.
MODEL_IO_MBPS = float(os.environ.get("MODEL_IO_MBPS", "0") or "0")

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


def prepare_model_path(path: str) -> str:
    """Optionally rate-limit the first full read to emulate constrained disk I/O."""
    if MODEL_IO_MBPS <= 0:
        return path

    dest = "/tmp/yolo-weights-throttled.pt"
    chunk = 1024 * 1024
    limit_bps = MODEL_IO_MBPS * 1024 * 1024
    print(
        f"[{DEPLOYMENT_MODE}] Giới hạn đọc weights ~{MODEL_IO_MBPS:.2f} MB/s "
        f"(mô phỏng đĩa chậm) từ {path} → {dest}",
        flush=True,
    )
    t0 = time.time()
    transferred = 0
    with open(path, "rb") as src, open(dest, "wb") as dst:
        while True:
            data = src.read(chunk)
            if not data:
                break
            dst.write(data)
            transferred += len(data)
            expected = transferred / limit_bps
            elapsed = time.time() - t0
            if expected > elapsed:
                time.sleep(expected - elapsed)
    print(
        f"[{DEPLOYMENT_MODE}] Đọc có giới hạn xong: {transferred} bytes "
        f"trong {time.time() - t0:.2f}s",
        flush=True,
    )
    return dest


print(f"[{DEPLOYMENT_MODE}] Đang nạp model từ {MODEL_PATH}...")
load_start = time.time()
effective_path = prepare_model_path(MODEL_PATH)
model = YOLOWorld(effective_path)
load_elapsed = time.time() - load_start
MODEL_LOAD_SECONDS.labels(mode=DEPLOYMENT_MODE).set(load_elapsed)
print(f"[{DEPLOYMENT_MODE}] Nạp model thành công trong {load_elapsed:.2f}s")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": DEPLOYMENT_MODE,
        "model_path": MODEL_PATH,
        "model_io_mbps": MODEL_IO_MBPS,
    }


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

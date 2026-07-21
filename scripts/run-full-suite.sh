#!/usr/bin/env bash
# Chạy toàn bộ nghiệm thu: monitoring + lặp compare độc lập + burst + full + biểu đồ
#
#   ./scripts/run-full-suite.sh
#
# Tùy chỉnh:
#   REPEATS=3 COLD_VUS=3 BURST_VUS=15 ./scripts/run-full-suite.sh
#   SKIP_SETUP=1 ./scripts/run-full-suite.sh   # bỏ qua build/deploy
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

REPEATS="${REPEATS:-3}"
COLD_VUS="${COLD_VUS:-3}"
BURST_VUS="${BURST_VUS:-15}"
WARM_VUS="${WARM_VUS:-3}"
REQUEST_TIMEOUT="${REQUEST_TIMEOUT:-180s}"
SKIP_SETUP="${SKIP_SETUP:-0}"

mkdir -p results/runs results/charts results/monitoring

log() { echo ""; echo ">>> $*"; }

ensure_cluster() {
  if ! minikube status 2>/dev/null | grep -q "host: Running"; then
    log "Khởi động Minikube..."
    minikube start --driver=docker
  fi
  eval "$(minikube -p minikube docker-env)"
}

port_ready() {
  local code
  code=$(curl -s --max-time 2 -o /dev/null -w "%{http_code}" "http://127.0.0.1:8080" 2>/dev/null || echo "000")
  [[ "${code}" != "000" ]]
}

ensure_port_forward() {
  if port_ready; then
    return 0
  fi
  log "Khởi động / làm mới port-forward Kourier (nền)..."
  pkill -f "kubectl port-forward -n kourier-system svc/kourier" 2>/dev/null || true
  sleep 1
  kubectl port-forward -n kourier-system svc/kourier 8080:80 >/tmp/kourier-pf.log 2>&1 &
  for i in $(seq 1 30); do
    if port_ready; then
      echo "Port-forward OK sau ${i}x2s"
      return 0
    fi
    sleep 2
  done
  echo "ERROR: Không mở được port 8080 sau 60s"
  cat /tmp/kourier-pf.log 2>/dev/null || true
  exit 1
}

ensure_weights() {
  if minikube ssh "test -f /mnt/shared-weights/yolov8l-world.pt && test -f /mnt/disk-weights/yolov8l-world.pt" 2>/dev/null; then
    return 0
  fi
  log "Model weights thiếu trên node — chạy setup-weights.sh..."
  bash scripts/setup-weights.sh
}

assert_k6_success() {
  local json_path="$1"
  local label="$2"
  python3 - "$json_path" "$label" <<'PY'
import json, sys
path, label = sys.argv[1], sys.argv[2]
data = json.load(open(path, encoding="utf-8"))
failed = data.get("metrics", {}).get("http_req_failed", {}).get("values", {})
rate = failed.get("rate")
if rate is None:
    print(f"ERROR: {label}: thiếu http_req_failed")
    sys.exit(1)
duration = None
for k, m in data.get("metrics", {}).items():
    if "http_req_duration" in k and "phase:" in k:
        duration = m.get("values", {})
        break
if duration is None:
    duration = data.get("metrics", {}).get("http_req_duration", {}).get("values", {})
p99 = (duration or {}).get("p(99)", 0) or 0
# Cold-start thực tế luôn > 1s; reject run chết (0ms) hoặc fail > 50%
if p99 < 1000:
    print(f"ERROR: {label}: p99={p99}ms quá thấp — request không chạy thật")
    sys.exit(1)
if rate > 0.5:
    print(f"ERROR: {label}: fail_rate={rate:.2%} — quá nhiều lỗi HTTP")
    sys.exit(1)
print(f"OK: {label}: fail_rate={rate:.2%} p99={p99/1000:.2f}s")
PY
}

run_compare_once() {
  local run_dir="$1"
  mkdir -p "${run_dir}"
  ensure_port_forward

  log "[Compare] Optimized (RAM) → ${run_dir}"
  KNATIVE_SERVICE=yolo-inference bash scripts/prepare-cold-start.sh
  ensure_port_forward
  sleep 3
  k6 run -q --no-thresholds \
    -e "COLD_VUS=${COLD_VUS}" \
    -e "TIMEOUT=${REQUEST_TIMEOUT}" \
    -e "OUTPUT_TAG=optimized" \
    -e "BASE_URL=http://yolo-inference.default.127.0.0.1.sslip.io:8080/predict" \
    loadtest-cold.js
  cp results/k6-cold-optimized-latest.json "${run_dir}/k6-cold-optimized.json"
  assert_k6_success "${run_dir}/k6-cold-optimized.json" "optimized ${run_dir}"

  log "[Compare] Baseline (Disk) → ${run_dir}"
  KNATIVE_SERVICE=yolo-inference-baseline bash scripts/prepare-cold-start.sh
  ensure_port_forward
  sleep 3
  k6 run -q --no-thresholds \
    -e "COLD_VUS=${COLD_VUS}" \
    -e "TIMEOUT=${REQUEST_TIMEOUT}" \
    -e "OUTPUT_TAG=baseline" \
    -e "BASE_URL=http://yolo-inference-baseline.default.127.0.0.1.sslip.io:8080/predict" \
    loadtest-cold.js
  cp results/k6-cold-baseline-latest.json "${run_dir}/k6-cold-baseline.json"
  assert_k6_success "${run_dir}/k6-cold-baseline.json" "baseline ${run_dir}"
}

# ── Main ──────────────────────────────────────────────────────────
log "YOLO Serverless — Full Acceptance Suite"
echo "REPEATS=${REPEATS} COLD_VUS=${COLD_VUS} BURST_VUS=${BURST_VUS} TIMEOUT=${REQUEST_TIMEOUT}"

if [ "${SKIP_SETUP}" != "1" ]; then
  ensure_cluster
  bash scripts/setup-weights.sh
  bash scripts/build-image.sh
  kubectl apply -f service.yaml
  kubectl apply -f service-baseline.yaml
  bash scripts/setup-monitoring.sh
else
  ensure_cluster
  ensure_weights
fi

ensure_port_forward

# Xóa seed giả (copy trùng) nếu còn
rm -rf results/runs/run-*

# ── Lặp thí nghiệm compare ĐỘC LẬP ────────────────────────────────
log "Lặp compare cold-start ${REPEATS} lần (mỗi lần scale-to-zero riêng)..."
for i in $(seq 1 "${REPEATS}"); do
  run_compare_once "results/runs/run-${i}"
  echo "  ✓ Hoàn thành lần ${i}/${REPEATS}"
done

cp "results/runs/run-${REPEATS}/k6-cold-optimized.json" results/k6-cold-optimized-latest.json
cp "results/runs/run-${REPEATS}/k6-cold-baseline.json" results/k6-cold-baseline-latest.json

python3 scripts/analyze-comparison.py
python3 scripts/analyze-repeat.py

# ── Burst traffic ─────────────────────────────────────────────────
log "Burst traffic benchmark (BURST_VUS=${BURST_VUS})..."
ensure_port_forward
# Warmup optimized + baseline để Prometheus có cả 2 mode
curl -sf --max-time 180 -F "file=@test.jpg" \
  "http://yolo-inference.default.127.0.0.1.sslip.io:8080/predict" >/dev/null || true
curl -sf --max-time 180 -F "file=@test.jpg" \
  "http://yolo-inference-baseline.default.127.0.0.1.sslip.io:8080/predict" >/dev/null || true

k6 run -q --no-thresholds \
  -e "BURST_VUS=${BURST_VUS}" \
  -e "TIMEOUT=${REQUEST_TIMEOUT}" \
  -e "BASE_URL=http://yolo-inference.default.127.0.0.1.sslip.io:8080/predict" \
  loadtest-burst.js
python3 scripts/analyze-burst.py

# Snapshot monitoring ngay sau burst (còn metric nóng)
log "Capture Prometheus/Grafana evidence..."
bash scripts/capture-monitoring-evidence.sh || echo "WARN: capture monitoring thất bại (tiếp tục)"

# ── Full 3 phase ──────────────────────────────────────────────────
log "Full benchmark (cold → burst → warm)..."
KNATIVE_SERVICE=yolo-inference bash scripts/prepare-cold-start.sh
ensure_port_forward
sleep 3
k6 run -q --no-thresholds \
  -e "COLD_VUS=${COLD_VUS}" \
  -e "BURST_VUS=${BURST_VUS}" \
  -e "WARM_VUS=${WARM_VUS}" \
  -e "TIMEOUT=${REQUEST_TIMEOUT}" \
  -e "BASE_URL=http://yolo-inference.default.127.0.0.1.sslip.io:8080/predict" \
  loadtest.js
assert_k6_success results/k6-full-latest.json "full-suite"
python3 scripts/analyze-results.py results/k6-full-latest.json

# Capture lần nữa sau full
bash scripts/capture-monitoring-evidence.sh || true

# ── Export biểu đồ ────────────────────────────────────────────────
log "Export biểu đồ..."
pip3 install matplotlib -q 2>/dev/null || pip install matplotlib -q 2>/dev/null || true
python3 scripts/export-charts.py
python3 scripts/export-monitoring-charts.py

log "Tạo báo cáo tổng hợp..."
python3 scripts/generate-final-report.py
bash scripts/verify-acceptance.sh

echo ""
echo "════════════════════════════════════════════════════════"
echo "  HOÀN TẤT NGHIỆM THU — xem:"
echo "  • results/FINAL-REPORT.md"
echo "  • results/charts/"
echo "  • results/monitoring/"
echo "  • Grafana: kubectl port-forward -n monitoring svc/grafana 3000:3000"
echo "════════════════════════════════════════════════════════"

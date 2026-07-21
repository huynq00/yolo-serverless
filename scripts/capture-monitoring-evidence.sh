#!/usr/bin/env bash
# Thu thập bằng chứng Prometheus/Grafana khi hệ thống đang chịu tải.
#
#   ./scripts/capture-monitoring-evidence.sh
#
# Yêu cầu: monitoring namespace đã deploy (setup-monitoring.sh)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

OUT="${ROOT}/results/monitoring"
mkdir -p "${OUT}"

PROM_LOCAL_PORT="${PROM_LOCAL_PORT:-9091}"
GRAFANA_LOCAL_PORT="${GRAFANA_LOCAL_PORT:-3000}"

log() { echo "==> $*"; }

pkill -f "kubectl port-forward -n monitoring svc/prometheus ${PROM_LOCAL_PORT}" 2>/dev/null || true
pkill -f "kubectl port-forward -n monitoring svc/grafana ${GRAFANA_LOCAL_PORT}" 2>/dev/null || true
sleep 1

log "Port-forward Prometheus → localhost:${PROM_LOCAL_PORT}"
kubectl port-forward -n monitoring svc/prometheus "${PROM_LOCAL_PORT}:9090" \
  >"/tmp/prom-pf.log" 2>&1 &
PROM_PF_PID=$!

log "Port-forward Grafana → localhost:${GRAFANA_LOCAL_PORT}"
kubectl port-forward -n monitoring svc/grafana "${GRAFANA_LOCAL_PORT}:3000" \
  >"/tmp/grafana-pf.log" 2>&1 &
GRAFANA_PF_PID=$!

cleanup() {
  kill "${PROM_PF_PID}" "${GRAFANA_PF_PID}" 2>/dev/null || true
}
trap cleanup EXIT

for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${PROM_LOCAL_PORT}/-/ready" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! curl -sf "http://127.0.0.1:${PROM_LOCAL_PORT}/-/ready" >/dev/null 2>&1; then
  echo "ERROR: Prometheus chưa sẵn sàng"
  cat /tmp/prom-pf.log 2>/dev/null || true
  exit 1
fi

query() {
  local expr="$1"
  local out="$2"
  curl -sfG "http://127.0.0.1:${PROM_LOCAL_PORT}/api/v1/query" \
    --data-urlencode "query=${expr}" \
    -o "${out}"
}

log "Snapshot Prometheus metrics..."
query 'yolo_model_load_seconds' "${OUT}/model-load.json"
query 'histogram_quantile(0.99, sum(rate(yolo_inference_request_duration_seconds_bucket[5m])) by (le, mode))' \
  "${OUT}/p99-latency.json"
query 'sum(rate(yolo_inference_requests_total[5m])) by (mode, status)' \
  "${OUT}/request-rate.json"
query 'sum(rate(yolo_inference_request_duration_seconds_sum[5m])) by (mode) / sum(rate(yolo_inference_request_duration_seconds_count[5m])) by (mode)' \
  "${OUT}/avg-latency.json"

# Targets health
curl -sf "http://127.0.0.1:${PROM_LOCAL_PORT}/api/v1/targets" -o "${OUT}/targets.json" || true

# Grafana dashboard metadata (chứng minh dashboard đã provision)
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:${GRAFANA_LOCAL_PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if curl -sf "http://127.0.0.1:${GRAFANA_LOCAL_PORT}/api/health" >/dev/null 2>&1; then
  curl -sf -u admin:admin \
    "http://127.0.0.1:${GRAFANA_LOCAL_PORT}/api/dashboards/uid/yolo-coldstart" \
    -o "${OUT}/grafana-dashboard.json" || true
  echo "http://localhost:${GRAFANA_LOCAL_PORT}/d/yolo-coldstart/yolo-cold-start-ram-vs-disk" \
    > "${OUT}/grafana-url.txt"
  log "Grafana dashboard URL lưu tại ${OUT}/grafana-url.txt"
else
  echo "WARN: Grafana chưa sẵn sàng — bỏ qua dashboard metadata"
fi

python3 scripts/export-monitoring-charts.py

log "Monitoring evidence tại: ${OUT}/"
ls -la "${OUT}/"

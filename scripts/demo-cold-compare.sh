#!/usr/bin/env bash
# Demo đối chứng cold-start live: Baseline (Disk) → Optimized (RAM)
# In bảng P99 thực tế — không cần mở FINAL-REPORT.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

COLD_VUS="${COLD_VUS:-3}"
REQUEST_TIMEOUT="${TIMEOUT:-180s}"
DROP_CACHE="${DROP_CACHE:-1}"
URL_OPT="http://yolo-inference.default.127.0.0.1.sslip.io:8080/predict"
URL_BASE="http://yolo-inference-baseline.default.127.0.0.1.sslip.io:8080/predict"

if ! command -v k6 >/dev/null 2>&1; then
  echo "ERROR: chưa có lệnh k6. Cài: brew install k6"
  exit 1
fi

code=$(curl -s --max-time 2 -o /dev/null -w "%{http_code}" "http://127.0.0.1:8080" 2>/dev/null || echo "000")
if [[ "${code}" == "000" ]]; then
  echo "ERROR: không kết nối 127.0.0.1:8080"
  echo "Chạy ở terminal khác:"
  echo "  kubectl port-forward -n kourier-system svc/kourier 8080:80"
  exit 1
fi

mkdir -p results

drop_page_cache() {
  if [[ "${DROP_CACHE}" != "1" ]]; then
    return 0
  fi
  echo "==> Drop page cache trên Minikube node (đo Disk công bằng)..."
  minikube ssh "sudo sync; echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null"
}

run_cold() {
  local tag="$1"
  local service="$2"
  local url="$3"

  echo ""
  echo "════════════════════════════════════════════════════════"
  echo "  COLD-START: ${tag}  (COLD_VUS=${COLD_VUS})"
  echo "════════════════════════════════════════════════════════"

  KNATIVE_SERVICE="${service}" bash scripts/prepare-cold-start.sh

  if [[ "${tag}" == "baseline" ]]; then
    drop_page_cache
  fi

  sleep 2

  k6 run --no-thresholds \
    -e "COLD_VUS=${COLD_VUS}" \
    -e "TIMEOUT=${REQUEST_TIMEOUT}" \
    -e "OUTPUT_TAG=${tag}" \
    -e "BASE_URL=${url}" \
    loadtest-cold.js
}

echo "YOLO Serverless — DEMO cold-start đối chứng (số liệu LIVE)"
echo "Thứ tự: Baseline (Disk) trước → Optimized (RAM) sau"
echo "COLD_VUS=${COLD_VUS}  TIMEOUT=${REQUEST_TIMEOUT}  DROP_CACHE=${DROP_CACHE}"
echo ""

# Baseline trước để khán giả thấy chậm, rồi Optimized nhanh hơn
run_cold baseline yolo-inference-baseline "${URL_BASE}"
run_cold optimized yolo-inference "${URL_OPT}"

echo ""
echo "════════════════════════════════════════════════════════"
echo "  KẾT QUẢ LIVE (vừa đo xong — đọc to trên camera)"
echo "════════════════════════════════════════════════════════"
python3 scripts/analyze-comparison.py

opt_json="results/k6-cold-optimized-latest.json"
base_json="results/k6-cold-baseline-latest.json"
python3 - <<PY
import json
from pathlib import Path

def p99(path):
    d = json.loads(Path(path).read_text())
    m = d.get("metrics", {})
    for key, metric in m.items():
        if "http_req_duration" in key and "phase:cold_start" in key:
            return metric.get("values", {}).get("p(99)") or metric.get("values", {}).get("max")
    v = m.get("cold_start_latency_ms", {}).get("values", {})
    return v.get("p(99)") or v.get("max")

opt = p99("${opt_json}")
base = p99("${base_json}")
if not opt or not base:
    raise SystemExit("Không đọc được P99 từ k6 JSON")

opt_s, base_s = opt / 1000, base / 1000
imp = (1 - opt / base) * 100
print()
print("=" * 70)
print(f"  LIVE P99  Disk (baseline) : {base_s:6.2f}s")
print(f"  LIVE P99  RAM  (optimized): {opt_s:6.2f}s")
print(f"  Giảm P99                  : {imp:6.1f}%")
print("=" * 70)
if base_s < 25:
    print("CẢNH BÁO: Baseline P99 thấp bất thường (<25s).")
    print("  Kiểm tra tmpfs/weights; chạy lại với DROP_CACHE=1.")
if opt_s >= base_s:
    print("CẢNH BÁO: Optimized không nhanh hơn Baseline — đừng dùng take này.")
    raise SystemExit(2)
print("ĐẠT: RAM nhanh hơn Disk trên cold-start vừa đo — dùng số trên để kết luận demo.")
PY

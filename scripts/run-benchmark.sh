#!/usr/bin/env bash
# Pipeline benchmark đầy đủ: cold-start → burst → warm + phân tích P99
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

mkdir -p results

COLD_VUS="${COLD_VUS:-10}"
BURST_VUS="${BURST_VUS:-15}"
WARM_VUS="${WARM_VUS:-5}"
MODE="${1:-full}"

port_ready() {
  local code
  code=$(curl -s --max-time 2 -o /dev/null -w "%{http_code}" "http://127.0.0.1:8080" 2>/dev/null || echo "000")
  [[ "${code}" != "000" ]]
}

check_port_forward() {
  if port_ready; then
    return 0
  fi

  echo ""
  echo "ERROR: Không kết nối được 127.0.0.1:8080"
  echo "Hãy chạy port-forward ở terminal riêng:"
  echo "  kubectl port-forward -n kourier-system svc/kourier 8080:80"
  echo ""
  echo "Hoặc bỏ qua kiểm tra: SKIP_PORT_CHECK=1 ./scripts/run-benchmark.sh"
  if [ "${SKIP_PORT_CHECK:-}" != "1" ]; then
    exit 1
  fi
}

run_phase() {
  local name="$1"
  local script="$2"
  shift 2
  echo ""
  echo "════════════════════════════════════════"
  echo "  PHASE: ${name}"
  echo "════════════════════════════════════════"
  k6 run \
    -e "COLD_VUS=${COLD_VUS}" \
    -e "BURST_VUS=${BURST_VUS}" \
    -e "WARM_VUS=${WARM_VUS}" \
    "$@" \
    "${script}"
}

check_port_forward

case "${MODE}" in
  full)
    echo "==> Chuẩn bị cold-start (scale-to-zero)..."
    bash scripts/prepare-cold-start.sh
    sleep 3
    run_phase "COLD-START + BURST + WARM (full)" loadtest.js
    ;;
  cold)
    bash scripts/prepare-cold-start.sh
    sleep 3
    run_phase "COLD-START only" loadtest-cold.js
    ;;
  burst)
    echo "==> Burst (pod phải đang warm — gửi 1 request warmup trước)..."
    curl -sf --max-time 120 \
      -F "file=@test.jpg" \
      "http://yolo-inference.default.127.0.0.1.sslip.io:8080/predict" \
      >/dev/null || true
    run_phase "BURST only" loadtest-burst.js
    ;;
  smoke)
    run_phase "SMOKE test" loadtest-smoke.js
    ;;
  compare)
    echo "==> So sánh cold-start: Optimized (RAM) vs Baseline (Disk)"
    echo ""

    echo "--- [1/2] OPTIMIZED (RAM tmpfs) ---"
    KNATIVE_SERVICE=yolo-inference bash scripts/prepare-cold-start.sh
    sleep 3
    k6 run \
      -e "COLD_VUS=${COLD_VUS}" \
      -e "OUTPUT_TAG=optimized" \
      -e "BASE_URL=http://yolo-inference.default.127.0.0.1.sslip.io:8080/predict" \
      loadtest-cold.js

    echo ""
    echo "--- [2/2] BASELINE (Disk) ---"
    KNATIVE_SERVICE=yolo-inference-baseline bash scripts/prepare-cold-start.sh
    sleep 3
    k6 run \
      -e "COLD_VUS=${COLD_VUS}" \
      -e "OUTPUT_TAG=baseline" \
      -e "BASE_URL=http://yolo-inference-baseline.default.127.0.0.1.sslip.io:8080/predict" \
      loadtest-cold.js

    echo ""
    python3 scripts/analyze-comparison.py
    exit 0
    ;;
  *)
    echo "Usage: $0 [full|cold|burst|smoke|compare]"
    exit 1
    ;;
esac

echo ""
echo "==> Phân tích kết quả..."
python3 scripts/analyze-results.py

echo ""
echo "==> Xong. Kết quả JSON tại: results/"

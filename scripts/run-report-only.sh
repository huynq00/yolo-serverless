#!/usr/bin/env bash
# Chỉ xuất lại báo cáo/biểu đồ từ kết quả ĐÃ CÓ (không seed giả 3 lần chạy).
#
# Nếu muốn đo lại cold-start độc lập: dùng ./scripts/run-full-suite.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

mkdir -p results/charts results/monitoring

if [ ! -f results/k6-cold-optimized-latest.json ] || [ ! -f results/k6-cold-baseline-latest.json ]; then
  echo "ERROR: Thiếu k6-cold-*-latest.json — chạy ./scripts/run-full-suite.sh"
  exit 1
fi

# Không copy 1 file thành 3 runs. Chỉ phân tích runs thật nếu có.
if ls results/runs/run-*/k6-cold-optimized.json >/dev/null 2>&1; then
  # Phát hiện seed giả: hash trùng nhau
  hashes=$(find results/runs -name 'k6-cold-optimized.json' -exec shasum {} \; | awk '{print $1}' | sort -u | wc -l | tr -d ' ')
  if [ "${hashes}" = "1" ]; then
    n=$(find results/runs -name 'k6-cold-optimized.json' | wc -l | tr -d ' ')
    if [ "${n}" -gt 1 ]; then
      echo "ERROR: Phát hiện ${n} runs giống hệt nhau (seed giả)."
      echo "Xóa results/runs và chạy lại: ./scripts/run-full-suite.sh"
      exit 1
    fi
  fi
  python3 scripts/analyze-repeat.py
else
  echo "WARN: Chưa có results/runs/run-* — bỏ qua thống kê lặp"
fi

python3 scripts/analyze-comparison.py

if [ -f results/k6-burst-latest.json ]; then
  python3 scripts/analyze-burst.py
fi

if [ -f results/k6-full-latest.json ]; then
  python3 scripts/analyze-results.py results/k6-full-latest.json
fi

pip3 install matplotlib -q 2>/dev/null || true
python3 scripts/export-charts.py
python3 scripts/export-monitoring-charts.py || true
python3 scripts/generate-final-report.py

echo ""
echo "════════════════════════════════════════════════════════"
echo "  Báo cáo: results/FINAL-REPORT.md"
echo "════════════════════════════════════════════════════════"

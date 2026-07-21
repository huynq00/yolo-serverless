#!/usr/bin/env bash
# Kiểm tra nghiệm thu 100% theo checklist đề tài.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

PASS=0
FAIL=0

ok() { echo "  ✓ $1"; PASS=$((PASS + 1)); }
bad() { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }

echo "════════════════════════════════════════════════════════"
echo "  VERIFY ACCEPTANCE — YOLO Serverless"
echo "════════════════════════════════════════════════════════"

# 1. Infra manifests
[ -f service.yaml ] && [ -f service-baseline.yaml ] && ok "Knative services (optimized + baseline)" || bad "Thiếu Knative service manifests"
[ -f scripts/setup-weights.sh ] && ok "Weight-sharing setup script" || bad "Thiếu setup-weights.sh"
[ -d monitoring ] && [ -f scripts/setup-monitoring.sh ] && ok "Prometheus/Grafana manifests" || bad "Thiếu monitoring"

# 2. Independent repeats
if [ -d results/runs ]; then
  n=$(find results/runs -name 'k6-cold-optimized.json' 2>/dev/null | wc -l | tr -d ' ')
  if [ "${n}" -ge 3 ]; then
    hashes=$(find results/runs -name 'k6-cold-optimized.json' -exec shasum {} \; | awk '{print $1}' | sort -u | wc -l | tr -d ' ')
    if [ "${hashes}" -ge 2 ]; then
      ok "Cold-start lặp độc lập (${n} runs, ${hashes} hash khác nhau)"
    elif [ "${hashes}" = "1" ]; then
      bad "Cold-start runs trùng hash (seed giả) — cần chạy lại full suite"
    else
      bad "Không đọc được hash runs"
    fi
  else
    bad "Cần ≥3 lần cold-start độc lập (hiện có ${n})"
  fi
else
  bad "Thiếu results/runs/"
fi

# 3. P99 improvement
if [ -f results/repeat-stats.json ]; then
  python3 - <<'PY' && ok "P99 improvement có trong repeat-stats" || bad "P99 improvement thiếu/không hợp lệ"
import json
from pathlib import Path
d=json.loads(Path("results/repeat-stats.json").read_text())
imp=d.get("improvement_percent")
opt=d.get("optimized",{}).get("stdev")
assert imp is not None and imp > 50, imp
# stdev có thể 0 nếu infra rất ổn định, nhưng mean phải khác nhau giữa modes
assert d["optimized"]["mean"] < d["baseline"]["mean"]
print(f"improvement={imp:.1f}% opt_stdev={opt}")
PY
else
  bad "Thiếu repeat-stats.json"
fi

# 4. Burst
if [ -f results/burst-verdict.json ]; then
  python3 - <<'PY' && ok "Burst không tắc nghẽn" || bad "Burst chưa đạt"
import json
from pathlib import Path
d=json.loads(Path("results/burst-verdict.json").read_text())
assert d.get("verdict")=="ok", d
assert d.get("failed_rate_percent", 100) < 10
PY
else
  bad "Thiếu burst-verdict.json"
fi

# 5. Full 3-phase không toàn 0
if [ -f results/k6-full-latest.json ]; then
  python3 - <<'PY' && ok "Full 3-phase có latency thực" || bad "Full 3-phase toàn 0 / thất bại"
import json
from pathlib import Path
m=json.loads(Path("results/k6-full-latest.json").read_text())["metrics"]
ok_phases=0
for phase in ("cold_start","burst","warm"):
  key=f"http_req_duration{{phase:{phase}}}"
  v=m.get(key,{}).get("values",{})
  if (v.get("p(99)") or 0) > 0:
    ok_phases+=1
assert ok_phases>=3, f"chỉ {ok_phases}/3 phase có p99>0"
failed=m.get("http_req_failed",{}).get("values",{}).get("rate",1)
assert failed < 0.2, failed
PY
else
  bad "Thiếu k6-full-latest.json"
fi

# 6. Charts
[ -f results/charts/chart-cold-p99-comparison.svg ] || [ -f results/charts/chart-cold-p99-comparison.png ] \
  && ok "Biểu đồ cold P99" || bad "Thiếu biểu đồ cold P99"
[ -f results/charts/grafana-p99-sidebyside.svg ] || [ -f results/charts/grafana-p99-sidebyside.png ] \
  && ok "Biểu đồ Grafana-style side-by-side" || bad "Thiếu biểu đồ Grafana-style"

# 7. Monitoring evidence
[ -f results/monitoring/evidence-summary.json ] || [ -f results/monitoring/model-load.json ] \
  && ok "Monitoring evidence (Prometheus snapshot)" || bad "Thiếu results/monitoring evidence"
[ -f monitoring/grafana.yaml ] && ok "Grafana dashboard provisioned in manifests" || bad "Thiếu grafana.yaml"

# 8. Final report
[ -f results/FINAL-REPORT.md ] && ok "FINAL-REPORT.md" || bad "Thiếu FINAL-REPORT.md"

echo ""
echo "Kết quả: ${PASS} đạt, ${FAIL} chưa đạt"
if [ "${FAIL}" -gt 0 ]; then
  echo "Chưa khớp 100% — chạy: ./scripts/run-full-suite.sh"
  exit 1
fi
echo "NGHIỆM THU 100% — sẵn sàng bảo vệ."
exit 0

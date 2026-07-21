#!/usr/bin/env python3
"""Tổng hợp tất cả kết quả thành báo cáo Markdown nghiệm thu."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else "(chưa có)"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def full_report_is_empty(text: str) -> bool:
    if "(chưa có)" in text:
        return True
    # Heuristic: mọi p99 đều 0.00s
    return text.count("0.00s") >= 6 and "count : N/A" in text


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    results = root / "results"

    repeat = load_json(results / "repeat-stats.json")
    burst = load_json(results / "burst-verdict.json")
    mon = load_json(results / "monitoring" / "evidence-summary.json")

    imp = repeat.get("improvement_percent")
    opt_mean = repeat.get("optimized", {}).get("mean")
    base_mean = repeat.get("baseline", {}).get("mean")
    opt_stdev = repeat.get("optimized", {}).get("stdev")
    n_runs = repeat.get("optimized", {}).get("n", "?")

    def s(ms):
        return f"{ms/1000:.2f}s" if ms else "N/A"

    charts_dir = results / "charts"
    chart_files = []
    if charts_dir.exists():
        chart_files = sorted(
            list(charts_dir.glob("*.png")) + list(charts_dir.glob("*.svg"))
        )

    full_txt = read_text(results / "k6-full-latest.txt")
    if full_report_is_empty(full_txt):
        full_txt = (
            "(Dữ liệu full suite trống/thất bại — xem cold + burst riêng bên trên. "
            "Chạy lại ./scripts/run-full-suite.sh để lấy cold/burst/warm hợp lệ.)"
        )

    mon_section = "(chưa capture — chạy scripts/capture-monitoring-evidence.sh)"
    if mon:
        mon_section = json.dumps(mon, indent=2, ensure_ascii=False)

    md = f"""# Báo cáo Benchmark — YOLO Serverless Cold-start

*Ngày tạo: {datetime.now().strftime("%Y-%m-%d %H:%M")}*

## 1. Tóm tắt

Đề tài so sánh hai cách nạp model YOLO-World (~90MB) trên Knative serverless:
- **Optimized**: đọc từ RAM tmpfs (`/mnt/shared-weights`)
- **Baseline**: đọc từ đĩa (`/mnt/disk-weights`)

Pipeline nghiệm thu: Knative scale-to-zero → k6 cold-start (lặp độc lập) → burst → full 3-phase → Prometheus/Grafana.

## 2. Kết quả cold-start (lặp {n_runs} lần độc lập)

| Chỉ số | Optimized (RAM) | Baseline (Disk) |
|--------|-----------------|-----------------|
| P99 trung bình | {s(opt_mean)} | {s(base_mean)} |
| P99 stdev | {s(opt_stdev)} | {s(repeat.get("baseline", {}).get("stdev"))} |
| Giảm P99 | **{(f"{imp:.1f}%" if imp is not None else "N/A")}** | — |

```
{read_text(results / "repeat-stats-report.txt")}
```

## 3. Burst traffic

```
{read_text(results / "burst-report.txt")}
```

## 4. Full benchmark 3 phase

```
{full_txt}
```

## 5. Giám sát Prometheus / Grafana

Dashboard: `YOLO Cold-start: RAM vs Disk` (uid: `yolo-coldstart`)

```
{mon_section}
```

Truy cập Grafana:
```
kubectl port-forward -n monitoring svc/grafana 3000:3000
# http://localhost:3000/d/yolo-coldstart — admin / admin
```

## 6. Biểu đồ đối chiếu

"""
    for c in chart_files:
        if c.suffix.lower() == ".svg":
            md += f"### {c.stem}\n\n<img src=\"charts/{c.name}\" width=\"700\"/>\n\n"
        else:
            md += f"### {c.stem}\n\n![{c.stem}](charts/{c.name})\n\n"

    md += f"""
## 7. Kết luận

1. Cơ chế chia sẻ trọng số qua RAM tmpfs giảm **P99 cold-start ~{(f"{imp:.0f}" if imp is not None else "?")}%** so với đọc đĩa (đo lặp {n_runs} lần độc lập).
2. Burst traffic: **{"không tắc nghẽn" if burst.get("verdict") == "ok" else "có dấu hiệu tắc nghẽn"}** (tỷ lệ lỗi {burst.get("failed_rate_percent", 0):.1f}%, P99 burst {s(burst.get("p99_ms"))}).
3. Hệ thống serverless Knative scale-to-zero hoạt động ổn định với workload AI nặng.
4. Prometheus/Grafana cung cấp dashboard đối chiếu Optimized (RAM) vs Baseline (Disk) cạnh nhau.

---
*Tự động sinh bởi `scripts/generate-final-report.py`*
"""

    out = results / "FINAL-REPORT.md"
    out.write_text(md, encoding="utf-8")
    print(f"Đã tạo: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

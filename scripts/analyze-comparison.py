#!/usr/bin/env python3
"""So sánh P99 cold-start: optimized (RAM) vs baseline (disk)."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def fmt_ms(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value / 1000:.2f}s"


def load_metric(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    metrics = data.get("metrics", {})
    for key, metric in metrics.items():
        if "http_req_duration" in key and "phase:cold_start" in key:
            return metric.get("values", {})

    return metrics.get("http_req_duration", {}).get("values", {})


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    results = root / "results"

    optimized_path = results / "k6-cold-optimized-latest.json"
    baseline_path = results / "k6-cold-baseline-latest.json"

    if not optimized_path.exists() or not baseline_path.exists():
        print("Thiếu file kết quả. Chạy trước:")
        print("  ./scripts/run-benchmark.sh compare")
        return 1

    opt = load_metric(optimized_path)
    base = load_metric(baseline_path)

    print("=" * 70)
    print("  SO SÁNH COLD-START: OPTIMIZED (RAM) vs BASELINE (DISK)")
    print("=" * 70)
    print(f"{'Metric':<12} {'Optimized':>12} {'Baseline':>12} {'Cải thiện':>14}")
    print("-" * 70)

    for label, key in [
        ("Avg", "avg"),
        ("P90", "p(90)"),
        ("P95", "p(95)"),
        ("P99", "p(99)"),
        ("Max", "max"),
    ]:
        o = opt.get(key)
        b = base.get(key)
        if o and b and b > 0:
            improvement = (1 - o / b) * 100
            imp_str = f"{improvement:+.1f}%"
        else:
            imp_str = "N/A"
        print(f"{label:<12} {fmt_ms(o):>12} {fmt_ms(b):>12} {imp_str:>14}")

    print("-" * 70)
    opt_p99 = opt.get("p(99)") or opt.get("max")
    base_p99 = base.get("p(99)") or base.get("max")
    if opt_p99 and base_p99:
        delta = base_p99 - opt_p99
        print(f"  P99 baseline chậm hơn optimized: {fmt_ms(delta)}")
        print(f"  Giảm P99: {(1 - opt_p99 / base_p99) * 100:.1f}%")

    report_path = results / "comparison-report.txt"
    report_path.write_text(
        "\n".join(
            [
                "Cold-start comparison",
                f"optimized_p99={fmt_ms(opt.get('p(99)'))}",
                f"baseline_p99={fmt_ms(base.get('p(99)'))}",
                f"optimized_avg={fmt_ms(opt.get('avg'))}",
                f"baseline_avg={fmt_ms(base.get('avg'))}",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\nBáo cáo lưu tại: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

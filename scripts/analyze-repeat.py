#!/usr/bin/env python3
"""Tổng hợp thống kê từ nhiều lần chạy compare (mean, std, CI)."""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path


def fmt_ms(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value / 1000:.2f}s"


def load_p99(path: Path, phase: str = "cold_start") -> dict:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    metrics = data.get("metrics", {})
    for key, metric in metrics.items():
        if "http_req_duration" in key and f"phase:{phase}" in key:
            return metric.get("values", {})

    return metrics.get("http_req_duration", {}).get("values", {})


def collect_runs(runs_dir: Path, tag: str) -> list[dict]:
    runs = []
    for path in sorted(runs_dir.glob(f"run-*/k6-cold-{tag}.json")):
        values = load_p99(path)
        if values:
            runs.append(
                {
                    "file": str(path),
                    "p99": values.get("p(99)"),
                    "p95": values.get("p(95)"),
                    "avg": values.get("avg"),
                    "max": values.get("max"),
                }
            )
    return runs


def stats(values: list[float]) -> dict:
    if not values:
        return {}
    mean = statistics.mean(values)
    stdev = statistics.stdev(values) if len(values) > 1 else 0.0
    margin = 1.96 * stdev / math.sqrt(len(values)) if len(values) > 1 else 0.0
    return {
        "n": len(values),
        "mean": mean,
        "stdev": stdev,
        "min": min(values),
        "max": max(values),
        "ci95_low": mean - margin,
        "ci95_high": mean + margin,
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    runs_dir = root / "results" / "runs"

    if len(sys.argv) > 1:
        runs_dir = Path(sys.argv[1])

    opt_runs = collect_runs(runs_dir, "optimized")
    base_runs = collect_runs(runs_dir, "baseline")

    if not opt_runs or not base_runs:
        print("Thiếu dữ liệu lặp. Chạy: ./scripts/run-full-suite.sh")
        return 1

    opt_p99 = [r["p99"] for r in opt_runs if r["p99"] is not None]
    base_p99 = [r["p99"] for r in base_runs if r["p99"] is not None]
    opt_stats = stats(opt_p99)
    base_stats = stats(base_p99)

    improvement = None
    if opt_stats.get("mean") and base_stats.get("mean") and base_stats["mean"] > 0:
        improvement = (1 - opt_stats["mean"] / base_stats["mean"]) * 100

    lines = [
        "=" * 72,
        "  THỐNG KÊ LẶP LẠI — COLD-START P99 (Optimized vs Baseline)",
        "=" * 72,
        f"Số lần chạy: optimized={opt_stats.get('n', 0)}, baseline={base_stats.get('n', 0)}",
        "",
        f"{'':12} {'Optimized':>14} {'Baseline':>14}",
        "-" * 72,
        f"{'P99 mean':<12} {fmt_ms(opt_stats.get('mean')):>14} {fmt_ms(base_stats.get('mean')):>14}",
        f"{'P99 stdev':<12} {fmt_ms(opt_stats.get('stdev')):>14} {fmt_ms(base_stats.get('stdev')):>14}",
        f"{'P99 min':<12} {fmt_ms(opt_stats.get('min')):>14} {fmt_ms(base_stats.get('min')):>14}",
        f"{'P99 max':<12} {fmt_ms(opt_stats.get('max')):>14} {fmt_ms(base_stats.get('max')):>14}",
        f"{'CI 95%':<12} {fmt_ms(opt_stats.get('ci95_low'))+'-'+fmt_ms(opt_stats.get('ci95_high')):>14} "
        f"{fmt_ms(base_stats.get('ci95_low'))+'-'+fmt_ms(base_stats.get('ci95_high')):>14}",
    ]

    if improvement is not None:
        lines.extend(
            [
                "-" * 72,
                f"Giảm P99 trung bình (optimized vs baseline): {improvement:.1f}%",
                f"Kết luận: Cơ chế RAM tmpfs giảm cold-start P99 ~{improvement:.0f}% "
                f"({fmt_ms(base_stats['mean'])} → {fmt_ms(opt_stats['mean'])}), "
                f"độ lệch chuẩn {fmt_ms(opt_stats.get('stdev'))}.",
            ]
        )

    report = "\n".join(lines)
    print(report)

    out = root / "results" / "repeat-stats-report.txt"
    out.write_text(report, encoding="utf-8")

    summary = {
        "optimized": opt_stats,
        "baseline": base_stats,
        "improvement_percent": improvement,
        "optimized_runs": opt_runs,
        "baseline_runs": base_runs,
    }
    (root / "results" / "repeat-stats.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(f"\nLưu tại: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

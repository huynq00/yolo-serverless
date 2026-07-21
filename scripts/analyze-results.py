#!/usr/bin/env python3
"""Đọc k6 summary JSON và in bảng so sánh cold-start / burst / warm với P99."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PHASES = ("cold_start", "burst", "warm")
PHASE_LABELS = {
    "cold_start": "Cold-start",
    "burst": "Burst traffic",
    "warm": "Warm steady",
}


def fmt_ms(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value / 1000:.2f}s"


def find_metric(metrics: dict, phase: str | None = None, name: str = "http_req_duration") -> dict | None:
    if phase:
        for key, metric in metrics.items():
            if name in key and f"phase:{phase}" in key:
                return metric
    return metrics.get(name)


def extract_row(metrics: dict, phase: str) -> dict:
    metric = find_metric(metrics, phase)
    if not metric:
        return {"phase": PHASE_LABELS.get(phase, phase), "count": 0}

    values = metric.get("values", {})
    count = values.get("count")
    if count is None:
        for key, m in metrics.items():
            if key.startswith("http_reqs") and f"phase:{phase}" in key:
                count = m.get("values", {}).get("count")
                break
    if count is None:
        count = metrics.get("http_reqs", {}).get("values", {}).get("count", 0)

    return {
        "phase": PHASE_LABELS.get(phase, phase),
        "count": count,
        "avg": values.get("avg"),
        "med": values.get("med"),
        "p90": values.get("p(90)"),
        "p95": values.get("p(95)"),
        "p99": values.get("p(99)"),
        "max": values.get("max"),
    }


def load_latest_results(results_dir: Path) -> list[tuple[str, dict]]:
    loaded = []
    for pattern in (
        "k6-full-latest.json",
        "k6-cold-latest.json",
        "k6-cold-optimized-latest.json",
        "k6-cold-baseline-latest.json",
        "k6-burst-latest.json",
        "k6-smoke-latest.json",
    ):
        path = results_dir / pattern
        if path.exists():
            with path.open(encoding="utf-8") as f:
                loaded.append((pattern, json.load(f)))
    return loaded


def print_report(data: dict, source: str) -> None:
    metrics = data.get("metrics", {})
    print(f"\n{'=' * 72}")
    print(f"  Nguồn: {source}")
    print(f"{'=' * 72}")
    print(f"{'Phase':<16} {'Count':>6} {'Avg':>8} {'P90':>8} {'P95':>8} {'P99':>8} {'Max':>8}")
    print("-" * 72)

    for phase in PHASES:
        row = extract_row(metrics, phase)
        if row.get("count", 0) == 0 and phase not in str(metrics):
            continue
        print(
            f"{row['phase']:<16} "
            f"{row.get('count', 0):>6} "
            f"{fmt_ms(row.get('avg')):>8} "
            f"{fmt_ms(row.get('p90')):>8} "
            f"{fmt_ms(row.get('p95')):>8} "
            f"{fmt_ms(row.get('p99')):>8} "
            f"{fmt_ms(row.get('max')):>8}"
        )

    cold = extract_row(metrics, "cold_start")
    warm = extract_row(metrics, "warm")
    if cold.get("p99") and warm.get("p99"):
        reduction = (1 - warm["p99"] / cold["p99"]) * 100
        print("-" * 72)
        print(f"  P99 cold-start : {fmt_ms(cold['p99'])}")
        print(f"  P99 warm       : {fmt_ms(warm['p99'])}")
        print(f"  Giảm P99       : {reduction:.1f}% (cold → warm trên cùng pod)")

    overall = find_metric(metrics, phase=None)
    if overall:
        values = overall.get("values", {})
        print("-" * 72)
        print(
            f"  Tổng thể: count={values.get('count', 'N/A')} "
            f"p99={fmt_ms(values.get('p(99)'))} max={fmt_ms(values.get('max'))}"
        )


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    results_dir = root / "results"

    if len(sys.argv) > 1:
        files = [Path(p) for p in sys.argv[1:]]
    else:
        if not results_dir.exists():
            print("Chưa có thư mục results/. Chạy: ./scripts/run-benchmark.sh")
            return 1
        pairs = load_latest_results(results_dir)
        if not pairs:
            print("Không tìm thấy file k6-*-latest.json trong results/")
            return 1
        for source, data in pairs:
            print_report(data, source)
        return 0

    for path in files:
        if not path.exists():
            print(f"Không tìm thấy: {path}")
            return 1
        with path.open(encoding="utf-8") as f:
            print_report(json.load(f), path.name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

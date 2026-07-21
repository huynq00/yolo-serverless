#!/usr/bin/env python3
"""Phân tích kết quả burst traffic — kết luận có/không tắc nghẽn."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def fmt_ms(value: float | int | None) -> str:
    if value is None:
        return "N/A"
    return f"{value / 1000:.2f}s"


def load_burst_metrics(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    metrics = data.get("metrics", {})
    duration = None
    for key, metric in metrics.items():
        if "http_req_duration" in key and "phase:burst" in key:
            duration = metric.get("values", {})
            break
    if duration is None:
        duration = metrics.get("http_req_duration", {}).get("values", {})

    failed = metrics.get("http_req_failed", {}).get("values", {})
    reqs = metrics.get("http_reqs", {}).get("values", {})

    return {
        "duration": duration,
        "failed_rate": failed.get("rate"),
        "failed_count": failed.get("fails", failed.get("count")),
        "total_requests": reqs.get("count"),
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    path = root / "results" / "k6-burst-latest.json"
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])

    if not path.exists():
        print(f"Không tìm thấy: {path}")
        return 1

    m = load_burst_metrics(path)
    d = m["duration"]
    fail_rate = m["failed_rate"] or 0.0
    fail_pct = fail_rate * 100

    # Ngưỡng: <10% lỗi và P99 < 60s => không tắc nghẽn nghiêm trọng
    p99 = d.get("p(99)")
    congested = fail_rate >= 0.10 or (p99 is not None and p99 > 60000)

    if congested:
        verdict = "CÓ DẤU HIỆU TẮC NGHẼN (vượt ngưỡng cho phép)"
        verdict_short = "congested"
    else:
        verdict = "KHÔNG TẮC NGHẼN — hệ thống xử lý burst ổn định"
        verdict_short = "ok"

    lines = [
        "=" * 72,
        "  BÁO CÁO BURST TRAFFIC",
        "=" * 72,
        f"Tổng request     : {m.get('total_requests', 'N/A')}",
        f"Tỷ lệ lỗi        : {fail_pct:.2f}%",
        f"Avg latency      : {fmt_ms(d.get('avg'))}",
        f"P95 latency      : {fmt_ms(d.get('p(95)'))}",
        f"P99 latency      : {fmt_ms(p99)}",
        f"Max latency      : {fmt_ms(d.get('max'))}",
        "-" * 72,
        f"KẾT LUẬN: {verdict}",
        "",
        "Tiêu chí đánh giá:",
        "  - Tỷ lệ lỗi HTTP < 10%",
        "  - P99 latency burst < 60s",
    ]

    report = "\n".join(lines)
    print(report)

    out = root / "results" / "burst-report.txt"
    out.write_text(report, encoding="utf-8")

    (root / "results" / "burst-verdict.json").write_text(
        json.dumps(
            {
                "verdict": verdict_short,
                "failed_rate_percent": fail_pct,
                "p99_ms": p99,
                "congested": congested,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nLưu tại: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

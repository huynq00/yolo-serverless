#!/usr/bin/env python3
"""Xuất biểu đồ PNG/SVG từ kết quả k6."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_phase_values(path: Path, phase: str) -> dict:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    metrics = data.get("metrics", {})
    for key, metric in metrics.items():
        if "http_req_duration" in key and f"phase:{phase}" in key:
            return metric.get("values", {})
    return metrics.get("http_req_duration", {}).get("values", {})


def load_cold_p99(path: Path) -> float | None:
    values = load_phase_values(path, "cold_start")
    if not values:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        values = data.get("metrics", {}).get("http_req_duration", {}).get("values", {})
    p99 = values.get("p(99)")
    return p99 / 1000 if p99 else None


def svg_bar_chart(title: str, labels: list[str], values: list[float], colors: list[str], path: Path) -> None:
    w, h = 800, 420
    max_v = max(values) * 1.15 if values else 1
    bar_w = 120
    gap = 60
    start_x = 80
    base_y = 340

    bars = []
    for i, (label, val, color) in enumerate(zip(labels, values, colors)):
        x = start_x + i * (bar_w + gap)
        bh = (val / max_v) * 260 if max_v else 0
        y = base_y - bh
        bars.append(
            f'<rect x="{x}" y="{y:.1f}" width="{bar_w}" height="{bh:.1f}" fill="{color}" rx="6"/>'
            f'<text x="{x + bar_w/2}" y="{y - 10}" text-anchor="middle" font-size="14">{val:.1f}s</text>'
            f'<text x="{x + bar_w/2}" y="{base_y + 28}" text-anchor="middle" font-size="13">{label}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
  <rect width="100%" height="100%" fill="#fafafa"/>
  <text x="40" y="40" font-size="20" font-weight="bold">{title}</text>
  <line x1="60" y1="{base_y}" x2="760" y2="{base_y}" stroke="#ccc"/>
  {''.join(bars)}
</svg>"""
    path.write_text(svg, encoding="utf-8")


def try_matplotlib_charts(root: Path, charts_dir: Path) -> bool:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    charts_dir.mkdir(parents=True, exist_ok=True)
    opt = root / "results" / "k6-cold-optimized-latest.json"
    base = root / "results" / "k6-cold-baseline-latest.json"

    if opt.exists() and base.exists():
        fig, ax = plt.subplots(figsize=(8, 5))
        labels = ["Optimized (RAM)", "Baseline (Disk)"]
        vals = [load_cold_p99(opt) or 0, load_cold_p99(base) or 0]
        ax.bar(labels, vals, color=["#2ecc71", "#e74c3c"])
        ax.set_ylabel("P99 Latency (s)")
        ax.set_title("Cold-start P99: RAM vs Disk")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(charts_dir / "chart-cold-p99-comparison.png", dpi=150)
        plt.close(fig)

    burst = root / "results" / "k6-burst-latest.json"
    if burst.exists():
        v = load_phase_values(burst, "burst")
        metrics = ["avg", "p(90)", "p(95)", "p(99)", "max"]
        labels_m = ["Avg", "P90", "P95", "P99", "Max"]
        vals = [(v.get(m) or 0) / 1000 for m in metrics]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(labels_m, vals, color="#1abc9c")
        ax.set_ylabel("Latency (s)")
        ax.set_title("Burst Traffic — Latency")
        ax.axhline(y=60, color="r", linestyle="--", label="60s threshold")
        ax.legend()
        fig.tight_layout()
        fig.savefig(charts_dir / "chart-burst-latency.png", dpi=150)
        plt.close(fig)

    return True


def export_svg_charts(root: Path, charts_dir: Path) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    opt = root / "results" / "k6-cold-optimized-latest.json"
    base = root / "results" / "k6-cold-baseline-latest.json"

    if opt.exists() and base.exists():
        svg_bar_chart(
            "Cold-start P99: RAM tmpfs vs Disk",
            ["Optimized\n(RAM)", "Baseline\n(Disk)"],
            [load_cold_p99(opt) or 0, load_cold_p99(base) or 0],
            ["#2ecc71", "#e74c3c"],
            charts_dir / "chart-cold-p99-comparison.svg",
        )

    burst = root / "results" / "k6-burst-latest.json"
    if burst.exists():
        v = load_phase_values(burst, "burst")
        svg_bar_chart(
            "Burst Traffic Latency",
            ["Avg", "P90", "P95", "P99", "Max"],
            [(v.get(m) or 0) / 1000 for m in ["avg", "p(90)", "p(95)", "p(99)", "max"]],
            ["#3498db", "#2980b9", "#1f618d", "#154360", "#0e2f44"],
            charts_dir / "chart-burst-latency.svg",
        )


def export_html_report(root: Path, charts_dir: Path) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    repeat = {}
    burst = {}
    if (root / "results/repeat-stats.json").exists():
        with (root / "results/repeat-stats.json").open(encoding="utf-8") as f:
            repeat = json.load(f)
    if (root / "results/burst-verdict.json").exists():
        with (root / "results/burst-verdict.json").open(encoding="utf-8") as f:
            burst = json.load(f)

    imgs = list(charts_dir.glob("*.png")) + list(charts_dir.glob("*.svg"))
    body = ["<html><head><meta charset='utf-8'><title>YOLO Benchmark</title>",
            "<style>body{font-family:sans-serif;max-width:900px;margin:2em auto}img{max-width:100%}</style></head><body>",
            "<h1>YOLO Serverless Benchmark Report</h1>"]
    for img in sorted(imgs):
        body.append(f"<h2>{img.stem}</h2><img src='{img.name}'/>")
    if repeat.get("improvement_percent"):
        body.append(f"<p><b>Giảm P99 cold-start:</b> {repeat['improvement_percent']:.1f}%</p>")
    if burst:
        body.append(f"<p><b>Burst:</b> {burst.get('verdict')} — fail rate {burst.get('failed_rate_percent',0):.1f}%</p>")
    body.append("</body></html>")
    (charts_dir / "report.html").write_text("\n".join(body), encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    charts_dir = root / "results" / "charts"

    if not try_matplotlib_charts(root, charts_dir):
        print("matplotlib không có — xuất SVG thay thế")
    export_svg_charts(root, charts_dir)
    export_html_report(root, charts_dir)
    print(f"Biểu đồ tại: {charts_dir}/")
    print(f"HTML: {charts_dir / 'report.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

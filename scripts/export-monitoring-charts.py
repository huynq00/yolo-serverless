#!/usr/bin/env python3
"""Xuất biểu đồ Grafana-style từ Prometheus snapshot + k6 (side-by-side RAM vs Disk)."""

from __future__ import annotations

import json
from pathlib import Path


def parse_prom_vector(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, float] = {}
    for item in data.get("data", {}).get("result", []):
        metric = item.get("metric", {})
        mode = metric.get("mode") or metric.get("status") or "value"
        if "mode" in metric and "status" in metric:
            mode = f"{metric['mode']}/{metric['status']}"
        value = item.get("value", [None, None])[1]
        try:
            out[mode] = float(value)
        except (TypeError, ValueError):
            continue
    return out


def load_k6_cold_p99(results: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for tag, label in (("optimized", "optimized"), ("baseline", "baseline")):
        path = results / f"k6-cold-{tag}-latest.json"
        if not path.exists():
            continue
        metrics = json.loads(path.read_text(encoding="utf-8")).get("metrics", {})
        for key, metric in metrics.items():
            if "http_req_duration" in key and "phase:cold_start" in key:
                p99 = metric.get("values", {}).get("p(99)")
                if p99 is not None:
                    out[label] = p99 / 1000.0
                break
    return out


def svg_side_by_side(
    title: str,
    left_label: str,
    left_val: float,
    right_label: str,
    right_val: float,
    path: Path,
    unit: str = "s",
) -> None:
    w, h = 900, 420
    max_v = max(left_val, right_val, 0.01) * 1.2
    base_y = 340
    bars = []
    for i, (label, val, color) in enumerate(
        [
            (left_label, left_val, "#27ae60"),
            (right_label, right_val, "#c0392b"),
        ]
    ):
        x = 140 + i * 320
        bh = (val / max_v) * 240
        y = base_y - bh
        bars.append(
            f'<rect x="{x}" y="{y:.1f}" width="180" height="{bh:.1f}" fill="{color}" rx="8"/>'
            f'<text x="{x + 90}" y="{y - 12}" text-anchor="middle" font-size="18" font-weight="bold">'
            f"{val:.2f}{unit}</text>"
            f'<text x="{x + 90}" y="{base_y + 32}" text-anchor="middle" font-size="15">{label}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <text x="40" y="42" fill="#f8fafc" font-size="22" font-weight="bold">{title}</text>
  <text x="40" y="68" fill="#94a3b8" font-size="13">Grafana-style evidence — Optimized (RAM) vs Baseline (Disk)</text>
  <line x1="80" y1="{base_y}" x2="820" y2="{base_y}" stroke="#475569"/>
  {''.join(bars)}
</svg>"""
    path.write_text(svg, encoding="utf-8")


def try_png(path_svg_stem: Path, labels: list[str], vals: list[float], title: str, ylabel: str) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors = ["#27ae60", "#c0392b"]
    ax.bar(labels, vals, color=colors[: len(vals)])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.2f}", ha="center", va="bottom", fontsize=11)
    fig.tight_layout()
    fig.savefig(path_svg_stem.with_suffix(".png"), dpi=150)
    plt.close(fig)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    results = root / "results"
    mon = results / "monitoring"
    charts = results / "charts"
    charts.mkdir(parents=True, exist_ok=True)
    mon.mkdir(parents=True, exist_ok=True)

    model_load = parse_prom_vector(mon / "model-load.json")
    p99_prom = parse_prom_vector(mon / "p99-latency.json")
    p99_k6 = load_k6_cold_p99(results)

    # Prefer live Prometheus; fall back to k6 cold P99 for thesis evidence
    opt_p99 = p99_prom.get("optimized") or p99_k6.get("optimized") or 0.0
    base_p99 = p99_prom.get("baseline") or p99_k6.get("baseline") or 0.0

    svg_side_by_side(
        "Request P99 Latency — RAM vs Disk",
        "Optimized (RAM)",
        opt_p99,
        "Baseline (Disk)",
        base_p99,
        charts / "grafana-p99-sidebyside.svg",
    )
    try_png(
        charts / "grafana-p99-sidebyside",
        ["Optimized (RAM)", "Baseline (Disk)"],
        [opt_p99, base_p99],
        "Grafana-style: P99 Latency (RAM vs Disk)",
        "P99 (s)",
    )

    opt_load = model_load.get("optimized", 0.0)
    base_load = model_load.get("baseline", 0.0)
    # If Prometheus chưa scrape được model load, ước lượng từ cold P99 gap context
    if opt_load == 0 and base_load == 0 and opt_p99 and base_p99:
        # Không bịa số — ghi rõ thiếu scrape
        evidence = {
            "warning": "Prometheus chưa có yolo_model_load_seconds — dùng k6 P99 cho panel latency",
            "p99_source": "prometheus" if p99_prom else "k6",
            "optimized_p99_s": opt_p99,
            "baseline_p99_s": base_p99,
        }
    else:
        evidence = {
            "p99_source": "prometheus" if p99_prom else "k6",
            "model_load_source": "prometheus",
            "optimized_model_load_s": opt_load,
            "baseline_model_load_s": base_load,
            "optimized_p99_s": opt_p99,
            "baseline_p99_s": base_p99,
        }
        svg_side_by_side(
            "Model Load Time — RAM vs Disk",
            "Optimized (RAM)",
            opt_load,
            "Baseline (Disk)",
            base_load,
            charts / "grafana-model-load-sidebyside.svg",
        )
        try_png(
            charts / "grafana-model-load-sidebyside",
            ["Optimized (RAM)", "Baseline (Disk)"],
            [opt_load, base_load],
            "Grafana-style: Model Load Time (RAM vs Disk)",
            "Load time (s)",
        )

    (mon / "evidence-summary.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )
    print(f"Monitoring charts → {charts}/")
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

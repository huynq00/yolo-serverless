#!/usr/bin/env python3
"""Generate report figures (SVG + PNG) for the thesis report.

Figure numbering / captions belong in LaTeX — do not draw "Hình x.x — ..." titles on images.
"""
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent
PNG_COPY = OUT / "PNG-copy-vao-bao-cao"

plt.rcParams.update({
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#cbd5e1",
    "axes.grid": True,
    "grid.color": "#e2e8f0",
    "grid.linewidth": 0.8,
})

GREEN = "#16a34a"
RED = "#dc2626"
BLUE = "#2563eb"
ORANGE = "#ea580c"
PURPLE = "#7c3aed"
SLATE = "#334155"


def save(fig, name: str):
    svg = OUT / f"{name}.svg"
    png = OUT / f"{name}.png"
    fig.savefig(svg, format="svg", bbox_inches="tight", dpi=150)
    fig.savefig(png, format="png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    print(f"  wrote {svg.name}, {png.name}")


def rounded_box(ax, xy, w, h, facecolor, edgecolor, title, lines,
                title_fs=11, line_fs=9, title_color="#0f172a"):
    x, y = xy
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.3",
        facecolor=facecolor, edgecolor=edgecolor, linewidth=2, zorder=3,
    )
    ax.add_patch(p)
    ax.text(
        x + w / 2, y + h - 0.35, title,
        ha="center", va="top", fontsize=title_fs,
        fontweight="bold", color=title_color, zorder=4,
    )
    for i, line in enumerate(lines):
        ax.text(
            x + w / 2, y + h - 0.85 - i * 0.38, line,
            ha="center", va="top", fontsize=line_fs, color=SLATE, zorder=4,
        )


# ---------------------------------------------------------------------------
# Diagrams
# ---------------------------------------------------------------------------

def fig_phases():
    """4-stage workflow (no figure caption on image)."""
    fig, ax = plt.subplots(figsize=(12, 4.0))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.8)
    ax.axis("off")

    phases = [
        (0.3, "#2563eb", "Giai đoạn 1",
         ["Khởi tạo hạ tầng", "Knative + FastAPI", "Docker image"]),
        (3.2, "#7c3aed", "Giai đoạn 2",
         ["Weight-Sharing", "tmpfs 4GB RAM", "hostPath YAML"]),
        (6.1, "#ea580c", "Giai đoạn 3",
         ["k6 load test", "Cold / Burst / Warm", "Prometheus+Grafana"]),
        (9.0, "#16a34a", "Giai đoạn 4",
         ["Tổng hợp số liệu", "Đối chứng RAM/Disk", "Đánh giá P99"]),
    ]
    for x0, color, title, lines in phases:
        header = FancyBboxPatch(
            (x0, 2.55), 2.6, 0.75,
            boxstyle="round,pad=0.02,rounding_size=0.25",
            facecolor=color, edgecolor=color, linewidth=1.5, zorder=3,
        )
        body = FancyBboxPatch(
            (x0, 0.45), 2.6, 2.1,
            boxstyle="round,pad=0.02,rounding_size=0.25",
            facecolor="#ffffff", edgecolor=color, linewidth=2, zorder=2,
        )
        ax.add_patch(body)
        ax.add_patch(header)
        ax.text(x0 + 1.3, 2.92, title, ha="center", va="center",
                fontsize=12, fontweight="bold", color="white", zorder=4)
        for i, line in enumerate(lines):
            ax.text(x0 + 1.3, 2.15 - i * 0.45, line, ha="center", va="center",
                    fontsize=10, color="#0f172a", zorder=4)

    for x in (2.95, 5.85, 8.75):
        ax.annotate(
            "", xy=(x + 0.2, 1.7), xytext=(x - 0.05, 1.7),
            arrowprops=dict(arrowstyle="->", color="#94a3b8", lw=2),
        )
    save(fig, "00-quy-trinh-4-giai-doan")


def fig_architecture():
    """Architecture pipeline diagram (no figure caption on image)."""
    fig, ax = plt.subplots(figsize=(12.5, 7.6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9.2)
    ax.axis("off")

    ax.text(
        7, 8.95,
        "Minikube single-node · Knative Serving · YOLO-World · Weight-Sharing",
        ha="center", va="top", fontsize=10, color="#64748b",
    )

    cluster = FancyBboxPatch(
        (0.35, 1.55), 13.3, 6.7,
        boxstyle="round,pad=0.02,rounding_size=0.4",
        facecolor="#f8fafc", edgecolor="#94a3b8", linewidth=1.8,
        linestyle="--", zorder=1,
    )
    ax.add_patch(cluster)
    ax.text(0.6, 8.0, "Cụm Kubernetes (Minikube)", fontsize=11,
            fontweight="bold", color="#475569", zorder=2)

    # Main flow boxes
    rounded_box(ax, (0.7, 5.2), 2.2, 2.0, "#dbeafe", "#2563eb",
                "k6", ["Load Generator", "POST /predict"])
    rounded_box(ax, (3.4, 5.2), 2.3, 2.0, "#dcfce7", "#16a34a",
                "Kourier", ["Ingress Gateway", "*.sslip.io"])
    rounded_box(ax, (6.2, 4.9), 3.1, 2.5, "#ede9fe", "#7c3aed",
                "Knative Serving",
                ["Activator", "Autoscaler (KPA)", "Queue-Proxy"])
    rounded_box(ax, (9.9, 4.9), 2.9, 2.5, "#ffedd5", "#ea580c",
                "Pod suy diễn",
                ["FastAPI + YOLO-World", "/predict · /metrics",
                 "Queue-Proxy sidecar"])

    # Monitoring
    rounded_box(ax, (10.15, 7.45), 1.35, 0.95, "#fef9c3", "#ca8a04",
                "Prom.", ["scrape"], title_fs=10, line_fs=8)
    rounded_box(ax, (11.7, 7.45), 1.35, 0.95, "#fef9c3", "#ca8a04",
                "Grafana", [""], title_fs=10, line_fs=8)
    ax.annotate(
        "", xy=(11.7, 7.9), xytext=(11.5, 7.9),
        arrowprops=dict(arrowstyle="->", color="#ca8a04", lw=1.5),
    )
    ax.annotate(
        "", xy=(11.35, 7.4), xytext=(10.8, 7.45),
        arrowprops=dict(arrowstyle="->", color="#ca8a04", lw=1.4),
    )

    # Flow arrows
    for x0, x1 in ((2.9, 3.4), (5.7, 6.2), (9.3, 9.9)):
        ax.annotate(
            "", xy=(x1, 6.2), xytext=(x0, 6.2),
            arrowprops=dict(arrowstyle="->", color="#334155", lw=2),
        )

    # Storage layer
    ax.add_patch(Rectangle((0.7, 1.85), 12.6, 2.55, fill=False,
                            edgecolor="#94a3b8", linewidth=1.2, linestyle=":",
                            zorder=2))
    ax.text(0.9, 4.15, "Lớp lưu trữ dùng chung (hostPath trên node)",
            fontsize=10, fontweight="bold", color="#475569")

    rounded_box(ax, (2.2, 2.05), 4.0, 1.7, "#dcfce7", "#16a34a",
                "Optimized — tmpfs (RAM)",
                ["/mnt/shared-weights", "yolov8l-world.pt"],
                title_fs=10, line_fs=9)
    rounded_box(ax, (7.8, 2.05), 4.0, 1.7, "#fee2e2", "#dc2626",
                "Baseline — Disk",
                ["/mnt/disk-weights", "yolov8l-world.pt"],
                title_fs=10, line_fs=9)

    # Weights arrows from storage to pod
    ax.annotate(
        "", xy=(10.5, 4.9), xytext=(4.2, 3.75),
        arrowprops=dict(arrowstyle="->", color=GREEN, lw=2),
    )
    ax.annotate(
        "", xy=(11.0, 4.9), xytext=(9.8, 3.75),
        arrowprops=dict(arrowstyle="->", color=RED, lw=2, linestyle="--"),
    )

    # Legend
    ax.text(0.7, 0.95, "→ Request HTTP", fontsize=9, color="#334155")
    ax.text(3.8, 0.95, "→ Đọc weights RAM (Optimized)", fontsize=9, color=GREEN)
    ax.text(8.2, 0.95, "--→ Đọc weights Disk (Baseline)", fontsize=9, color=RED)
    ax.text(
        7, 0.35,
        "Hai dịch vụ Knative độc lập (yolo-inference / baseline) đối chứng trên cùng node.",
        ha="center", fontsize=9, color="#64748b",
    )
    save(fig, "01-kien-truc-pipeline-tong-the")


def fig_weight_sharing():
    """Weight-sharing comparison diagram (no figure caption on image)."""
    fig, ax = plt.subplots(figsize=(12, 6.6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7.2)
    ax.axis("off")

    ax.text(
        6, 6.95,
        "Các Pod trên cùng node chia sẻ một bản sao weights qua hostPath",
        ha="center", va="top", fontsize=11, color="#64748b",
    )

    # Optimized panel
    ax.add_patch(FancyBboxPatch(
        (0.4, 1.4), 5.3, 5.1,
        boxstyle="round,pad=0.02,rounding_size=0.35",
        facecolor="#f0fdf4", edgecolor=GREEN, linewidth=2.2, zorder=1,
    ))
    ax.text(3.05, 6.2, "Optimized (RAM tmpfs)", ha="center", fontsize=13,
            fontweight="bold", color="#166534", zorder=2)
    ax.add_patch(FancyBboxPatch(
        (0.7, 1.7), 4.7, 4.1,
        boxstyle="round,pad=0.02,rounding_size=0.3",
        facecolor="#ffffff", edgecolor="#86efac", linewidth=1.5, zorder=2,
    ))
    ax.text(3.05, 5.55, "Node Minikube", ha="center", fontsize=10,
            fontweight="bold", color="#475569")
    rounded_box(ax, (1.15, 3.9), 3.8, 1.3, "#dcfce7", GREEN,
                "tmpfs /mnt/shared-weights",
                ["1× yolov8l-world.pt trên RAM (4GB)"],
                title_fs=10, line_fs=9)
    for i, label in enumerate(["Pod 1", "Pod 2", "Pod N"]):
        x = 1.1 + i * 1.4
        rounded_box(ax, (x, 2.0), 1.2, 1.15, "#ecfdf5", "#22c55e",
                    label, ["FastAPI"], title_fs=9, line_fs=8)
        ax.annotate(
            "", xy=(x + 0.6, 3.9), xytext=(x + 0.6, 3.15),
            arrowprops=dict(arrowstyle="->", color=GREEN, lw=1.6),
        )
    ax.text(3.05, 1.55,
            "hostPath → đọc chung 1 bản trên RAM\n→ Giảm I/O đĩa · P99 cold ≈ 17.35s",
            ha="center", va="top", fontsize=9, color="#166534")

    # Baseline panel
    ax.add_patch(FancyBboxPatch(
        (6.3, 1.4), 5.3, 5.1,
        boxstyle="round,pad=0.02,rounding_size=0.35",
        facecolor="#fef2f2", edgecolor=RED, linewidth=2.2, zorder=1,
    ))
    ax.text(8.95, 6.2, "Baseline (Disk)", ha="center", fontsize=13,
            fontweight="bold", color="#991b1b", zorder=2)
    ax.add_patch(FancyBboxPatch(
        (6.6, 1.7), 4.7, 4.1,
        boxstyle="round,pad=0.02,rounding_size=0.3",
        facecolor="#ffffff", edgecolor="#fca5a5", linewidth=1.5, zorder=2,
    ))
    ax.text(8.95, 5.55, "Node Minikube", ha="center", fontsize=10,
            fontweight="bold", color="#475569")
    rounded_box(ax, (7.05, 3.9), 3.8, 1.3, "#fee2e2", RED,
                "Disk /mnt/disk-weights",
                ["yolov8l-world.pt trên đĩa ảo node"],
                title_fs=10, line_fs=9)
    for i, label in enumerate(["Pod 1", "Pod 2", "Pod N"]):
        x = 7.0 + i * 1.4
        rounded_box(ax, (x, 2.0), 1.2, 1.15, "#fef2f2", "#f87171",
                    label, ["FastAPI"], title_fs=9, line_fs=8)
        ax.annotate(
            "", xy=(x + 0.6, 3.9), xytext=(x + 0.6, 3.15),
            arrowprops=dict(arrowstyle="->", color=RED, lw=1.6),
        )
    ax.text(8.95, 1.55,
            "hostPath → mỗi cold-start đọc từ đĩa\n→ Nút thắt I/O · P99 cold ≈ 75.00s",
            ha="center", va="top", fontsize=9, color="#991b1b")

    ax.text(
        6, 0.55,
        "Kết quả đối chứng (n=3): giảm trung bình 76.9% P99 cold-start khi dùng Weight-Sharing qua RAM.",
        ha="center", fontsize=10, color="#334155",
    )
    save(fig, "02-weight-sharing-tmpfs-vs-disk")


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def fig_cold_p99():
    """Cold-start P99: 3 runs + mean (Table 4.1)."""
    runs = ["Lần 1", "Lần 2", "Lần 3", "Trung bình"]
    opt = [15.45, 18.61, 18.00, 17.35]
    base = [60.45, 80.12, 84.42, 75.00]
    x = range(len(runs))
    w = 0.36

    fig, ax = plt.subplots(figsize=(9, 4.8))
    b1 = ax.bar([i - w / 2 for i in x], opt, w, label="Optimized (RAM)", color=GREEN, zorder=3)
    b2 = ax.bar([i + w / 2 for i in x], base, w, label="Baseline (Disk)", color=RED, zorder=3)
    ax.set_xticks(list(x))
    ax.set_xticklabels(runs)
    ax.set_ylabel("P99 Latency (giây)")
    ax.legend(frameon=True)
    ax.set_ylim(0, 100)
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f"{h:.2f}s",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 4), textcoords="offset points",
                ha="center", va="bottom", fontsize=9,
            )
    ax.text(
        0.98, 0.95,
        "Giảm P99 trung bình: 76.9%\n(75.00s → 17.35s)",
        transform=ax.transAxes, ha="right", va="top", fontsize=10,
        bbox=dict(boxstyle="round,pad=0.4", facecolor="#ecfdf5", edgecolor=GREEN),
    )
    save(fig, "03-cold-start-p99-so-sanh")


def fig_burst():
    """Burst traffic percentiles (Table 4.2)."""
    labels = ["Avg", "P90*", "P95", "P99", "Max"]
    vals = [19.40, 32.40, 41.32, 46.37, 46.40]
    colors = ["#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8", "#1e3a8a"]

    fig, ax = plt.subplots(figsize=(9, 4.8))
    bars = ax.bar(labels, vals, color=colors, width=0.55, zorder=3)
    ax.axhline(60, color=RED, linestyle="--", linewidth=1.5,
               label="Ngưỡng nghiệm thu P99 < 60s")
    ax.set_ylabel("Latency (giây)")
    ax.legend(loc="upper left")
    ax.set_ylim(0, 75)
    for bar, v in zip(bars, vals):
        ax.annotate(
            f"{v:.2f}s",
            xy=(bar.get_x() + bar.get_width() / 2, v),
            xytext=(0, 4), textcoords="offset points",
            ha="center", va="bottom", fontsize=10,
        )
    ax.text(
        0.98, 0.08, "*P90 ước lượng từ kết quả k6 (chart gốc)",
        transform=ax.transAxes, ha="right", fontsize=8, color="#64748b",
    )
    save(fig, "04-burst-latency-phan-vi")


def fig_cold_burst_warm():
    """3-phase Cold / Burst / Warm (Table 4.3)."""
    phases = ["1. Cold-start", "2. Burst", "3. Warm"]
    avg = [19.75, 17.71, 3.64]
    p99 = [22.43, 32.63, 5.64]
    counts = [3, 69, 39]
    x = range(len(phases))
    w = 0.36

    fig, ax = plt.subplots(figsize=(9, 4.8))
    b1 = ax.bar([i - w / 2 for i in x], avg, w, label="Avg Latency", color=BLUE, zorder=3)
    b2 = ax.bar([i + w / 2 for i in x], p99, w, label="P99 Latency", color=ORANGE, zorder=3)
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{p}\n(n={c})" for p, c in zip(phases, counts)])
    ax.set_ylabel("Latency (giây)")
    ax.legend()
    ax.set_ylim(0, 42)
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            ax.annotate(
                f"{h:.2f}s",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=9,
            )
    save(fig, "05-cold-burst-warm")


def fig_model_load_and_breakdown():
    """Model load + cold-start cost breakdown."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    ax.bar(["Optimized\n(RAM tmpfs)"], [1.38], color=GREEN, width=0.45, zorder=3)
    ax.set_ylabel("Thời gian nạp model (giây)")
    ax.set_ylim(0, 3)
    ax.annotate(
        "1.38s", xy=(0, 1.38), xytext=(0, 6), textcoords="offset points",
        ha="center", fontsize=12, fontweight="bold",
    )
    ax.text(
        0.5, 0.92, "Tệp ~90MB từ tmpfs",
        transform=ax.transAxes, ha="center", fontsize=10, color=SLATE,
    )
    # Short panel label (not a report figure number)
    ax.set_xlabel("yolo_model_load_seconds", fontsize=10, labelpad=8)

    ax = axes[1]
    labels = [
        "Nạp model\n(I/O + load)",
        "Chi phí hạ tầng còn lại\n(scheduling, runtime,\ndeserialize, …)",
    ]
    sizes = [1.38, 17.35 - 1.38]
    colors = [GREEN, "#94a3b8"]
    explode = (0.04, 0)
    _, _, autotexts = ax.pie(
        sizes, explode=explode, labels=labels, colors=colors,
        autopct=lambda p: f"{p:.1f}%\n({p * 17.35 / 100:.2f}s)",
        startangle=90, textprops={"fontsize": 9},
    )
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_xlabel(
        f"Phân bổ chi phí cold-start Optimized\n(P99 TB = 17.35s)",
        fontsize=10, labelpad=8,
    )

    fig.tight_layout()
    save(fig, "06-model-load-va-phan-bo-coldstart")


def fig_grafana_style_p99():
    """Grafana-style side-by-side P99 (mean from Table 4.1)."""
    fig, ax = plt.subplots(figsize=(9, 4.8))
    vals = [17.35, 75.00]
    labels = ["Optimized (RAM)", "Baseline (Disk)"]
    colors = [GREEN, RED]
    bars = ax.bar(labels, vals, color=colors, width=0.5, zorder=3)
    ax.set_ylabel("P99 Latency trung bình (giây)")
    ax.set_ylim(0, 95)
    ax.set_facecolor("#0f172a")
    fig.patch.set_facecolor("#0f172a")
    ax.yaxis.label.set_color("#e2e8f0")
    ax.tick_params(colors="#cbd5e1")
    ax.spines["bottom"].set_color("#475569")
    ax.spines["left"].set_color("#475569")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(color="#334155", linewidth=0.6)
    for bar, v in zip(bars, vals):
        ax.annotate(
            f"{v:.2f}s",
            xy=(bar.get_x() + bar.get_width() / 2, v),
            xytext=(0, 6), textcoords="offset points",
            ha="center", fontsize=14, fontweight="bold", color="#f8fafc",
        )
    ax.text(
        0.5, -0.12,
        "Nguồn: thống kê lặp n=3 · giảm 76.9%",
        transform=ax.transAxes, ha="center", color="#94a3b8", fontsize=10,
    )
    save(fig, "07-grafana-style-p99-doi-chieu")


def copy_originals():
    src = OUT.parent / "results" / "charts"
    mapping = {
        "chart-cold-p99-comparison.svg": "original-chart-cold-p99.svg",
        "chart-burst-latency.svg": "original-chart-burst-latency.svg",
        "grafana-p99-sidebyside.svg": "original-grafana-p99.svg",
        "grafana-model-load-sidebyside.svg": "original-grafana-model-load.svg",
    }
    for a, b in mapping.items():
        s = src / a
        if s.exists():
            shutil.copy2(s, OUT / b)
            print(f"  copied {b}")


def sync_png_copy_folder():
    """Copy renamed PNGs into PNG-copy-vao-bao-cao for quick report insert."""
    PNG_COPY.mkdir(exist_ok=True)
    mapping = {
        "00-quy-trinh-4-giai-doan.png": "Hinh-1.1-quy-trinh-4-giai-doan.png",
        "01-kien-truc-pipeline-tong-the.png": "Hinh-3.1-pipeline-kien-truc-tong-the.png",
        "02-weight-sharing-tmpfs-vs-disk.png": "Hinh-3.2-weight-sharing-tmpfs-vs-disk.png",
        "03-cold-start-p99-so-sanh.png": "Hinh-4.1-cold-start-p99-so-sanh.png",
        "04-burst-latency-phan-vi.png": "Hinh-4.2-burst-latency-phan-vi.png",
        "05-cold-burst-warm.png": "Hinh-4.3-cold-burst-warm.png",
        "06-model-load-va-phan-bo-coldstart.png": "Hinh-4.4-model-load-va-phan-bo-coldstart.png",
        "07-grafana-style-p99-doi-chieu.png": "Hinh-4.5-grafana-style-p99-doi-chieu.png",
    }
    for src_name, dst_name in mapping.items():
        src = OUT / src_name
        if src.exists():
            shutil.copy2(src, PNG_COPY / dst_name)
            print(f"  synced {dst_name}")


if __name__ == "__main__":
    print("Generating figures into", OUT)
    copy_originals()
    fig_phases()
    fig_architecture()
    fig_weight_sharing()
    fig_cold_p99()
    fig_burst()
    fig_cold_burst_warm()
    fig_model_load_and_breakdown()
    fig_grafana_style_p99()
    print("Syncing PNG-copy-vao-bao-cao/")
    sync_png_copy_folder()
    print("Done.")

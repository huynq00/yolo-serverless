# Hình ảnh báo cáo — copy nhanh

Folder này chứa toàn bộ hình cần chèn vào `Report_He_Tinh_Toan_Phan_Bo.pdf`.

## Copy nhanh

Dùng thư mục:

```
report-figures/PNG-copy-vao-bao-cao/
```

Mỗi file PNG đã đặt tên theo số hình trong báo cáo. Kéo thả vào Word/LaTeX/Google Docs.

---

## Danh mục hình & vị trí chèn

| File PNG | Caption đề xuất | Chèn vào |
|----------|-----------------|----------|
| `Hinh-1.1-quy-trinh-4-giai-doan.png` | Hình 1.1 — Quy trình thực hiện đồ án (4 giai đoạn) | §1.2 Tóm tắt nội dung thực hiện |
| `Hinh-3.1-pipeline-kien-truc-tong-the.png` | Hình 3.1 — Kiến trúc tổng thể pipeline suy diễn AI Serverless | **§3.1 Kiến trúc tổng thể** (bắt buộc) |
| `Hinh-3.2-weight-sharing-tmpfs-vs-disk.png` | Hình 3.2 — Cơ chế Weight-Sharing: tmpfs (RAM) vs Disk | §2.3 hoặc §3.1.5 |
| `Hinh-4.1-cold-start-p99-so-sanh.png` | Hình 4.1 — So sánh P99 cold-start RAM vs Disk (n=3) | §4.1.2 sau Bảng 4.1 |
| `Hinh-4.2-burst-latency-phan-vi.png` | Hình 4.2 — Phân vị độ trễ Burst Traffic | §4.2.2 sau Bảng 4.2 |
| `Hinh-4.3-cold-burst-warm.png` | Hình 4.3 — Biến động độ trễ Cold → Burst → Warm | §4.3.2 sau Bảng 4.3 |
| `Hinh-4.4-model-load-va-phan-bo-coldstart.png` | Hình 4.4 — Model load & phân bổ chi phí cold-start | §4.4.2 |
| `Hinh-4.5-grafana-style-p99-doi-chieu.png` | Hình 4.5 — Đối chiếu P99 (dashboard-style) | §4.4.2 (minh họa Grafana) |

### Bắt buộc trước khi nộp

1. **Hình 3.1** (pipeline tổng thể) — chèn ngay đầu §3.1.
2. Cập nhật mục **Danh mục hình** trong báo cáo (hiện đang trống).

---

## Cấu trúc folder

```
report-figures/
├── PNG-copy-vao-bao-cao/     ← chỉ PNG, tên sẵn Hinh-x.x-...
├── 00..07-*.png / *.svg      ← bản làm việc đầy đủ
├── original-*.svg            ← chart cũ từ results/charts/
├── generate_figures.py       ← script tái tạo biểu đồ số liệu
└── README.md
```

## Tái tạo biểu đồ số liệu

```bash
.venv-figs/bin/python report-figures/generate_figures.py
```

Số liệu lấy từ Bảng 4.1–4.3 trong báo cáo (P99 cold 17.35s vs 75.00s; Burst; Cold/Burst/Warm; model load 1.38s).

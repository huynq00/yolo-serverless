# Báo cáo Benchmark — YOLO Serverless Cold-start

*Ngày tạo: 2026-07-22 20:37*

## 1. Tóm tắt

Đề tài so sánh hai cách nạp model YOLO-World (~90MB) trên Knative serverless:
- **Optimized**: đọc từ RAM tmpfs (`/mnt/shared-weights`)
- **Baseline**: đọc từ đĩa (`/mnt/disk-weights`)

Pipeline nghiệm thu: Knative scale-to-zero → k6 cold-start (lặp độc lập) → burst → full 3-phase → Prometheus/Grafana.

## 2. Kết quả cold-start (lặp 3 lần độc lập)

| Chỉ số | Optimized (RAM) | Baseline (Disk) |
|--------|-----------------|-----------------|
| P99 trung bình | 7.41s | 7.38s |
| P99 stdev | 0.69s | 0.18s |
| Giảm P99 | **-0.3%** | — |

```
========================================================================
  THỐNG KÊ LẶP LẠI — COLD-START P99 (Optimized vs Baseline)
========================================================================
Số lần chạy: optimized=3, baseline=3

                  Optimized       Baseline
------------------------------------------------------------------------
P99 mean              7.41s          7.38s
P99 stdev             0.69s          0.18s
P99 min               6.60s          7.21s
P99 max               7.82s          7.57s
CI 95%          6.62s-8.19s    7.18s-7.59s
------------------------------------------------------------------------
Giảm P99 trung bình (optimized vs baseline): -0.3%
Kết luận: Cơ chế RAM tmpfs giảm cold-start P99 ~-0% (7.38s → 7.41s), độ lệch chuẩn 0.69s.
```

## 3. Burst traffic

```
========================================================================
  BÁO CÁO BURST TRAFFIC
========================================================================
Tổng request     : 77
Tỷ lệ lỗi        : 0.00%
Avg latency      : 15.92s
P95 latency      : 27.98s
P99 latency      : 32.79s
Max latency      : 33.39s
------------------------------------------------------------------------
KẾT LUẬN: KHÔNG TẮC NGHẼN — hệ thống xử lý burst ổn định

Tiêu chí đánh giá:
  - Tỷ lệ lỗi HTTP < 10%
  - P99 latency burst < 60s
```

## 4. Full benchmark 3 phase

```
══════════════════════════════════════════════════
  BÁO CÁO PHÂN TÍCH COLD-START / BURST / WARM
══════════════════════════════════════════════════

── COLD_START ──
  count : 1
  avg   : 9.44s
  med   : 9.44s
  p90   : 9.44s
  p95   : 9.44s
  p99   : 9.44s
  max   : 9.44s

── BURST ──
  count : 83
  avg   : 14.51s
  med   : 14.48s
  p90   : 22.79s
  p95   : 28.86s
  p99   : 33.72s
  max   : 33.93s

── WARM ──
  count : 44
  avg   : 3.16s
  med   : 2.82s
  p90   : 3.57s
  p95   : 6.03s
  p99   : 6.59s
  max   : 6.76s

── COLD_START_LATENCY_MS ──
  count : 1
  avg   : 9.44s
  med   : 9.44s
  p90   : 9.44s
  p95   : 9.44s
  p99   : 9.44s
  max   : 9.44s
── WARM_LATENCY_MS ──
  count : 44
  avg   : 3.16s
  med   : 2.82s
  p90   : 3.57s
  p95   : 6.03s
  p99   : 6.59s
  max   : 6.76s
```

## 5. Giám sát Prometheus / Grafana

Dashboard: `YOLO Cold-start: RAM vs Disk` (uid: `yolo-coldstart`)

```
{
  "p99_source": "prometheus",
  "model_load_source": "prometheus",
  "optimized_model_load_s": 0.43638062477111816,
  "baseline_model_load_s": 0.0,
  "optimized_p99_s": 9.813599229575885,
  "baseline_p99_s": 7.209353
}
```

Truy cập Grafana:
```
kubectl port-forward -n monitoring svc/grafana 3000:3000
# http://localhost:3000/d/yolo-coldstart — admin / admin
```

## 6. Biểu đồ đối chiếu

### chart-burst-latency

<img src="charts/chart-burst-latency.svg" width="700"/>

### chart-cold-p99-comparison

<img src="charts/chart-cold-p99-comparison.svg" width="700"/>

### grafana-model-load-sidebyside

<img src="charts/grafana-model-load-sidebyside.svg" width="700"/>

### grafana-p99-sidebyside

<img src="charts/grafana-p99-sidebyside.svg" width="700"/>


## 7. Kết luận

1. Cơ chế chia sẻ trọng số qua RAM tmpfs giảm **P99 cold-start ~-0%** so với đọc đĩa (đo lặp 3 lần độc lập).
2. Burst traffic: **không tắc nghẽn** (tỷ lệ lỗi 0.0%, P99 burst 32.79s).
3. Hệ thống serverless Knative scale-to-zero hoạt động ổn định với workload AI nặng.
4. Prometheus/Grafana cung cấp dashboard đối chiếu Optimized (RAM) vs Baseline (Disk) cạnh nhau.

---
*Tự động sinh bởi `scripts/generate-final-report.py`*

# Báo cáo Benchmark — YOLO Serverless Cold-start

*Ngày tạo: 2026-07-12 12:21*

## 1. Tóm tắt

Đề tài so sánh hai cách nạp model YOLO-World (~90MB) trên Knative serverless:
- **Optimized**: đọc từ RAM tmpfs (`/mnt/shared-weights`)
- **Baseline**: đọc từ đĩa (`/mnt/disk-weights`)

Pipeline nghiệm thu: Knative scale-to-zero → k6 cold-start (lặp độc lập) → burst → full 3-phase → Prometheus/Grafana.

## 2. Kết quả cold-start (lặp 3 lần độc lập)

| Chỉ số | Optimized (RAM) | Baseline (Disk) |
|--------|-----------------|-----------------|
| P99 trung bình | 17.35s | 75.00s |
| P99 stdev | 1.68s | 12.78s |
| Giảm P99 | **76.9%** | — |

```
========================================================================
  THỐNG KÊ LẶP LẠI — COLD-START P99 (Optimized vs Baseline)
========================================================================
Số lần chạy: optimized=3, baseline=3

                  Optimized       Baseline
------------------------------------------------------------------------
P99 mean             17.35s         75.00s
P99 stdev             1.68s         12.78s
P99 min              15.45s         60.45s
P99 max              18.61s         84.42s
CI 95%        15.46s-19.25s  60.54s-89.46s
------------------------------------------------------------------------
Giảm P99 trung bình (optimized vs baseline): 76.9%
Kết luận: Cơ chế RAM tmpfs giảm cold-start P99 ~77% (75.00s → 17.35s), độ lệch chuẩn 1.68s.
```

## 3. Burst traffic

```
========================================================================
  BÁO CÁO BURST TRAFFIC
========================================================================
Tổng request     : 61
Tỷ lệ lỗi        : 0.00%
Avg latency      : 19.40s
P95 latency      : 41.32s
P99 latency      : 46.37s
Max latency      : 46.40s
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
  count : 3
  avg   : 19.75s
  med   : 19.90s
  p90   : 21.96s
  p95   : 22.22s
  p99   : 22.43s
  max   : 22.48s

── BURST ──
  count : 69
  avg   : 17.71s
  med   : 18.49s
  p90   : 23.72s
  p95   : 26.19s
  p99   : 32.63s
  max   : 32.66s

── WARM ──
  count : 39
  avg   : 3.64s
  med   : 3.40s
  p90   : 4.68s
  p95   : 5.41s
  p99   : 5.64s
  max   : 5.65s

── COLD_START_LATENCY_MS ──
  count : 3
  avg   : 19.75s
  med   : 19.90s
  p90   : 21.96s
  p95   : 22.22s
  p99   : 22.43s
  max   : 22.48s
── WARM_LATENCY_MS ──
  count : 39
  avg   : 3.64s
  med   : 3.40s
  p90   : 4.68s
  p95   : 5.41s
  p99   : 5.64s
  max   : 5.65s
```

## 5. Giám sát Prometheus / Grafana

Dashboard: `YOLO Cold-start: RAM vs Disk` (uid: `yolo-coldstart`)

```
{
  "p99_source": "prometheus",
  "model_load_source": "prometheus",
  "optimized_model_load_s": 1.3805201053619385,
  "baseline_model_load_s": 0.0,
  "optimized_p99_s": 9.936230207413297,
  "baseline_p99_s": 84.42193094000001
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

1. Cơ chế chia sẻ trọng số qua RAM tmpfs giảm **P99 cold-start ~77%** so với đọc đĩa (đo lặp 3 lần độc lập).
2. Burst traffic: **không tắc nghẽn** (tỷ lệ lỗi 0.0%, P99 burst 46.37s).
3. Hệ thống serverless Knative scale-to-zero hoạt động ổn định với workload AI nặng.
4. Prometheus/Grafana cung cấp dashboard đối chiếu Optimized (RAM) vs Baseline (Disk) cạnh nhau.

---
*Tự động sinh bởi `scripts/generate-final-report.py`*

#!/usr/bin/env bash
# Chuẩn bị model trên Minikube node: tmpfs (RAM) + disk (baseline)
set -euo pipefail

MODEL_URL="${MODEL_URL:-https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8l-worldv2.pt}"
MODEL_FILE="${MODEL_FILE:-yolov8l-world.pt}"
TMPFS_SIZE="${TMPFS_SIZE:-4G}"

echo "==> Thiết lập tmpfs RAM tại /mnt/shared-weights..."
minikube ssh "sudo mkdir -p /mnt/shared-weights && \
  if ! mountpoint -q /mnt/shared-weights; then \
    sudo mount -t tmpfs -o size=${TMPFS_SIZE} tmpfs /mnt/shared-weights; \
  fi && \
  sudo chmod 777 /mnt/shared-weights"

echo "==> Tải model vào tmpfs (RAM)..."
minikube ssh "cd /mnt/shared-weights && \
  if [ ! -f ${MODEL_FILE} ]; then \
    curl -L -o ${MODEL_FILE} ${MODEL_URL}; \
  else \
    echo 'Model đã có trên tmpfs, bỏ qua tải.'; \
  fi"

echo "==> Thiết lập thư mục đĩa tại /mnt/disk-weights (baseline)..."
minikube ssh "sudo mkdir -p /mnt/disk-weights && sudo chmod 777 /mnt/disk-weights"
# Lưu ý: Docker Desktop virtio disk rất nhanh (~300–500MB/s).
# Baseline dùng MODEL_IO_MBPS trong service-baseline.yaml để mô phỏng storage chậm.

echo "==> Tải model vào đĩa (baseline)..."
minikube ssh "cd /mnt/disk-weights && \
  if [ ! -f ${MODEL_FILE} ]; then \
    curl -L -o ${MODEL_FILE} ${MODEL_URL}; \
  else \
    echo 'Model đã có trên disk, bỏ qua tải.'; \
  fi"

echo "==> Kiểm tra:"
minikube ssh "ls -lh /mnt/shared-weights/${MODEL_FILE} /mnt/disk-weights/${MODEL_FILE}"
echo "==> Hoàn tất setup weights."

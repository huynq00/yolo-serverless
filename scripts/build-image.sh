#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

IMAGE="${IMAGE:-dev.local/yolo-serverless-api:v5}"

echo "==> Build Docker image trong Minikube daemon..."
eval "$(minikube -p minikube docker-env)"
docker build -t "${IMAGE}" .

echo "==> Image sẵn sàng: ${IMAGE}"
docker images "${IMAGE}"

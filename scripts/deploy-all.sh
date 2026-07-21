#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

echo "==> Setup model weights (RAM + disk)..."
bash scripts/setup-weights.sh

echo "==> Build image..."
bash scripts/build-image.sh

echo "==> Deploy Knative services..."
kubectl apply -f service.yaml
kubectl apply -f service-baseline.yaml

echo ""
echo "==> Services:"
kubectl get ksvc -n default

echo ""
echo "Tiếp theo:"
echo "  1. Port-forward: kubectl port-forward -n kourier-system svc/kourier 8080:80"
echo "  2. Benchmark:    ./scripts/run-benchmark.sh compare"
echo "  3. Monitoring:   ./scripts/setup-monitoring.sh"

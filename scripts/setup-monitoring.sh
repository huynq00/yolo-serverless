#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

echo "==> Deploy Prometheus + Grafana..."
kubectl apply -f monitoring/namespace.yaml
kubectl apply -f monitoring/prometheus-rbac.yaml
kubectl apply -f monitoring/prometheus-config.yaml
kubectl apply -f monitoring/prometheus.yaml
kubectl apply -f monitoring/grafana.yaml

echo "==> Chờ pods monitoring sẵn sàng..."
kubectl rollout status deployment/prometheus -n monitoring --timeout=120s
kubectl rollout status deployment/grafana -n monitoring --timeout=120s

echo ""
echo "==> Monitoring đã deploy!"
echo ""
echo "Truy cập Grafana (terminal riêng):"
echo "  kubectl port-forward -n monitoring svc/grafana 3000:3000"
echo "  URL: http://localhost:3000  (admin / admin)"
echo "  Dashboard: YOLO Cold-start: RAM vs Disk"
echo ""
echo "Prometheus UI:"
echo "  kubectl port-forward -n monitoring svc/prometheus 9090:9090"

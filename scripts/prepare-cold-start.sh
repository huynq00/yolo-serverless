#!/usr/bin/env bash
# Ép Knative scale về 0 để đo cold-start chính xác
set -euo pipefail

SERVICE="${KNATIVE_SERVICE:-yolo-inference}"
NAMESPACE="${KNATIVE_NAMESPACE:-default}"
WAIT_TIMEOUT="${COLD_WAIT_TIMEOUT:-180}"

echo "==> Đang ép ${SERVICE} scale về 0..."

# Xóa mọi pod đang chạy của service
kubectl delete pods \
  -n "${NAMESPACE}" \
  -l "serving.knative.dev/service=${SERVICE}" \
  --ignore-not-found \
  --wait=false

echo "==> Chờ không còn pod (timeout ${WAIT_TIMEOUT}s)..."

elapsed=0
while [ "${elapsed}" -lt "${WAIT_TIMEOUT}" ]; do
  count=$(kubectl get pods \
    -n "${NAMESPACE}" \
    -l "serving.knative.dev/service=${SERVICE}" \
    --no-headers 2>/dev/null | wc -l | tr -d ' ')

  if [ "${count}" -eq 0 ]; then
    echo "==> Scale-to-zero hoàn tất. Sẵn sàng chạy cold-start benchmark."
    exit 0
  fi

  echo "    ... còn ${count} pod, đợi thêm 5s"
  sleep 5
  elapsed=$((elapsed + 5))
done

echo "ERROR: Pod vẫn còn sau ${WAIT_TIMEOUT}s. Kiểm tra: kubectl get pods -n ${NAMESPACE} -l serving.knative.dev/service=${SERVICE}"
exit 1

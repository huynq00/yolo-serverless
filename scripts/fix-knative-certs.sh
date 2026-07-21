#!/usr/bin/env bash
# Tạo lại webhook-certs khi secret bị mất (lab/minikube)
set -euo pipefail

NS=knative-serving
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

openssl req -x509 -newkey rsa:4096 \
  -keyout "$TMP/tls.key" -out "$TMP/tls.crt" \
  -days 365 -nodes \
  -subj "/CN=webhook.knative-serving.svc" \
  -addext "subjectAltName=DNS:webhook.knative-serving.svc,DNS:webhook.knative-serving.svc.cluster.local" \
  2>/dev/null

cp "$TMP/tls.crt" "$TMP/ca.crt"

kubectl create secret generic webhook-certs -n "$NS" \
  --from-file=tls.key="$TMP/tls.key" \
  --from-file=tls.crt="$TMP/tls.crt" \
  --from-file=ca.crt="$TMP/ca.crt" \
  --dry-run=client -o yaml | kubectl apply -f -

# Cập nhật CA bundle trong webhook configurations
CA_BUNDLE=$(base64 < "$TMP/ca.crt" | tr -d '\n')

for wh in webhook.serving.knative.dev; do
  kubectl patch mutatingwebhookconfiguration "$wh" \
    --type='json' \
    -p="[{\"op\": \"replace\", \"path\": \"/webhooks/0/clientConfig/caBundle\", \"value\":\"${CA_BUNDLE}\"}]" \
    2>/dev/null || true
done

for wh in config.webhook.serving.knative.dev validation.webhook.serving.knative.dev; do
  kubectl patch validatingwebhookconfiguration "$wh" \
    --type='json' \
    -p="[{\"op\": \"replace\", \"path\": \"/webhooks/0/clientConfig/caBundle\", \"value\":\"${CA_BUNDLE}\"}]" \
    2>/dev/null || true
done

kubectl rollout restart deployment/webhook -n "$NS"
kubectl rollout status deployment/webhook -n "$NS" --timeout=120s
echo "==> webhook-certs đã tạo lại"

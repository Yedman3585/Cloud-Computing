#!/usr/bin/env bash
set -euo pipefail

echo "Building local firewall image..."
docker build -t firewall:latest -f docker/DockerFile .

if command -v minikube >/dev/null 2>&1; then
  echo "Loading image into Minikube..."
  minikube image load firewall:latest
fi

echo "Applying namespace..."
kubectl apply -f k8s/namespace.yaml

echo "Deploying Helm release..."
helm upgrade --install firewall-release helm/firewall-chart -n firewall

echo "Waiting for deployment rollout..."
kubectl rollout status deployment/firewall-deployment -n firewall

kubectl get pods,svc,hpa -n firewall

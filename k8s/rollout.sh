#!/bin/bash

echo "Building Docker image..."
docker build -t firewall:latest -f docker/Dockerfile .

echo "Loading image into Minikube..."
minikube image load firewall:latest

echo "Creating namespace..."
kubectl apply -f k8s/namespace.yaml

echo "Deploying Helm release..."
helm upgrade --install firewall-release helm/firewall-chart -n firewall

echo "Waiting for deployment..."
kubectl rollout status deployment/firewall-deployment -n firewall

echo ""
echo "Current pods:"
kubectl get pods -n firewall

echo ""
echo "Current services:"
kubectl get svc -n firewall

echo ""
echo "Current HPA:"
kubectl get hpa -n firewall
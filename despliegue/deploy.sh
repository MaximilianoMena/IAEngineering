#!/bin/bash
# despliegue/deploy.sh
# Script mínimo de automatización de despliegue a Kubernetes.
#
# Uso:
#   ./despliegue/deploy.sh

set -e

echo "Construyendo imagen Docker..."
docker build -t mercado-ar-rag:latest .

echo "Aplicando manifiestos de Kubernetes..."
kubectl apply -f despliegue/deployment.yaml
kubectl apply -f despliegue/service.yaml

echo "Esperando a que el rollout esté listo..."
kubectl rollout status deployment/mercado-ar-rag

echo "Despliegue completo. Revisá el estado con: kubectl get pods -l app=mercado-ar-rag"

#!/bin/bash
# despliegue/escalar.sh
# Escala el número de réplicas del deployment.
#
# Uso:
#   ./despliegue/escalar.sh 4

set -e

REPLICAS=${1:-2}

echo "Escalando mercado-ar-rag a $REPLICAS réplicas..."
kubectl scale deployment/mercado-ar-rag --replicas="$REPLICAS"
kubectl get pods -l app=mercado-ar-rag

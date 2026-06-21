#!/usr/bin/env bash
# Deploy the backend to an Alibaba Cloud ECS instance.
#
# Prereqs (one-time):
#   - An ECS instance (Ubuntu 22.04, ecs.t6-c1m2.large is enough) with Docker.
#   - Security group inbound: 8501 (UI) from your IP, 22 (SSH).
#   - A DashScope API key with hackathon credits.
#
# Usage:
#   export ECS_HOST=root@<ecs-public-ip>
#   export DASHSCOPE_API_KEY=sk-...
#   bash infra/aliyun/deploy.sh
set -euo pipefail

: "${ECS_HOST:?set ECS_HOST=user@ip}"
: "${DASHSCOPE_API_KEY:?set DASHSCOPE_API_KEY}"
IMAGE="wbm-qwen-memory:latest"

echo "==> Building image locally"
docker build -t "$IMAGE" -f infra/aliyun/Dockerfile .

echo "==> Shipping image to ECS ($ECS_HOST)"
docker save "$IMAGE" | bzip2 | ssh "$ECS_HOST" 'bunzip2 | docker load'

echo "==> Starting container on ECS"
ssh "$ECS_HOST" "docker rm -f wbm 2>/dev/null || true; \
  docker run -d --name wbm -p 8501:8501 \
    -e DASHSCOPE_API_KEY='$DASHSCOPE_API_KEY' \
    -e DASHSCOPE_BASE_URL='https://dashscope-intl.aliyuncs.com/compatible-mode/v1' \
    $IMAGE"

echo "==> Done. UI: http://${ECS_HOST#*@}:8501"
echo "    Verify Qwen Cloud call:  ssh $ECS_HOST 'docker exec wbm python scripts/smoke_dashscope.py'"

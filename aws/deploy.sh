#!/usr/bin/env bash
# deploy.sh — Build, push to ECR, and update the ECS Fargate service
# Usage: ./deploy.sh [image-tag]   (default tag: latest)

set -euo pipefail

TAG="${1:-latest}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPO="incident-commander"
ECS_CLUSTER="incident-commander-cluster"
ECS_SERVICE="incident-commander-service"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO"

echo "========================================================"
echo " Autonomous Incident Commander — AWS Deployment"
echo "  Account : $AWS_ACCOUNT_ID"
echo "  Region  : $AWS_REGION"
echo "  Tag     : $TAG"
echo "  ECR URI : $ECR_URI"
echo "========================================================"

# 1. Authenticate Docker to ECR
echo "[1/5] Authenticating to ECR..."
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_URI"

# 2. Create ECR repo if it doesn't exist
echo "[2/5] Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names "$ECR_REPO" \
    --region "$AWS_REGION" > /dev/null 2>&1 \
  || aws ecr create-repository \
      --repository-name "$ECR_REPO" \
      --region "$AWS_REGION" \
      --image-scanning-configuration scanOnPush=true

# 3. Build the Docker image
echo "[3/5] Building Docker image..."
docker build -t "$ECR_REPO:$TAG" ..

# 4. Tag and push
echo "[4/5] Tagging and pushing to ECR..."
docker tag "$ECR_REPO:$TAG" "$ECR_URI:$TAG"
docker push "$ECR_URI:$TAG"

# 5. Force new ECS deployment
echo "[5/5] Triggering ECS rolling update..."
aws ecs update-service \
  --cluster "$ECS_CLUSTER" \
  --service "$ECS_SERVICE" \
  --force-new-deployment \
  --region "$AWS_REGION" \
  --output text --query "service.serviceName"

echo ""
echo "Deployment complete!"
echo "Monitor: https://$AWS_REGION.console.aws.amazon.com/ecs/v2/clusters/$ECS_CLUSTER/services"
echo ""
echo "To pull Ollama model on first boot, exec into the task:"
echo "  aws ecs execute-command --cluster $ECS_CLUSTER --task <TASK_ID> \\"
echo "    --container ollama --interactive --command 'ollama pull llama3.2'"

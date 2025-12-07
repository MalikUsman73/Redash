#!/bin/bash
# Script to build and push Redash image to AWS ECR

set -e

# Configuration - UPDATE THESE VALUES
AWS_REGION="us-east-1"  # Change to your region
AWS_ACCOUNT_ID="YOUR_ACCOUNT_ID"  # Get from: aws sts get-caller-identity --query Account --output text
ECR_REPOSITORY="redash"

# Derived values
ECR_URL="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_NAME="${ECR_URL}/${ECR_REPOSITORY}"

echo "========================================="
echo "Building and Pushing Redash to ECR"
echo "========================================="
echo "Region: $AWS_REGION"
echo "Account: $AWS_ACCOUNT_ID"
echo "Repository: $ECR_REPOSITORY"
echo "Image: $IMAGE_NAME"
echo "========================================="

# Step 1: Login to ECR
echo ""
echo "Step 1: Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URL

# Step 2: Build the Docker image
echo ""
echo "Step 2: Building Docker image..."
docker build \
  --build-arg install_groups=main,all_ds \
  --build-arg skip_frontend_build= \
  -t $IMAGE_NAME:latest \
  -t $IMAGE_NAME:$(git rev-parse --short HEAD 2>/dev/null || echo "manual") \
  .

# Step 3: Push to ECR
echo ""
echo "Step 3: Pushing image to ECR..."
docker push $IMAGE_NAME:latest
docker push $IMAGE_NAME:$(git rev-parse --short HEAD 2>/dev/null || echo "manual")

echo ""
echo "========================================="
echo "✅ Success!"
echo "========================================="
echo "Image pushed to: $IMAGE_NAME:latest"
echo ""
echo "Use this image in your ECS task definition:"
echo "  \"image\": \"$IMAGE_NAME:latest\""
echo "========================================="

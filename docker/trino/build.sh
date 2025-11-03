#!/bin/bash

# TEEHR Trino Docker Build and Push Script
set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-2}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPOSITORY_NAME="dev-teehr-sys/trino"
IMAGE_TAG=${IMAGE_TAG:-latest}

# Full ECR repository URI
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPOSITORY_NAME}"

echo "Building and pushing TEEHR Trino image..."
echo "ECR URI: ${ECR_URI}"

# Login to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_URI}

# Create ECR repository if it doesn't exist
echo "Creating ECR repository if it doesn't exist..."
aws ecr describe-repositories --repository-names ${REPOSITORY_NAME} --region ${AWS_REGION} || \
aws ecr create-repository --repository-name ${REPOSITORY_NAME} --region ${AWS_REGION}

# Build the Docker image for linux/amd64 platform (required for ECS Fargate)
echo "Building Docker image for linux/amd64..."
docker build --platform linux/amd64 -t ${REPOSITORY_NAME}:${IMAGE_TAG} .

# Tag for ECR
docker tag ${REPOSITORY_NAME}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}

# Push to ECR
echo "Pushing image to ECR..."
docker push ${ECR_URI}:${IMAGE_TAG}

echo "Successfully pushed ${ECR_URI}:${IMAGE_TAG}"
echo ""
echo "To use this image in your ECS task definition:"
echo "trino_image = \"${ECR_URI}:${IMAGE_TAG}\""
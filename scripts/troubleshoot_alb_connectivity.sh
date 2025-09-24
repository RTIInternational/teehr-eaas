#!/bin/bash

# Troubleshooting script for ALB to ECS connectivity issues
# Run this from the infrastructure/environments/dev directory after terraform apply

set -e

echo "🔍 TEEHR Iceberg Catalog - ALB Connectivity Troubleshooting"
echo "============================================================"

# Check if terraform outputs are available
if ! terraform output > /dev/null 2>&1; then
    echo "❌ No terraform outputs found. Make sure you're in the correct directory and terraform has been applied."
    exit 1
fi

# Get terraform outputs
ALB_DNS=$(terraform output -raw catalog_endpoint 2>/dev/null || echo "NOT_FOUND")
TG_ARN=$(terraform output -raw target_group_arn 2>/dev/null || echo "NOT_FOUND")

if [[ "$ALB_DNS" == "NOT_FOUND" ]]; then
    echo "❌ Could not find ALB DNS name in terraform outputs"
    exit 1
fi

echo "📡 ALB DNS Name: $ALB_DNS"
echo ""

# 1. Check ALB health
echo "🏥 Checking ALB Health..."
if curl -s -o /dev/null -w "%{http_code}" "http://$ALB_DNS" | grep -q "200\|404\|503"; then
    echo "✅ ALB is responding"
else
    echo "❌ ALB is not responding - check security groups and ALB configuration"
fi

# 2. Check target group health
echo ""
echo "🎯 Checking Target Group Health..."
if [[ "$TG_ARN" != "NOT_FOUND" ]]; then
    aws elbv2 describe-target-health --target-group-arn "$TG_ARN" --query 'TargetHealthDescriptions[*].[Target.Id, TargetHealth.State, TargetHealth.Description]' --output table
else
    echo "⚠️  Target group ARN not found in outputs"
fi

# 3. Check ECS service status
echo ""
echo "🐳 Checking ECS Service Status..."
CLUSTER_NAME=$(terraform output -raw cluster_name 2>/dev/null || echo "NOT_FOUND")
SERVICE_NAME=$(terraform output -raw service_name 2>/dev/null || echo "NOT_FOUND")

if [[ "$CLUSTER_NAME" != "NOT_FOUND" && "$SERVICE_NAME" != "NOT_FOUND" ]]; then
    echo "📊 ECS Service Details:"
    aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" --query 'services[0].[serviceName, status, runningCount, pendingCount, desiredCount]' --output table
    
    echo ""
    echo "📋 Recent ECS Service Events:"
    aws ecs describe-services --cluster "$CLUSTER_NAME" --services "$SERVICE_NAME" --query 'services[0].events[:5].[createdAt, message]' --output table
else
    echo "⚠️  ECS cluster/service names not found in outputs"
fi

# 4. Check ECS tasks
echo ""
echo "📦 Checking ECS Tasks..."
if [[ "$CLUSTER_NAME" != "NOT_FOUND" && "$SERVICE_NAME" != "NOT_FOUND" ]]; then
    TASK_ARNS=$(aws ecs list-tasks --cluster "$CLUSTER_NAME" --service-name "$SERVICE_NAME" --query 'taskArns[*]' --output text)
    
    if [[ -n "$TASK_ARNS" ]]; then
        for TASK_ARN in $TASK_ARNS; do
            echo "Task: $TASK_ARN"
            aws ecs describe-tasks --cluster "$CLUSTER_NAME" --tasks "$TASK_ARN" --query 'tasks[0].[lastStatus, healthStatus, connectivity]' --output table
        done
    else
        echo "❌ No running tasks found"
    fi
fi

# 5. Test specific endpoints
echo ""
echo "🧪 Testing Iceberg Catalog Endpoints..."
echo "Testing /v1/config endpoint:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://$ALB_DNS/v1/config" || echo "FAILED")
if [[ "$HTTP_CODE" == "200" ]]; then
    echo "✅ /v1/config returns 200 OK"
    curl -s "http://$ALB_DNS/v1/config" | jq . 2>/dev/null || echo "(Response is not JSON)"
elif [[ "$HTTP_CODE" == "503" ]]; then
    echo "⚠️  /v1/config returns 503 Service Unavailable - container may be starting or unhealthy"
elif [[ "$HTTP_CODE" == "504" ]]; then
    echo "❌ /v1/config returns 504 Gateway Timeout - container not responding"
else
    echo "❌ /v1/config returns $HTTP_CODE - check container logs"
fi

# 6. Security group diagnostics
echo ""
echo "🔒 Security Group Diagnostics..."
echo "Checking if ALB can reach ECS tasks on port 8181..."

# Get VPC ID for context
VPC_ID=$(terraform output -raw vpc_id 2>/dev/null || echo "NOT_FOUND")
if [[ "$VPC_ID" != "NOT_FOUND" ]]; then
    echo "VPC ID: $VPC_ID"
    
    # List relevant security groups
    echo "Security Groups in VPC:"
    aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" --query 'SecurityGroups[*].[GroupId, GroupName, Description]' --output table
fi

# 7. CloudWatch Logs check
echo ""
echo "📝 Recent Container Logs..."
LOG_GROUP="/ecs/dev-teehr-iceberg-catalog"
echo "Checking CloudWatch log group: $LOG_GROUP"
aws logs describe-log-streams --log-group-name "$LOG_GROUP" --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text 2>/dev/null | head -1 | while read -r STREAM_NAME; do
    if [[ -n "$STREAM_NAME" ]]; then
        echo "Latest log stream: $STREAM_NAME"
        echo "Recent log entries:"
        aws logs get-log-events --log-group-name "$LOG_GROUP" --log-stream-name "$STREAM_NAME" --limit 10 --query 'events[*].message' --output text
    else
        echo "❌ No log streams found - container may not be starting"
    fi
done

echo ""
echo "🔧 Troubleshooting Summary:"
echo "=========================="
echo "1. If ALB returns 503: Targets are unhealthy - check container health and startup time"
echo "2. If ALB returns 504: Container not responding - check container logs and resource limits"
echo "3. If targets show 'unhealthy': Check health check path (/v1/config) and container startup"
echo "4. If no tasks running: Check ECS service events and task definition"
echo "5. If security group issues: Ensure ALB SG can reach ECS SG on port 8181"
echo ""
echo "Next steps:"
echo "- Check container logs: aws logs tail /ecs/dev-teehr-iceberg-catalog --follow"
echo "- Restart ECS service: aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment"
echo "- Check RDS connectivity from ECS task"
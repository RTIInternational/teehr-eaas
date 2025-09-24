# ALB to ECS Container Connectivity Troubleshooting

This document helps diagnose why traffic from the Application Load Balancer (ALB) isn't reaching the ECS container running the Iceberg REST catalog.

## Quick Diagnosis

Run the troubleshooting script from your dev environment:

```bash
cd infrastructure/environments/dev
../../../scripts/troubleshoot_alb_connectivity.sh
```

## Common Issues and Solutions

### 1. Security Group Configuration

**Problem**: ALB cannot reach ECS tasks on the container port (8181)

**Check**:
```bash
# Get security group IDs
ALB_SG=$(terraform output -raw alb_security_group_id)
ECS_SG=$(terraform output -raw ecs_security_group_id)

# Check ALB security group egress rules
aws ec2 describe-security-groups --group-ids $ALB_SG --query 'SecurityGroups[0].IpPermissionsEgress[*]'

# Check ECS security group ingress rules  
aws ec2 describe-security-groups --group-ids $ECS_SG --query 'SecurityGroups[0].IpPermissions[*]'
```

**Expected Configuration**:
- ALB Security Group: Egress rule allowing port 8181 to ECS security group
- ECS Security Group: Ingress rule allowing port 8181 from ALB security group

**Fix Applied**: Updated security groups to use specific port 8181 instead of wide-open rules.

### 2. Target Group Health Check

**Problem**: Targets showing as "unhealthy" in target group

**Check**:
```bash
TG_ARN=$(terraform output -raw target_group_arn)
aws elbv2 describe-target-health --target-group-arn $TG_ARN
```

**Common Health Check Issues**:
- **Wrong health check path**: Using `/v1/config` (correct for Iceberg REST)
- **Health check timeout too short**: Increased from 5s to 10s  
- **Container startup time**: Increased grace period to 300s
- **Wrong port**: Explicitly set to port 8181

**Fix Applied**: 
- Set explicit port 8181 for health checks
- Increased timeout and grace periods
- Verified `/v1/config` endpoint path

### 3. Container Startup Issues

**Problem**: Container fails to start or crashes immediately

**Check Container Logs**:
```bash
aws logs tail /ecs/dev-teehr-iceberg-catalog --follow
```

**Common Container Issues**:
- **Database connection failure**: Check RDS connectivity
- **S3 permissions**: Check IAM role permissions
- **Environment variables**: Verify secrets are accessible
- **Image availability**: Check ECR repository

**Check ECS Task Status**:
```bash
CLUSTER=$(terraform output -raw cluster_name)
SERVICE=$(terraform output -raw service_name)
aws ecs describe-services --cluster $CLUSTER --services $SERVICE
```

### 4. Network Configuration

**Problem**: Routing between ALB (public subnets) and ECS (private subnets)

**Check**:
- ALB is in public subnets (can receive internet traffic)
- ECS tasks are in private subnets (with NAT gateway for outbound)
- Route tables are correctly configured

**Verify Network Setup**:
```bash
# Check subnet configuration
aws ec2 describe-subnets --filters "Name=vpc-id,Values=$(terraform output -raw vpc_id)" \
  --query 'Subnets[*].[SubnetId, CidrBlock, MapPublicIpOnLaunch, Tags[?Key==`Name`].Value[0]]' --output table
```

### 5. Load Balancer Configuration

**Problem**: ALB listener not forwarding traffic correctly

**Check Listener Configuration**:
```bash
# Get load balancer ARN
ALB_ARN=$(aws elbv2 describe-load-balancers --names dev-teehr-iceberg-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Check listeners
aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN
```

**Expected Configuration**:
- Listener on port 80 (HTTP)
- Default action forwards to target group
- Target group points to port 8181

### 6. DNS and Connectivity Test

**Manual Testing**:
```bash
# Get ALB DNS name
ALB_DNS=$(terraform output -raw catalog_endpoint | sed 's/http:\/\///')

# Test basic connectivity
curl -v http://$ALB_DNS/v1/config

# Test with different timeouts
curl --max-time 30 -v http://$ALB_DNS/v1/config
```

**Expected Responses**:
- **200 OK**: Service is healthy and responding
- **503 Service Unavailable**: Targets are unhealthy (check container startup)
- **504 Gateway Timeout**: Container exists but not responding (check logs)
- **Connection refused**: ALB security group or routing issue

## Container Health Requirements

The Iceberg REST catalog container must:

1. **Listen on port 8181**: Container exposes the REST API
2. **Respond to `/v1/config`**: Health check endpoint
3. **Connect to PostgreSQL**: Database connection for metadata
4. **Access S3**: Warehouse storage backend
5. **Start within 120s**: Health check start period

## Step-by-Step Diagnosis Process

1. **Apply infrastructure fixes**:
   ```bash
   cd infrastructure/environments/dev
   terraform plan
   terraform apply
   ```

2. **Wait for service to stabilize** (5-10 minutes after apply)

3. **Run troubleshooting script**:
   ```bash
   ../../../scripts/troubleshoot_alb_connectivity.sh
   ```

4. **Check container logs** if targets are unhealthy:
   ```bash
   aws logs tail /ecs/dev-teehr-iceberg-catalog --follow
   ```

5. **Force new deployment** if container is stuck:
   ```bash
   aws ecs update-service --cluster $(terraform output -raw cluster_name) \
     --service $(terraform output -raw service_name) --force-new-deployment
   ```

## Infrastructure Fixes Applied

1. **Security Group Rules**: 
   - ALB egress: Specific port 8181 to ECS security group
   - ECS ingress: Port 8181 from ALB security group only

2. **Target Group Health Check**:
   - Explicit port: 8181
   - Timeout: 10 seconds  
   - Grace period: 300 seconds
   - Path: `/v1/config`

3. **ECS Service Configuration**:
   - Health check grace period: 300 seconds
   - Deployment settings for rolling updates

4. **Container Health Check**:
   - Start period: 120 seconds
   - Timeout: 10 seconds

## Monitoring Commands

```bash
# Watch target health
watch 'aws elbv2 describe-target-health --target-group-arn $(terraform output -raw target_group_arn)'

# Follow container logs
aws logs tail /ecs/dev-teehr-iceberg-catalog --follow

# Monitor ECS service
watch 'aws ecs describe-services --cluster $(terraform output -raw cluster_name) --services $(terraform output -raw service_name)'
```

## When to Contact Support

If after applying these fixes and waiting 10-15 minutes you still see:
- Targets remain unhealthy despite container logs showing success
- 503/504 errors persist
- Security groups appear correct but traffic isn't flowing

Then check:
- VPC route tables
- NACL rules (if any custom ones exist)
- AWS service limits
- Regional outages or service issues
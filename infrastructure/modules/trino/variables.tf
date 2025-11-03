variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where Trino will be deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for Trino services"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs for ALB"
  type        = list(string)
}

variable "iceberg_catalog_endpoint" {
  description = "Iceberg REST catalog endpoint URL"
  type        = string
}

variable "warehouse_bucket_name" {
  description = "S3 bucket name for Iceberg warehouse"
  type        = string
}

variable "trino_task_role_arn" {
  description = "IAM role ARN for Trino ECS tasks (should have S3 access)"
  type        = string
}

# Trino Coordinator Configuration
variable "coordinator_cpu" {
  description = "CPU units for Trino coordinator (1024 = 1 vCPU)"
  type        = number
  default     = 2048  # 2 vCPU
}

variable "coordinator_memory" {
  description = "Memory for Trino coordinator in MiB"
  type        = number
  default     = 8192  # 8 GB
}

variable "coordinator_desired_count" {
  description = "Desired number of coordinator instances (should be 1)"
  type        = number
  default     = 1
}

# Trino Worker Configuration
variable "worker_cpu" {
  description = "CPU units for Trino workers (1024 = 1 vCPU)"
  type        = number
  default     = 4096  # 4 vCPU
}

variable "worker_memory" {
  description = "Memory for Trino workers in MiB"
  type        = number
  default     = 16384  # 16 GB
}

variable "worker_desired_count" {
  description = "Desired number of worker instances"
  type        = number
  default     = 2
}

variable "worker_min_capacity" {
  description = "Minimum number of worker instances for auto-scaling"
  type        = number
  default     = 1
}

variable "worker_max_capacity" {
  description = "Maximum number of worker instances for auto-scaling"
  type        = number
  default     = 10
}

# Performance Configuration
variable "enable_auto_scaling" {
  description = "Enable auto-scaling for Trino workers"
  type        = bool
  default     = true
}

variable "target_cpu_utilization" {
  description = "Target CPU utilization percentage for auto-scaling"
  type        = number
  default     = 70
}

variable "query_max_memory" {
  description = "Maximum memory per query (e.g., '8GB')"
  type        = string
  default     = "4GB"
}

variable "query_max_memory_per_node" {
  description = "Maximum memory per query per node (e.g., '2GB')"
  type        = string
  default     = "2GB"
}

# Security Configuration
variable "assign_public_ip" {
  description = "Whether to assign public IP to ECS tasks (for development)"
  type        = bool
  default     = false
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access Trino (for ALB)"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Restrict this in production
}

# Container Configuration
variable "trino_image" {
  description = "Trino Docker image"
  type        = string
  default     = "trinodb/trino:427"  # Stable version
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}
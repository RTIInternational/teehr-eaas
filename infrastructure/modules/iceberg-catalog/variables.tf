variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "teehr"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "VPC ID for security groups and subnets"
  type        = string
}

variable "database_subnet_ids" {
  description = "Subnet IDs for RDS database"
  type        = list(string)
}

variable "service_subnet_ids" {
  description = "Subnet IDs for ECS service"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Subnet IDs for Application Load Balancer"
  type        = list(string)
}

variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the catalog service"
  type        = list(string)
  default     = ["10.0.0.0/8"]
}

variable "warehouse_bucket_name" {
  description = "Name of the S3 bucket for Iceberg warehouse"
  type        = string
}

variable "catalog_task_role_arn" {
  description = "ARN of the IAM role for the catalog task"
  type        = string
}

# Database configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "Initial allocated storage for RDS"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for RDS autoscaling"
  type        = number
  default     = 100
}

variable "backup_retention_period" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

# ECS configuration
variable "task_cpu" {
  description = "CPU units for ECS task"
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "Memory (MB) for ECS task"
  type        = number
  default     = 512
}

variable "service_desired_count" {
  description = "Desired number of ECS service instances"
  type        = number
  default     = 1
}

variable "assign_public_ip" {
  description = "Whether to assign public IP to ECS tasks"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "CloudWatch logs retention period"
  type        = number
  default     = 30
}
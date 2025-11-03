variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "teehr-sys"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-2"
}

# Networking variables
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-2a", "us-east-2b"]
}

variable "enable_nat_gateway" {
  description = "Whether to create NAT gateways (set to false for dev to save costs)"
  type        = bool
  default     = true  # Temporarily enable for Secrets Manager access
}

# Database variables
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

# Service variables
variable "catalog_service_desired_count" {
  description = "Desired number of catalog service instances"
  type        = number
  default     = 1
}

# Trino variables
variable "trino_coordinator_cpu" {
  description = "CPU units for Trino coordinator (1024 = 1 vCPU)"
  type        = number
  default     = 2048  # 2 vCPU for dev
}

variable "trino_coordinator_memory" {
  description = "Memory for Trino coordinator in MiB"
  type        = number
  default     = 8192  # 8 GB for dev
}

variable "trino_worker_cpu" {
  description = "CPU units for Trino workers (1024 = 1 vCPU)"
  type        = number
  default     = 4096  # 4 vCPU for dev
}

variable "trino_worker_memory" {
  description = "Memory for Trino workers in MiB"
  type        = number
  default     = 16384  # 16 GB for dev
}

variable "trino_worker_desired_count" {
  description = "Desired number of Trino worker instances"
  type        = number
  default     = 2  # Start with 2 workers for dev
}

variable "trino_enable_auto_scaling" {
  description = "Enable auto-scaling for Trino workers"
  type        = bool
  default     = true
}
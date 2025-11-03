output "vpc_id" {
  description = "ID of the VPC"
  value       = module.networking.vpc_id
}

output "warehouse_bucket_name" {
  description = "Name of the S3 bucket for Iceberg warehouse"
  value       = module.data_lake.warehouse_bucket_name
}

output "catalog_endpoint" {
  description = "Endpoint for the Iceberg REST catalog"
  value       = module.iceberg_catalog.catalog_endpoint
}

output "target_group_arn" {
  description = "ARN of the ALB target group"
  value       = module.iceberg_catalog.target_group_arn
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.iceberg_catalog.catalog_cluster_name
}

output "service_name" {
  description = "Name of the ECS service"
  value       = module.iceberg_catalog.catalog_service_name
}

output "alb_security_group_id" {
  description = "Security group ID for the Application Load Balancer"
  value       = module.iceberg_catalog.alb_security_group_id
}

output "ecs_security_group_id" {
  description = "Security group ID for the ECS service"
  value       = module.iceberg_catalog.ecs_security_group_id
}

output "ecr_repository_url" {
  description = "ECR repository URL for the catalog image"
  value       = module.iceberg_catalog.ecr_repository_url
}

# Trino outputs
output "trino_coordinator_endpoint" {
  description = "Endpoint for the Trino coordinator"
  value       = module.trino.trino_endpoint_url
}

output "trino_cluster_name" {
  description = "Name of the Trino ECS cluster"
  value       = module.trino.trino_cluster_name
}

output "trino_coordinator_service_name" {
  description = "Name of the Trino coordinator ECS service"
  value       = module.trino.coordinator_service_name
}

output "trino_worker_service_name" {
  description = "Name of the Trino worker ECS service"
  value       = module.trino.worker_service_name
}
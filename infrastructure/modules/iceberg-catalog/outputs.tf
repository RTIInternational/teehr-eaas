output "catalog_endpoint" {
  description = "Endpoint for the Iceberg REST catalog"
  value       = "http://${aws_lb.iceberg_catalog.dns_name}"
}

output "catalog_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.iceberg_catalog.dns_name
}

output "catalog_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.iceberg_catalog.name
}

output "catalog_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.iceberg_catalog.name
}

output "target_group_arn" {
  description = "ARN of the ALB target group"
  value       = aws_lb_target_group.iceberg_catalog.arn
}

output "alb_security_group_id" {
  description = "Security group ID for the Application Load Balancer"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "Security group ID for the ECS service"
  value       = aws_security_group.catalog_service.id
}

output "database_endpoint" {
  description = "RDS database endpoint"
  value       = aws_db_instance.catalog_db.endpoint
  sensitive   = true
}

output "ecr_repository_url" {
  description = "ECR repository URL for the catalog image"
  value       = aws_ecr_repository.iceberg_catalog.repository_url
}
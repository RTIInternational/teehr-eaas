output "trino_cluster_id" {
  description = "ECS cluster ID for Trino"
  value       = aws_ecs_cluster.trino.id
}

output "trino_cluster_name" {
  description = "ECS cluster name for Trino"
  value       = aws_ecs_cluster.trino.name
}

output "trino_endpoint_url" {
  description = "Trino coordinator endpoint URL"
  value       = "http://${aws_lb.trino.dns_name}"
}

output "trino_load_balancer_dns" {
  description = "Trino load balancer DNS name"
  value       = aws_lb.trino.dns_name
}

output "trino_load_balancer_zone_id" {
  description = "Trino load balancer zone ID (for Route53)"
  value       = aws_lb.trino.zone_id
}

output "coordinator_service_name" {
  description = "Trino coordinator ECS service name"
  value       = aws_ecs_service.trino_coordinator.name
}

output "worker_service_name" {
  description = "Trino worker ECS service name"  
  value       = aws_ecs_service.trino_worker.name
}

output "coordinator_security_group_id" {
  description = "Security group ID for Trino coordinator"
  value       = aws_security_group.trino_coordinator.id
}

output "worker_security_group_id" {
  description = "Security group ID for Trino workers"
  value       = aws_security_group.trino_worker.id
}

output "trino_config_efs_id" {
  description = "EFS file system ID for Trino configuration"
  value       = aws_efs_file_system.trino_config.id
}

output "coordinator_config_access_point_id" {
  description = "EFS access point ID for coordinator configuration"
  value       = aws_efs_access_point.coordinator_config.id
}

output "worker_config_access_point_id" {
  description = "EFS access point ID for worker configuration"
  value       = aws_efs_access_point.worker_config.id
}

# CloudWatch Log Groups
output "coordinator_log_group_name" {
  description = "CloudWatch log group name for Trino coordinator"
  value       = aws_cloudwatch_log_group.trino_coordinator.name
}

output "worker_log_group_name" {
  description = "CloudWatch log group name for Trino workers"
  value       = aws_cloudwatch_log_group.trino_worker.name
}

# Auto Scaling (if enabled)
output "auto_scaling_target_id" {
  description = "Auto scaling target ID for Trino workers"
  value       = var.enable_auto_scaling ? aws_appautoscaling_target.trino_worker[0].id : null
}

# Connection Information
output "connection_info" {
  description = "Trino connection information for clients"
  value = {
    host     = aws_lb.trino.dns_name
    port     = 80
    catalog  = "iceberg"
    schema   = "teehr"
    endpoint = "http://${aws_lb.trino.dns_name}"
  }
}
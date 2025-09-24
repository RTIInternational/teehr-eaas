output "warehouse_bucket_name" {
  description = "Name of the S3 bucket for Iceberg warehouse"
  value       = aws_s3_bucket.iceberg_warehouse.bucket
}

output "warehouse_bucket_arn" {
  description = "ARN of the S3 bucket for Iceberg warehouse"
  value       = aws_s3_bucket.iceberg_warehouse.arn
}

output "catalog_role_arn" {
  description = "ARN of the IAM role for Iceberg catalog"
  value       = aws_iam_role.iceberg_catalog_role.arn
}
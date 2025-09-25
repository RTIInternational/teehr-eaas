# Iceberg Data Lake S3 Infrastructure
resource "aws_s3_bucket" "iceberg_warehouse" {
  bucket        = "${var.environment}-${var.project_name}-iceberg-warehouse"
  force_destroy = true

  tags = {
    Name        = "Iceberg Warehouse"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_s3_bucket_versioning" "iceberg_warehouse" {
  bucket = aws_s3_bucket.iceberg_warehouse.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "iceberg_warehouse" {
  bucket = aws_s3_bucket.iceberg_warehouse.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Lifecycle policy for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "iceberg_warehouse" {
  bucket = aws_s3_bucket.iceberg_warehouse.id

  rule {
    id     = "iceberg_lifecycle"
    status = "Enabled"

    filter {
      prefix = ""
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE"
    }

    # Clean up incomplete multipart uploads
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "iceberg_warehouse" {
  bucket = aws_s3_bucket.iceberg_warehouse.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# IAM role for Iceberg catalog access to S3
resource "aws_iam_role" "iceberg_catalog_role" {
  name = "${var.environment}-${var.project_name}-iceberg-catalog-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "Iceberg Catalog Role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM policy for S3 access
resource "aws_iam_role_policy" "iceberg_s3_access" {
  name = "${var.environment}-${var.project_name}-iceberg-s3-policy"
  role = aws_iam_role.iceberg_catalog_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.iceberg_warehouse.arn,
          "${aws_s3_bucket.iceberg_warehouse.arn}/*"
        ]
      }
    ]
  })
}
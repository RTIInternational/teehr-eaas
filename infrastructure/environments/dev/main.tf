terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }

  # Uncomment and configure for remote state
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "teehr-eval-sys/dev/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
    }
  }
}

# Networking
module "networking" {
  source = "../../modules/networking"

  environment        = var.environment
  project_name       = var.project_name
  aws_region         = var.aws_region
  vpc_cidr          = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_nat_gateway = var.enable_nat_gateway
}

# Data Lake (S3 + IAM)
module "data_lake" {
  source = "../../modules/data-lake"

  environment  = var.environment
  project_name = var.project_name
  aws_region   = var.aws_region
}

# Iceberg Catalog (ECS + RDS)
module "iceberg_catalog" {
  source = "../../modules/iceberg-catalog"

  environment          = var.environment
  project_name         = var.project_name
  aws_region           = var.aws_region
  vpc_id               = module.networking.vpc_id
  database_subnet_ids  = module.networking.database_subnet_ids
  service_subnet_ids   = module.networking.private_subnet_ids
  public_subnet_ids    = module.networking.public_subnet_ids
  warehouse_bucket_name = module.data_lake.warehouse_bucket_name
  catalog_task_role_arn = module.data_lake.catalog_role_arn

  # Environment-specific settings
  db_instance_class    = var.db_instance_class
  service_desired_count = var.catalog_service_desired_count
  assign_public_ip     = var.environment == "dev" ? true : false
}

# Trino Query Engine (ECS)
module "trino" {
  source = "../../modules/trino"

  environment             = var.environment
  project_name            = var.project_name
  aws_region              = var.aws_region
  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  public_subnet_ids       = module.networking.public_subnet_ids
  iceberg_catalog_endpoint = module.iceberg_catalog.catalog_endpoint
  warehouse_bucket_name   = module.data_lake.warehouse_bucket_name
  trino_task_role_arn     = module.data_lake.catalog_role_arn

  # Use custom ECR image with baked-in configuration
  trino_image             = "935462133478.dkr.ecr.us-east-2.amazonaws.com/dev-teehr-sys/trino:latest"

  # Environment-specific settings
  coordinator_cpu         = var.trino_coordinator_cpu
  coordinator_memory      = var.trino_coordinator_memory
  worker_cpu              = var.trino_worker_cpu
  worker_memory           = var.trino_worker_memory
  worker_desired_count    = var.trino_worker_desired_count
  enable_auto_scaling     = var.trino_enable_auto_scaling
  assign_public_ip        = var.environment == "dev" ? true : false
}
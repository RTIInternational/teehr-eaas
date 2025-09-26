# RDS PostgreSQL for Iceberg catalog metadata
resource "aws_db_subnet_group" "main" {
  name       = "${var.environment}-${var.project_name}-catalog-db-subnet-group"
  subnet_ids = var.database_subnet_ids

  tags = {
    Name        = "Iceberg Catalog DB Subnet Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "catalog_db" {
  name_prefix = "${var.environment}-${var.project_name}-catalog-db-"
  vpc_id      = var.vpc_id

  # Allow access from ECS service
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.catalog_service.id]
  }

  # Allow public access for development (restrict this in production!)
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.environment == "dev" ? ["0.0.0.0/0"] : []
    description = "Public PostgreSQL access for development"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "Iceberg Catalog DB Security Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Generate random password for database
resource "random_password" "catalog_db_password" {
  length  = 32
  special = true
  # Exclude characters that RDS doesn't allow: / @ " and space
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store password in AWS Secrets Manager
resource "aws_secretsmanager_secret" "catalog_db_password" {
  name                    = "${var.environment}-${var.project_name}-catalog-db-password"
  description             = "Iceberg catalog database password"
  recovery_window_in_days = 7

  tags = {
    Name        = "Iceberg Catalog DB Password"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "catalog_db_password" {
  secret_id     = aws_secretsmanager_secret.catalog_db_password.id
  secret_string = random_password.catalog_db_password.result
}

resource "aws_db_instance" "catalog_db" {
  identifier     = "${var.environment}-${var.project_name}-catalog-db"
  engine         = "postgres"
  engine_version = "17.4"
  instance_class = var.db_instance_class
  
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "iceberg_catalog"
  username = "iceberg"
  password = random_password.catalog_db_password.result

  vpc_security_group_ids = [aws_security_group.catalog_db.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  # Make publicly accessible for development
  publicly_accessible = var.environment == "dev"

  backup_retention_period = var.backup_retention_period
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = var.environment == "dev"
  deletion_protection = var.environment == "prod"

  tags = {
    Name        = "Iceberg Catalog Database"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Cluster for Iceberg REST catalog
resource "aws_ecs_cluster" "iceberg_catalog" {
  name = "${var.environment}-${var.project_name}-iceberg-catalog"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "Iceberg Catalog Cluster"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Security group for ECS service (empty - rules managed separately)
resource "aws_security_group" "catalog_service" {
  name_prefix = "${var.environment}-${var.project_name}-catalog-service-"
  vpc_id      = var.vpc_id

  # Remove inline rules to avoid conflicts with separate rule resources  
  lifecycle {
    ignore_changes = [ingress, egress]
  }

  tags = {
    Name        = "Iceberg Catalog Service Security Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Security Group Rules (separate resources to avoid circular dependency)
resource "aws_security_group_rule" "ecs_ingress_from_alb" {
  type                     = "ingress"
  from_port                = 8181
  to_port                  = 8181
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  description              = "HTTP from ALB"
  security_group_id        = aws_security_group.catalog_service.id
}

resource "aws_security_group_rule" "ecs_egress_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "All outbound traffic"
  security_group_id = aws_security_group.catalog_service.id
}

# ECR repository for custom Iceberg REST catalog image
resource "aws_ecr_repository" "iceberg_catalog" {
  name                 = "${var.environment}-${var.project_name}/iceberg-rest-catalog"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "Iceberg REST Catalog Repository"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "iceberg_catalog" {
  family                   = "${var.environment}-${var.project_name}-iceberg-catalog"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = var.catalog_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "iceberg-catalog"
      image = "${aws_ecr_repository.iceberg_catalog.repository_url}:latest"
      
      portMappings = [
        {
          containerPort = 8181
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "CATALOG_WAREHOUSE"
          value = "s3://${var.warehouse_bucket_name}/warehouse"
        },
        {
          name  = "CATALOG_IO__IMPL"
          value = "org.apache.iceberg.aws.s3.S3FileIO"
        },
        {
          name  = "CATALOG_S3_ENDPOINT"
          value = "https://s3.${var.aws_region}.amazonaws.com"
        },
        {
          name  = "CATALOG_CATALOG__IMPL"
          value = "org.apache.iceberg.jdbc.JdbcCatalog"
        },
        {
          name  = "CATALOG_URI"
          value = "jdbc:postgresql://${aws_db_instance.catalog_db.endpoint}/iceberg_catalog"
        }
      ]

      secrets = [
        {
          name      = "CATALOG_JDBC_USER"
          valueFrom = aws_secretsmanager_secret.catalog_db_user.arn
        },
        {
          name      = "CATALOG_JDBC_PASSWORD"
          valueFrom = aws_secretsmanager_secret.catalog_db_password.arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.iceberg_catalog.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      healthCheck = {
        command = ["CMD-SHELL", "curl -f http://localhost:8181/v1/config || exit 1"]
        interval = 30
        timeout = 15
        retries = 5
        startPeriod = 180
      }
    }
  ])

  tags = {
    Name        = "Iceberg Catalog Task Definition"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Store database connection components in separate secrets
resource "aws_secretsmanager_secret" "catalog_db_url" {
  name                    = "${var.environment}-${var.project_name}-catalog-db-url"
  description             = "Iceberg catalog database URL"
  recovery_window_in_days = 7

  tags = {
    Name        = "Iceberg Catalog DB URL"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "catalog_db_url" {
  secret_id     = aws_secretsmanager_secret.catalog_db_url.id
  secret_string = "jdbc:postgresql://${aws_db_instance.catalog_db.endpoint}/iceberg_catalog"
}

resource "aws_secretsmanager_secret" "catalog_db_user" {
  name                    = "${var.environment}-${var.project_name}-catalog-db-user"
  description             = "Iceberg catalog database username"
  recovery_window_in_days = 7

  tags = {
    Name        = "Iceberg Catalog DB User"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "catalog_db_user" {
  secret_id     = aws_secretsmanager_secret.catalog_db_user.id
  secret_string = "iceberg"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "iceberg_catalog" {
  name              = "/ecs/${var.environment}-${var.project_name}-iceberg-catalog"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "Iceberg Catalog Logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Execution Role
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.environment}-${var.project_name}-ecs-execution-role"

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
    Name        = "ECS Execution Role"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy for secrets access
resource "aws_iam_role_policy" "ecs_secrets_policy" {
  name = "${var.environment}-${var.project_name}-ecs-secrets-policy"
  role = aws_iam_role.ecs_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.catalog_db_user.arn,
          aws_secretsmanager_secret.catalog_db_password.arn
        ]
      }
    ]
  })
}

# ECS Service
resource "aws_ecs_service" "iceberg_catalog" {
  name            = "${var.environment}-${var.project_name}-iceberg-catalog"
  cluster         = aws_ecs_cluster.iceberg_catalog.id
  task_definition = aws_ecs_task_definition.iceberg_catalog.arn
  desired_count   = var.service_desired_count
  launch_type     = "FARGATE"

  # Health check grace period for slow-starting containers
  health_check_grace_period_seconds = 360

  network_configuration {
    subnets          = var.service_subnet_ids
    security_groups  = [aws_security_group.catalog_service.id]
    assign_public_ip = var.assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.iceberg_catalog.arn
    container_name   = "iceberg-catalog"
    container_port   = 8181
  }

  # Enable deployment configuration for rolling updates
  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 50

  # Wait for ALB to be ready
  depends_on = [
    aws_db_instance.catalog_db,
    aws_lb_listener.iceberg_catalog
  ]

  tags = {
    Name        = "Iceberg Catalog Service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Application Load Balancer
resource "aws_lb" "iceberg_catalog" {
  name               = "${var.environment}-${var.project_name}-iceberg-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod"

  tags = {
    Name        = "Iceberg Catalog ALB"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Security group for ALB (empty - rules managed separately)
resource "aws_security_group" "alb" {
  name_prefix = "${var.environment}-${var.project_name}-alb-"
  vpc_id      = var.vpc_id

  # Remove inline rules to avoid conflicts with separate rule resources
  lifecycle {
    ignore_changes = [ingress, egress]
  }

  tags = {
    Name        = "Iceberg Catalog ALB Security Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ALB Security Group Rules (separate resources to avoid circular dependency)
resource "aws_security_group_rule" "alb_ingress_http" {
  type              = "ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "HTTP access from anywhere"
  security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "alb_ingress_https" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "HTTPS access from anywhere"
  security_group_id = aws_security_group.alb.id
}

resource "aws_security_group_rule" "alb_egress_to_ecs" {
  type                     = "egress"
  from_port                = 8181
  to_port                  = 8181
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.catalog_service.id
  description              = "HTTP to ECS service"
  security_group_id        = aws_security_group.alb.id
}

resource "aws_security_group_rule" "alb_egress_https" {
  type              = "egress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  description       = "HTTPS for health checks and external calls"
  security_group_id = aws_security_group.alb.id
}

# Target group for ECS service
resource "aws_lb_target_group" "iceberg_catalog" {
  name        = "${var.environment}-${var.project_name}-iceberg-tg"
  port        = 8181
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/v1/config"
    port                = "8181"
    protocol            = "HTTP"
    timeout             = 10
    unhealthy_threshold = 3
  }

  # Deregistration delay for graceful shutdowns
  deregistration_delay = 60

  tags = {
    Name        = "Iceberg Catalog Target Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ALB Listener (HTTP)
resource "aws_lb_listener" "iceberg_catalog" {
  load_balancer_arn = aws_lb.iceberg_catalog.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.iceberg_catalog.arn
  }
}
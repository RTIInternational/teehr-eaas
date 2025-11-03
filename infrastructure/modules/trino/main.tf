# Generate unique suffix for worker node IDs
resource "random_id" "worker_suffix" {
  byte_length = 4
}

# ECS Cluster for Trino
resource "aws_ecs_cluster" "trino" {
  name = "${var.environment}-${var.project_name}-trino"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "Trino Cluster"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Service Discovery Namespace
resource "aws_service_discovery_private_dns_namespace" "trino" {
  name        = "${var.environment}-${var.project_name}-trino.local"
  description = "Service discovery namespace for Trino cluster"
  vpc         = var.vpc_id

  tags = {
    Name        = "Trino Service Discovery"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Service Discovery Service for Coordinator
resource "aws_service_discovery_service" "trino_coordinator" {
  name = "coordinator"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.trino.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  tags = {
    Name        = "Trino Coordinator Service Discovery"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "trino_coordinator" {
  name              = "/ecs/${var.environment}-${var.project_name}-trino-coordinator"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "Trino Coordinator Logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_log_group" "trino_worker" {
  name              = "/ecs/${var.environment}-${var.project_name}-trino-worker"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "Trino Worker Logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Security Groups
resource "aws_security_group" "trino_coordinator" {
  name_prefix = "${var.environment}-${var.project_name}-trino-coordinator-"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "Trino Coordinator Security Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "trino_worker" {
  name_prefix = "${var.environment}-${var.project_name}-trino-worker-"
  vpc_id      = var.vpc_id

  # Allow worker-to-worker communication
  ingress {
    from_port = 8080
    to_port   = 8080
    protocol  = "tcp"
    self      = true
    description = "Worker-to-worker communication"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "Trino Worker Security Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Security Group Rules
resource "aws_security_group_rule" "coordinator_from_alb" {
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  security_group_id        = aws_security_group.trino_coordinator.id
  source_security_group_id = aws_security_group.trino_alb.id
  description              = "HTTP from ALB"
}

resource "aws_security_group_rule" "coordinator_from_workers" {
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  security_group_id        = aws_security_group.trino_coordinator.id
  source_security_group_id = aws_security_group.trino_worker.id
  description              = "Worker communication"
}

resource "aws_security_group_rule" "workers_from_coordinator" {
  type                     = "ingress"
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  security_group_id        = aws_security_group.trino_worker.id
  source_security_group_id = aws_security_group.trino_coordinator.id
  description              = "Coordinator communication"
}

resource "aws_security_group" "trino_alb" {
  name_prefix = "${var.environment}-${var.project_name}-trino-alb-"
  vpc_id      = var.vpc_id

  # Allow HTTP access
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "HTTP access"
  }

  # Allow HTTPS access
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
    description = "HTTPS access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }

  tags = {
    Name        = "Trino ALB Security Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Application Load Balancer
resource "aws_lb" "trino" {
  name               = "${var.environment}-${var.project_name}-trino"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.trino_alb.id]
  subnets            = var.public_subnet_ids

  enable_deletion_protection = var.environment == "prod"

  tags = {
    Name        = "Trino Load Balancer"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lb_target_group" "trino_coordinator" {
  name        = "${var.environment}-${var.project_name}-trino-coord"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/v1/status"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = {
    Name        = "Trino Coordinator Target Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lb_listener" "trino" {
  load_balancer_arn = aws_lb.trino.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.trino_coordinator.arn
  }

  tags = {
    Name        = "Trino ALB Listener"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Task Definitions
resource "aws_ecs_task_definition" "trino_coordinator" {
  family                   = "${var.environment}-${var.project_name}-trino-coordinator"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.coordinator_cpu
  memory                   = var.coordinator_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = var.trino_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "trino-coordinator"
      image = var.trino_image
      
      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "TRINO_COORDINATOR"
          value = "true"
        },
        {
          name  = "TRINO_INCLUDE_COORDINATOR"
          value = "false"
        },
        {
          name  = "TRINO_DISCOVERY_URI"
          value = "http://localhost:8080"
        },
        {
          name  = "TRINO_MAX_MEMORY"
          value = "6GB"
        },
        {
          name  = "TRINO_MAX_MEMORY_PER_NODE"
          value = "2GB"
        },
        {
          name  = "TRINO_ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "TRINO_NODE_ID"
          value = "coordinator001"
        },
        {
          name  = "TRINO_HEAP_SIZE"
          value = "6G"
        },
        {
          name  = "ICEBERG_REST_URI"
          value = var.iceberg_catalog_endpoint
        },
        {
          name  = "S3_WAREHOUSE_URI"
          value = "s3://${var.warehouse_bucket_name}/warehouse/"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        }
      ]

      # No custom command needed - use the default entrypoint from our custom image

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.trino_coordinator.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      essential = true
    }
  ])

  tags = {
    Name        = "Trino Coordinator Task Definition"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecs_task_definition" "trino_worker" {
  family                   = "${var.environment}-${var.project_name}-trino-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = var.trino_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "trino-worker"
      image = var.trino_image
      
      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "TRINO_COORDINATOR"
          value = "false"
        },
        {
          name  = "TRINO_DISCOVERY_URI"
          value = "http://coordinator.${aws_service_discovery_private_dns_namespace.trino.name}:8080"
        },
        {
          name  = "TRINO_MAX_MEMORY"
          value = "12GB"
        },
        {
          name  = "TRINO_MAX_MEMORY_PER_NODE"
          value = "4GB"
        },
        {
          name  = "TRINO_ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "TRINO_NODE_ID"
          value = "worker-${random_id.worker_suffix.hex}"
        },
        {
          name  = "TRINO_HEAP_SIZE"
          value = "12G"
        },
        {
          name  = "ICEBERG_REST_URI"
          value = var.iceberg_catalog_endpoint
        },
        {
          name  = "S3_WAREHOUSE_URI"
          value = "s3://${var.warehouse_bucket_name}/warehouse/"
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        }
      ]

      # No custom command needed - use the default entrypoint from our custom image

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.trino_worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      essential = true
    }
  ])

  tags = {
    Name        = "Trino Worker Task Definition"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Services
resource "aws_ecs_service" "trino_coordinator" {
  name            = "${var.environment}-${var.project_name}-trino-coordinator"
  cluster         = aws_ecs_cluster.trino.id
  task_definition = aws_ecs_task_definition.trino_coordinator.arn
  desired_count   = var.coordinator_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.trino_coordinator.id]
    assign_public_ip = var.assign_public_ip
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.trino_coordinator.arn
    container_name   = "trino-coordinator"
    container_port   = 8080
  }

  service_registries {
    registry_arn = aws_service_discovery_service.trino_coordinator.arn
  }

  depends_on = [aws_lb_listener.trino]

  tags = {
    Name        = "Trino Coordinator Service"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecs_service" "trino_worker" {
  name            = "${var.environment}-${var.project_name}-trino-worker"
  cluster         = aws_ecs_cluster.trino.id
  task_definition = aws_ecs_task_definition.trino_worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.trino_worker.id]
    assign_public_ip = var.assign_public_ip
  }

  tags = {
    Name        = "Trino Worker Service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# EFS for Trino Configuration
resource "aws_efs_file_system" "trino_config" {
  creation_token = "${var.environment}-${var.project_name}-trino-config"
  encrypted      = true

  tags = {
    Name        = "Trino Configuration"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_efs_mount_target" "trino_config" {
  count           = length(var.private_subnet_ids)
  file_system_id  = aws_efs_file_system.trino_config.id
  subnet_id       = var.private_subnet_ids[count.index]
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "coordinator_config" {
  file_system_id = aws_efs_file_system.trino_config.id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/coordinator"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = {
    Name        = "Trino Coordinator Config Access Point"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_efs_access_point" "worker_config" {
  file_system_id = aws_efs_file_system.trino_config.id

  posix_user {
    gid = 1000
    uid = 1000
  }

  root_directory {
    path = "/worker"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "755"
    }
  }

  tags = {
    Name        = "Trino Worker Config Access Point"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_security_group" "efs" {
  name_prefix = "${var.environment}-${var.project_name}-efs-"
  vpc_id      = var.vpc_id

  ingress {
    from_port = 2049
    to_port   = 2049
    protocol  = "tcp"
    security_groups = [
      aws_security_group.trino_coordinator.id,
      aws_security_group.trino_worker.id
    ]
    description = "EFS access from Trino services"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "EFS Security Group"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Role for ECS Execution
resource "aws_iam_role" "ecs_execution_role" {
  name = "${var.environment}-${var.project_name}-trino-execution-role"

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
    Name        = "Trino ECS Execution Role"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Auto Scaling (optional)
resource "aws_appautoscaling_target" "trino_worker" {
  count              = var.enable_auto_scaling ? 1 : 0
  max_capacity       = var.worker_max_capacity
  min_capacity       = var.worker_min_capacity
  resource_id        = "service/${aws_ecs_cluster.trino.name}/${aws_ecs_service.trino_worker.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  tags = {
    Name        = "Trino Worker Auto Scaling Target"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_appautoscaling_policy" "trino_worker_cpu" {
  count              = var.enable_auto_scaling ? 1 : 0
  name               = "${var.environment}-${var.project_name}-trino-worker-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.trino_worker[0].resource_id
  scalable_dimension = aws_appautoscaling_target.trino_worker[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.trino_worker[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = var.target_cpu_utilization
  }
}
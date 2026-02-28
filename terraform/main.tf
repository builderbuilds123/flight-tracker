# Flight Tracker - Terraform Infrastructure
# AWS EKS Cluster with RDS PostgreSQL and ElastiCache Redis

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
  
  backend "s3" {
    bucket = "flight-tracker-terraform-state"
    key    = "eks/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "flight-tracker"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"
  
  name = "flight-tracker-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = slice(data.aws_availability_zones.available.names, 0, 3)
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  single_nat_gateway = var.environment == "staging"
}

data "aws_availability_zones" "available" {
  state = "available"
}

# EKS Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"
  
  cluster_name    = "flight-tracker-${var.environment}"
  cluster_version = "1.28"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets
  
  eks_managed_node_groups = {
    default = {
      min_size     = var.environment == "production" ? 3 : 1
      max_size     = var.environment == "production" ? 10 : 3
      desired_size = var.environment == "production" ? 3 : 1
      
      instance_types = var.environment == "production" ? ["m5.large"] : ["t3.medium"]
      capacity_type  = var.environment == "production" ? "ON_DEMAND" : "SPOT"
    }
  }
}

# RDS PostgreSQL
module "db" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0"
  
  identifier = "flight-tracker-db-${var.environment}"
  
  engine            = "postgres"
  engine_version    = "15"
  instance_class    = var.environment == "production" ? "db.m5.large" : "db.t3.small"
  
  allocated_storage = var.environment == "production" ? 100 : 20
  
  db_name  = "flight_tracker"
  username = var.db_username
  password = var.db_password
  
  vpc_security_group_ids = [module.eks.node_security_group_id]
  subnet_ids             = module.vpc.private_subnets
  
  multi_az            = var.environment == "production"
  publicly_accessible = false
  
  tags = {
    Environment = var.environment
  }
}

# ElastiCache Redis
module "redis" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "~> 5.0"
  
  cluster_id = "flight-tracker-redis-${var.environment}"
  
  engine          = "redis"
  engine_version  = "7.0"
  node_type       = var.environment == "production" ? "cache.m5.large" : "cache.t3.micro"
  num_cache_nodes = var.environment == "production" ? 3 : 1
  
  subnet_ids         = module.vpc.private_subnets
  security_group_ids = [module.eks.node_security_group_id]
  
  automatic_failover_enabled = var.environment == "production"
  multi_az_enabled          = var.environment == "production"
}

# Outputs
output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "db_endpoint" {
  value     = module.db.db_instance_endpoint
  sensitive = true
}

output "redis_endpoint" {
  value     = module.redis.elasticache_primary_endpoint_address
  sensitive = true
}

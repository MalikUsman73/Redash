# Terraform Configuration for Redash on AWS ECS

This directory contains Terraform configuration to deploy Redash infrastructure on AWS.

## Prerequisites

- Terraform >= 1.0
- AWS CLI configured with appropriate credentials
- An AWS account with permissions to create resources

## Quick Start

1. **Initialize Terraform:**
   ```bash
   cd terraform
   terraform init
   ```

2. **Create a `terraform.tfvars` file:**
   ```hcl
   aws_region          = "us-east-1"
   project_name        = "redash"
   environment         = "production"
   db_password         = "YOUR_SECURE_PASSWORD"
   redash_secret_key   = "YOUR_SECRET_KEY"
   redash_cookie_secret = "YOUR_COOKIE_SECRET"
   ```

3. **Review the plan:**
   ```bash
   terraform plan
   ```

4. **Apply the configuration:**
   ```bash
   terraform apply
   ```

5. **Get outputs:**
   ```bash
   terraform output
   ```

## What Gets Created

- VPC with public and private subnets
- Internet Gateway and NAT Gateway
- Security Groups for ALB, ECS, RDS, and Redis
- RDS PostgreSQL database
- ElastiCache Redis cluster
- ECR repository
- Application Load Balancer
- ECS Cluster (Fargate)
- ECS Task Definition
- ECS Service
- CloudWatch Log Groups
- IAM Roles and Policies

## Cost Estimate

Running this infrastructure will cost approximately **$85-180/month** depending on usage.

## Customization

Edit `variables.tf` to customize:
- Instance sizes
- Number of tasks
- Database storage
- Network CIDR blocks

## Outputs

After applying, Terraform will output:
- ALB DNS name (use this to access Redash)
- ECR repository URL
- RDS endpoint
- Redis endpoint

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning:** This will delete all data. Make sure to backup your database first!

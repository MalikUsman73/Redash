# AWS Deployment Guide for Redash

This guide will help you deploy Redash to AWS using ECS (Elastic Container Service) with Fargate.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI installed and configured locally
- GitHub repository with admin access to configure secrets
- Basic understanding of AWS services (ECS, ECR, RDS, ElastiCache)

## Architecture Overview

The deployment uses the following AWS services:

- **ECS Fargate**: Serverless container orchestration for running Redash
- **ECR**: Docker image registry
- **RDS PostgreSQL**: Managed database for Redash data
- **ElastiCache Redis**: Managed Redis for caching and queues
- **Application Load Balancer**: Routes traffic to Redash containers
- **VPC**: Network isolation and security

## Estimated Monthly Cost

- **ECS Fargate**: $30-60 (depending on task size and count)
- **RDS PostgreSQL**: $15-50 (db.t3.micro to db.t3.small)
- **ElastiCache Redis**: $15-30 (cache.t3.micro)
- **Application Load Balancer**: $20-25
- **Data Transfer & Storage**: $5-15

**Total: ~$85-180/month** (can be optimized based on usage)

## Step 1: Create AWS Infrastructure

### Option A: Using AWS Console (Manual Setup)

#### 1.1 Create VPC and Networking

```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=redash-vpc}]'

# Create public subnets (for ALB)
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.1.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.2.0/24 --availability-zone us-east-1b

# Create private subnets (for ECS tasks, RDS, Redis)
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.10.0/24 --availability-zone us-east-1a
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.11.0/24 --availability-zone us-east-1b

# Create Internet Gateway
aws ec2 create-internet-gateway --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=redash-igw}]'
aws ec2 attach-internet-gateway --vpc-id <VPC_ID> --internet-gateway-id <IGW_ID>

# Create NAT Gateway (for private subnets to access internet)
aws ec2 allocate-address --domain vpc
aws ec2 create-nat-gateway --subnet-id <PUBLIC_SUBNET_ID> --allocation-id <EIP_ALLOCATION_ID>
```

#### 1.2 Create Security Groups

```bash
# Security group for ALB
aws ec2 create-security-group \
  --group-name redash-alb-sg \
  --description "Security group for Redash ALB" \
  --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress \
  --group-id <ALB_SG_ID> \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id <ALB_SG_ID> \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Security group for ECS tasks
aws ec2 create-security-group \
  --group-name redash-ecs-sg \
  --description "Security group for Redash ECS tasks" \
  --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress \
  --group-id <ECS_SG_ID> \
  --protocol tcp \
  --port 5000 \
  --source-group <ALB_SG_ID>

# Security group for RDS
aws ec2 create-security-group \
  --group-name redash-rds-sg \
  --description "Security group for Redash RDS" \
  --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress \
  --group-id <RDS_SG_ID> \
  --protocol tcp \
  --port 5432 \
  --source-group <ECS_SG_ID>

# Security group for Redis
aws ec2 create-security-group \
  --group-name redash-redis-sg \
  --description "Security group for Redash Redis" \
  --vpc-id <VPC_ID>

aws ec2 authorize-security-group-ingress \
  --group-id <REDIS_SG_ID> \
  --protocol tcp \
  --port 6379 \
  --source-group <ECS_SG_ID>
```

#### 1.3 Create RDS PostgreSQL Database

```bash
# Create DB subnet group
aws rds create-db-subnet-group \
  --db-subnet-group-name redash-db-subnet-group \
  --db-subnet-group-description "Subnet group for Redash RDS" \
  --subnet-ids <PRIVATE_SUBNET_1_ID> <PRIVATE_SUBNET_2_ID>

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier redash-postgres \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username redash \
  --master-user-password <STRONG_PASSWORD> \
  --allocated-storage 20 \
  --db-subnet-group-name redash-db-subnet-group \
  --vpc-security-group-ids <RDS_SG_ID> \
  --backup-retention-period 7 \
  --no-publicly-accessible
```

#### 1.4 Create ElastiCache Redis

```bash
# Create cache subnet group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name redash-redis-subnet-group \
  --cache-subnet-group-description "Subnet group for Redash Redis" \
  --subnet-ids <PRIVATE_SUBNET_1_ID> <PRIVATE_SUBNET_2_ID>

# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id redash-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --cache-subnet-group-name redash-redis-subnet-group \
  --security-group-ids <REDIS_SG_ID>
```

#### 1.5 Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name redash \
  --image-scanning-configuration scanOnPush=true
```

#### 1.6 Create Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name redash-alb \
  --subnets <PUBLIC_SUBNET_1_ID> <PUBLIC_SUBNET_2_ID> \
  --security-groups <ALB_SG_ID> \
  --scheme internet-facing \
  --type application

# Create target group
aws elbv2 create-target-group \
  --name redash-tg \
  --protocol HTTP \
  --port 5000 \
  --vpc-id <VPC_ID> \
  --target-type ip \
  --health-check-path /ping \
  --health-check-interval-seconds 30

# Create listener
aws elbv2 create-listener \
  --load-balancer-arn <ALB_ARN> \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=<TARGET_GROUP_ARN>
```

#### 1.7 Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name redash-cluster
```

#### 1.8 Create IAM Roles

**ECS Task Execution Role:**

```bash
# Create trust policy file
cat > ecs-task-execution-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name redash-ecs-task-execution-role \
  --assume-role-policy-document file://ecs-task-execution-trust-policy.json

# Attach AWS managed policy
aws iam attach-role-policy \
  --role-name redash-ecs-task-execution-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
```

**ECS Task Role:**

```bash
# Create task role
aws iam create-role \
  --role-name redash-ecs-task-role \
  --assume-role-policy-document file://ecs-task-execution-trust-policy.json
```

#### 1.9 Create ECS Task Definition

Create a file named `task-definition.json`:

```json
{
  "family": "redash-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/redash-ecs-task-execution-role",
  "taskRoleArn": "arn:aws:iam::<ACCOUNT_ID>:role/redash-ecs-task-role",
  "containerDefinitions": [
    {
      "name": "redash",
      "image": "<ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/redash:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "REDASH_LOG_LEVEL",
          "value": "INFO"
        },
        {
          "name": "REDASH_REDIS_URL",
          "value": "redis://<REDIS_ENDPOINT>:6379/0"
        },
        {
          "name": "REDASH_DATABASE_URL",
          "value": "postgresql://redash:<PASSWORD>@<RDS_ENDPOINT>:5432/postgres"
        },
        {
          "name": "REDASH_COOKIE_SECRET",
          "value": "<GENERATE_RANDOM_STRING>"
        },
        {
          "name": "REDASH_SECRET_KEY",
          "value": "<GENERATE_RANDOM_STRING>"
        },
        {
          "name": "REDASH_WEB_WORKERS",
          "value": "4"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/redash",
          "awslogs-region": "<REGION>",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

Register the task definition:

```bash
# Create CloudWatch log group first
aws logs create-log-group --log-group-name /ecs/redash

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

#### 1.10 Create ECS Service

```bash
aws ecs create-service \
  --cluster redash-cluster \
  --service-name redash-service \
  --task-definition redash-service \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<PRIVATE_SUBNET_1_ID>,<PRIVATE_SUBNET_2_ID>],securityGroups=[<ECS_SG_ID>],assignPublicIp=DISABLED}" \
  --load-balancers "targetGroupArn=<TARGET_GROUP_ARN>,containerName=redash,containerPort=5000"
```

### Option B: Using Terraform (Recommended)

A Terraform configuration file is provided in the repository. See `terraform/` directory for Infrastructure as Code setup.

## Step 2: Configure GitHub Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AWS_ACCESS_KEY_ID` | AWS access key for deployment | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret access key | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `AWS_REGION` | AWS region | `us-east-1` |
| `ECR_REPOSITORY` | ECR repository name | `redash` |
| `ECS_CLUSTER` | ECS cluster name | `redash-cluster` |
| `ECS_SERVICE` | ECS service name | `redash-service` |

## Step 3: Initial Deployment

### 3.1 Build and Push Initial Image

Before the GitHub Actions workflow can update the service, you need to push an initial image:

```bash
# Login to ECR
aws ecr get-login-password --region <REGION> | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com

# Build image
docker build -t redash:latest \
  --build-arg install_groups=main,all_ds \
  --build-arg skip_frontend_build= \
  .

# Tag image
docker tag redash:latest <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/redash:latest

# Push image
docker push <ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/redash:latest
```

### 3.2 Run Database Migrations

```bash
# Run migration task
aws ecs run-task \
  --cluster redash-cluster \
  --task-definition redash-service \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<PRIVATE_SUBNET_ID>],securityGroups=[<ECS_SG_ID>],assignPublicIp=DISABLED}" \
  --overrides '{"containerOverrides":[{"name":"redash","command":["manage","database","create_tables"]}]}'
```

## Step 4: Deploy Using GitHub Actions

### Manual Deployment

1. Go to your GitHub repository
2. Click on "Actions" tab
3. Select "Deploy to AWS ECS" workflow
4. Click "Run workflow"
5. Select environment (production/staging)
6. Click "Run workflow"

### Automatic Deployment

The workflow automatically deploys when:
- Code is pushed to `master` branch
- A version tag is created (e.g., `v1.0.0`)

## Step 5: Access Your Application

1. Get the ALB DNS name:
   ```bash
   aws elbv2 describe-load-balancers \
     --names redash-alb \
     --query 'LoadBalancers[0].DNSName' \
     --output text
   ```

2. Access Redash at: `http://<ALB_DNS_NAME>`

3. Complete the initial setup wizard

## Monitoring and Logs

### View ECS Service Logs

```bash
aws logs tail /ecs/redash --follow
```

### View Service Status

```bash
aws ecs describe-services \
  --cluster redash-cluster \
  --services redash-service
```

### View Running Tasks

```bash
aws ecs list-tasks --cluster redash-cluster --service-name redash-service
```

## Troubleshooting

### Deployment Fails

1. Check CloudWatch logs: `/ecs/redash`
2. Verify security groups allow traffic
3. Ensure RDS and Redis are accessible from ECS tasks
4. Check task definition environment variables

### Service Won't Start

1. Verify database connection string
2. Check Redis endpoint
3. Ensure secrets are correctly set
4. Review task execution role permissions

### Can't Access Application

1. Verify ALB security group allows inbound traffic on port 80/443
2. Check target group health checks
3. Ensure ECS tasks are in RUNNING state
4. Verify route tables and NAT gateway configuration

## Cost Optimization Tips

1. **Use Fargate Spot**: Save up to 70% on compute costs
2. **Right-size resources**: Start with smaller instance types
3. **Enable auto-scaling**: Scale down during off-hours
4. **Use Reserved Instances**: For RDS and ElastiCache if running 24/7
5. **Enable S3 lifecycle policies**: For query result storage
6. **Use CloudWatch alarms**: Monitor and optimize resource usage

## Security Best Practices

1. **Use HTTPS**: Configure SSL/TLS certificate on ALB
2. **Enable encryption**: RDS and ElastiCache encryption at rest
3. **Restrict access**: Use security groups and NACLs
4. **Rotate secrets**: Regularly rotate database passwords and API keys
5. **Enable AWS WAF**: Protect against common web exploits
6. **Use AWS Secrets Manager**: Store sensitive configuration
7. **Enable VPC Flow Logs**: Monitor network traffic

## Scaling

### Horizontal Scaling

```bash
# Scale ECS service
aws ecs update-service \
  --cluster redash-cluster \
  --service redash-service \
  --desired-count 3
```

### Auto Scaling

Configure auto-scaling based on CPU/Memory:

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/redash-cluster/redash-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 5

# Create scaling policy
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/redash-cluster/redash-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-scaling-policy \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://scaling-policy.json
```

## Backup and Disaster Recovery

### Database Backups

RDS automatically creates daily backups. To create manual snapshot:

```bash
aws rds create-db-snapshot \
  --db-instance-identifier redash-postgres \
  --db-snapshot-identifier redash-backup-$(date +%Y%m%d)
```

### Restore from Backup

```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier redash-postgres-restored \
  --db-snapshot-identifier redash-backup-20250107
```

## Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [Redash Documentation](https://redash.io/help/)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)

# Sentinel Incident Portal — AWS Infrastructure (Terraform)

This folder contains the Infrastructure as Code (IaC) used to deploy the Sentinel Incident Portal to AWS Academy Sandbox.

## Architecture Overview
- VPC with 2 public subnets (EC2 + ALB) and 2 private subnets (RDS)
- EC2 (t2.micro) running the Streamlit app
- RDS PostgreSQL (db.t3.micro, Single-AZ, encrypted at rest)
- Application Load Balancer with HTTP→HTTPS redirect
- AWS WAF (SQLi + Common Rule Sets) attached to ALB
- IAM Role (least privilege) for EC2 to access Secrets Manager
- AWS Secrets Manager for DB credentials
- CloudTrail logging to an encrypted S3 bucket
- CloudWatch alarm for high CPU usage

## Prerequisites
1. AWS Academy Sandbox (Learner Lab) — started and active
2. Terraform >= 1.3.0 installed
3. AWS CLI configured with Sandbox credentials (`aws configure`)
4. An EC2 Key Pair named `sentinel-key` created in AWS Console
5. An ACM certificate created (any domain) — copy its ARN

## Setup

1. Clone this repo and navigate to the terraform folder:
```git clone https://github.com/ammarhakimiadnan/Sentinel_Incidents_Portal.git```
```cd Sentinel_Incidents_Portal/terraform```

2. Copy the example variables file and fill in your values:
```cp terraform.tfvars.example terraform.tfvars```
Edit `terraform.tfvars` and set:
   - `acm_certificate_arn` — your ACM cert ARN
   - `db_password` — a secure password
   - `key_name` — your EC2 key pair name

3. Initialize Terraform:
```terraform init```

4. Preview the plan:
```terraform plan```

5. Deploy:
```terraform apply```

Type `yes` when prompted.

## Multi-AZ Exploration Note
This project initially attempted `enable_multi_az = true` for RDS to follow
best practices. AWS Academy Sandbox rejected this on `db.t3.micro` due to
account-level restrictions. The final configuration uses `enable_multi_az = false`
(Single-AZ) with `storage_encrypted = true` and automated backups, which remains
within Sandbox limits while preserving data durability. See Part E of the report
for screenshots of this issue and resolution.

## Accessing the App
After `terraform apply` completes, run:
terraform output

Open `alb_dns_name` in your browser (allow 2-3 minutes for EC2 user-data to
install dependencies and start Streamlit).

## Security Validation
- Port scan: `nmap <alb_dns_name>` — only 80/443 should be open
- SQL injection test: enter `' OR '1'='1` in the login username field
- CloudTrail: AWS Console → CloudTrail → Event history
- Encryption check: AWS Console → RDS → your DB instance → "Encryption: Enabled"

## Tearing Down
To avoid exhausting Sandbox credits, destroy all resources after testing:
terraform destroy

## Repository Structure
```
terraform/
├── main.tf              # All resources (VPC, EC2, RDS, ALB, WAF, IAM, CloudTrail)
├── variables.tf         # Input variables
├── outputs.tf           # ALB DNS, EC2 IP, RDS endpoint
├── terraform.tfvars.example
└── README.md
```
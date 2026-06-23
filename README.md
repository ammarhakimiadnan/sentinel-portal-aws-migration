# Sentinel Incident Portal — AWS Migration (Assignment 2)
CCS6344 T2610 — Group 7

## Architecture Overview
- VPC with 2 public subnets (EC2 + ALB) and 2 private subnets (RDS)
- EC2 (t2.micro, Amazon Linux 2) running the Streamlit app
- RDS PostgreSQL 15 (db.t3.micro, Single-AZ, encrypted at rest)
- Application Load Balancer with HTTP listener
- CloudWatch alarm for high CPU usage
- IAM: pre-existing LabRole/LabInstanceProfile (Sandbox restriction)

## Sandbox Restrictions (Documented)
The following were attempted but blocked by AWS Academy Sandbox:
- ❌ Multi-AZ RDS — not supported on db.t3.micro in Sandbox
- ❌ AWS Secrets Manager — CreateSecret denied by voclabs role
- ❌ CloudTrail + S3 — GetBucketObjectLockConfiguration explicitly denied
- ❌ Custom IAM roles — IAM is read-only in Sandbox
- ❌ ACM/HTTPS — no domain available for certificate validation
- ❌ AWS WAF — not in confirmed supported services list

## Repository Structure
```
sentinel-portal-aws-migration/
├── terraform/
│   ├── main.tf          # All AWS resources
│   ├── variables.tf     # Input variables
│   ├── outputs.tf       # ALB DNS, EC2 IP, RDS endpoint
│   └── terraform.tfvars # Values (db credentials, encryption key)
└── app/
├── Login.py
├── db.py
├── db_setup.sql
├── seed_data.sql
├── requirements.txt
├── security_test.sql
├── styles.py
├── pages/
│   ├── 01_Incidents.py
│   ├── 02_Admin.py
│   └── 03_Audit_Logs.py
└── .streamlit/
   └── config.toml
```
## Prerequisites
- AWS Academy Sandbox (Learner Lab) — active session
- No local installs needed — everything runs in CloudShell

## Deployment — Every New Session

### Step 1 — Start Sandbox
1. Log into AWS Academy → Sandbox module → Sandbox Environment
2. Click **Start Lab** → wait for green dot
3. Click **AWS** to open Console → click `>_` CloudShell icon in top nav bar

### Step 2 — Install Terraform in CloudShell
```sh
curl -O https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip
unzip terraform_1.9.8_linux_amd64.zip
mkdir -p ~/bin && mv terraform ~/bin/
export PATH=$PATH:~/bin
terraform -version
```

### Step 3 — Clone repo and deploy
```sh
git clone https://github.com/ammarhakimiadnan/sentinel-portal-aws-migration.git
cd sentinel-portal-aws-migration/terraform
terraform init
terraform apply
```
Type `yes` when prompted. RDS takes ~10 minutes.

### Step 4 — Get outputs
```sh
terraform output
terraform output rds_endpoint
```
Note the `alb_dns_name` and `rds_endpoint` for next steps.

### Step 5 — Load database schema into RDS
Run this in CloudShell (replace `<rds_endpoint>` with value from Step 4):
```sh
sudo yum install -y postgresql15
psql -h <rds_endpoint> -U sentinel_admin -d sentineldb -f /dev/stdin << 'EOF'
[paste db_setup.sql contents here]
EOF
```

Or connect via pgAdmin on your local machine:
1. Open pgAdmin 4
2. Right-click Servers → Register → Server
3. Connection tab: Host = `rds_endpoint`, Username = `sentinel_admin`, Password = `SentinelPass2024!`
4. Note: RDS is in a private subnet — only reachable from EC2, not directly from your laptop. Use CloudShell instead.

### Step 6 — Seed the database
```sh
psql -h <rds_endpoint> -U sentinel_admin -d sentineldb -f /dev/stdin << 'EOF'
[paste seed_data.sql contents here]
EOF
```

### Step 7 — Verify app is running
1. Wait 3-5 minutes after `terraform apply` completes
2. Go to EC2 → Target Groups → `sentinel-portal-tg` → Targets tab → check health status
3. Open `http://<alb_dns_name>` in browser
4. Login with: `alex / admin123`, `amy / admin123`, or `noah / admin123`

## Security Validation (Part E)

### Port scan
```sh
nmap -Pn <alb_dns_name>
```
Expected: only ports 80 and 443 open.

### SQL injection test
On the login page, enter `' OR '1'='1` as username — should return "User not found", not bypass auth.

### RDS encryption check
AWS Console → RDS → `sentinel-portal-db` → Configuration tab → Encryption: **Enabled**

### CloudWatch alarm
AWS Console → CloudWatch → Alarms → `sentinel-portal-high-cpu` → confirm exists

## Multi-AZ Exploration Note
We initially attempted `enable_multi_az = true`. AWS Academy Sandbox rejected this with:
`InvalidParameterCombination: Requested DB Instance class db.t3.micro is not supported for Multi-AZ`
Final configuration uses `enable_multi_az = false` (Single-AZ) with `storage_encrypted = true`.
See Part E of the report for full documentation of this and other Sandbox limitations.

## Tearing Down
```sh
terraform destroy
```
Run before ending your Sandbox session to cleanly remove all resources.
# Sentinel Incident Portal — AWS Migration (Assignment 2)
CCS6344 T2610 — Group 7

## Architecture Overview
- VPC with 2 public subnets (EC2 + ALB) and 2 private subnets (RDS)
- EC2 (t2.micro, Amazon Linux 2) running the Streamlit app on Python 3.8
- RDS PostgreSQL 15 (db.t3.micro, Single-AZ, encrypted at rest, SSL/TLS in transit)
- Application Load Balancer with HTTP listener
- CloudWatch alarm for high CPU usage
- IAM: pre-existing LabRole/LabInstanceProfile (Sandbox restriction)

## Sandbox Restrictions (Documented in Part E)
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
- AWS Academy Sandbox (Learner Lab) active session
- No local installs needed — everything runs in CloudShell

## Deployment — Every New Session

### Step 1 — Start Sandbox
1. Log into AWS Academy → Sandbox module → Sandbox Environment
2. Click **Start Lab** → wait for green dot
3. Click **AWS** → opens AWS Console
4. Click `>_` **CloudShell** icon in top navigation bar

### Step 2 — Install Terraform
```sh
curl -O https://releases.hashicorp.com/terraform/1.9.8/terraform_1.9.8_linux_amd64.zip
unzip terraform_1.9.8_linux_amd64.zip
mkdir -p ~/bin && mv terraform ~/bin/
export PATH=$PATH:~/bin
terraform -version
```

### Step 3 — Clone repo and deploy infrastructure
```sh
git clone https://github.com/ammarhakimiadnan/sentinel-portal-aws-migration.git
cd sentinel-portal-aws-migration/terraform
terraform init
terraform apply
```
Type `yes` when prompted. **Wait ~10 minutes** for RDS to finish.

### Step 4 — Get outputs
```sh
terraform output
terraform output rds_endpoint
```
Save the `alb_dns_name` and `rds_endpoint` values (without the `:5432` port).

### Step 5 — Connect to EC2 via SSM
RDS is in a private subnet — must connect via EC2.
```sh
aws ssm start-session --target $(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=sentinel-portal-ec2" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text)
```
Then switch to root:
```sh
sudo su -
```

### Step 6 — Install PostgreSQL client on EC2
```sh
amazon-linux-extras install postgresql14 -y
```

### Step 7 — Connect to RDS and load schema
Replace `<rds_endpoint>` with value from Step 4:
```sh
psql -h <rds_endpoint> -p 5432 -U sentinel_admin -d sentineldb
```
Password: `SentinelPass2024!`

Once connected (`sentineldb=>`):
```sql
\i /home/ec2-user/sentinel-portal-aws-migration/app/db_setup.sql
\i /home/ec2-user/sentinel-portal-aws-migration/app/seed_data.sql
\dt
SELECT COUNT(*) FROM INCIDENTS;
\q
```
Expected: 5 tables, 103 incidents.

### Step 8 — Install Python 3.8 and dependencies on EC2
Still inside the SSM/EC2 session as root:
```sh
amazon-linux-extras install python3.8 -y
pip3.8 install -r /home/ec2-user/sentinel-portal-aws-migration/app/requirements.txt
```

### Step 9 — Start the app
```sh
pkill -f streamlit
cd /home/ec2-user/sentinel-portal-aws-migration/app
git pull
export DB_HOST="<rds_endpoint>"
export DB_PORT=5432
export DB_NAME="sentineldb"
export DB_USER="sentinel_admin"
export DB_PASSWORD='SentinelPass2024!'
export ENCRYPTION_KEY="dR2beRg1azhSVMaUzUpr8U-Z8-7VZmJDIrtMkX7P_XU="
python3.8 -m streamlit run Login.py --server.port 8501 --server.address 0.0.0.0 &
```

### Step 10 — Open the app
Wait 30 seconds then open in browser:
```sh
http://<alb_dns_name>
```
Login credentials:
- `alex` / `admin123` — Admin (full access)
- `amy` / `admin123` — Analyst (no delete)
- `noah` / `admin123` — Viewer (read only)

### Step 11 — Verify target group health
AWS Console → EC2 → Target Groups → `sentinel-portal-tg` → Targets tab → confirm **healthy**

## If App Crashes / Session Times Out
Re-run from Step 5. The database schema persists in RDS — no need to re-run Steps 6-8 unless it's a completely fresh Sandbox session. Just re-export env vars and restart Streamlit:
```sh
sudo su -
export DB_HOST="<rds_endpoint>"
export DB_PORT=5432
export DB_NAME="sentineldb"
export DB_USER="sentinel_admin"
export DB_PASSWORD='SentinelPass2024!'
export ENCRYPTION_KEY="dR2beRg1azhSVMaUzUpr8U-Z8-7VZmJDIrtMkX7P_XU="
pkill -f streamlit
cd /home/ec2-user/sentinel-portal-aws-migration/app
python3.8 -m streamlit run Login.py --server.port 8501 --server.address 0.0.0.0 &
```

## Security Validation (Part E)

### Test 1 — Port scan
```sh
sudo yum install -y nmap
nmap -Pn <alb_dns_name>
nmap -Pn -p 1-1000,3306,5432,8080,8501,8443,3389 <alb_dns_name>
```
Expected: only port 80 open, 998 ports filtered. Port 443 closed (no ACM cert in Sandbox).

### Test 2 — SQL injection
On login page enter `' OR '1'='1` as username → confirm "User not found". Screenshot.

### Test 3 — Encryption in transit (SSL/TLS)
Connect to RDS via psql — screenshot the SSL line:
```sh
SSL connection (protocol: TLSv1.2, cipher: ECDHE-RSA-AES256-GCM-SHA384, bits: 256)
```

### Test 4 — Encryption at rest
AWS Console → RDS → `sentinel-portal-db` → Configuration tab → **Encryption: Enabled**

### Test 5 — Python Fernet encryption
Report a new incident → screenshot `*** ENCRYPTED ***` (Decrypt OFF) → toggle ON → screenshot plaintext.

### Test 6 — RBAC validation
Login as alex, amy, noah — screenshot dashboard differences showing role-based access control.

### Test 7 — CloudWatch alarm
AWS Console → CloudWatch → Alarms → `sentinel-portal-high-cpu` → screenshot.

### Test 8 — Security Group rules
AWS Console → EC2 → Security Groups → screenshot inbound rules for all 3 SGs.

### Test 9 — Dynamic data masking
Login as noah → screenshot contact number showing `XXXXXXX003`.

## Known Issues & Resolutions (Part E)

| Issue | Error | Resolution |
|---|---|---|
| Multi-AZ RDS rejected | `db.t3.micro not supported for Multi-AZ` | Switched to Single-AZ with encryption |
| Secrets Manager denied | `AccessDeniedException: secretsmanager:CreateSecret` | Used env vars instead |
| S3/CloudTrail denied | `AccessDenied: s3:GetBucketObjectLockConfiguration` | Removed from Terraform |
| Custom IAM role denied | `AccessDenied: iam:CreateRole` | Used pre-existing LabInstanceProfile |
| PostgreSQL 15.7 not found | `Cannot find version 15.7 for postgres` | Changed to engine_version = "15" |
| Streamlit width error | `TypeError: form_submit_button() unexpected argument 'width'` | Replaced with use_container_width=True |
| Streamlit switch_page error | `AttributeError: module 'streamlit' has no attribute 'switch_page'` | Upgraded to Python 3.8 + latest Streamlit |
| RDS not reachable from CloudShell | `psql: Connection timed out` | Used SSM Session Manager via EC2 |
| Port 443 closed | No ACM certificate (requires domain ownership) | Documented as Sandbox limitation |

## Performance Note
App runs on t2.micro (1 vCPU, 1GB RAM) — expect slightly slower response times compared to local development. Acceptable for assignment demo purposes.

## Multi-AZ Exploration Note
Initially attempted `enable_multi_az = true`. Sandbox rejected this on `db.t3.micro`. Final config uses `enable_multi_az = false` with `storage_encrypted = true`.

## Tearing Down
```sh
terraform destroy
```
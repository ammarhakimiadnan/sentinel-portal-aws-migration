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
Save the `alb_dns_name` and `rds_endpoint` values.

### Step 5 — Connect to EC2 via SSM (to load database)
RDS is in a private subnet — connect via EC2 instead of CloudShell directly.
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
Replace `<rds_endpoint>` with value from Step 4 (without the `:5432` port):
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

### Step 8 — Start the app on EC2
Still inside the SSM/EC2 session:
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

### Step 9 — Open the app
Wait 30 seconds then open in browser:
```sh
http://<alb_dns_name>
```
Login credentials:
- `alex` / `admin123` — Admin (full access)
- `amy` / `admin123` — Analyst (no delete)
- `noah` / `admin123` — Viewer (read only)

### Step 10 — Verify target group health
AWS Console → EC2 → Target Groups → `sentinel-portal-tg` → Targets tab → confirm **healthy**

## Security Validation (Part E)

### Test 1 — Port scan
```sh
nmap -Pn <alb_dns_name>
```
Expected: only ports 80 and 443 open. Screenshot result.

### Test 2 — SQL injection
On login page enter `' OR '1'='1` as username → confirm "User not found", not bypassed. Screenshot.

### Test 3 — Encryption in transit
When connecting to RDS via psql, confirm SSL line:
```sh
SSL connection (protocol: TLSv1.2, cipher: ECDHE-RSA-AES256-GCM-SHA384)
```
Screenshot the psql connection output.

### Test 4 — Encryption at rest
AWS Console → RDS → `sentinel-portal-db` → Configuration tab → **Encryption: Enabled**. Screenshot.

### Test 5 — CloudWatch alarm
AWS Console → CloudWatch → Alarms → confirm `sentinel-portal-high-cpu` exists. Screenshot.

### Test 6 — Python-level encryption
Login as alex or amy → report a new incident with details → toggle Decrypt ON → confirm details are readable. Toggle OFF → confirm `*** ENCRYPTED ***` shown. Screenshot both states.

## Known Issues & Resolutions (Part E)

| Issue | Cause | Resolution |
|---|---|---|
| Multi-AZ RDS rejected | Sandbox account restriction | Switched to Single-AZ with encryption |
| Secrets Manager AccessDenied | voclabs role lacks CreateSecret | Removed; credentials passed via env vars |
| S3/CloudTrail AccessDenied | Explicit deny on GetBucketObjectLockConfiguration | Removed from Terraform; noted as limitation |
| Custom IAM role creation failed | IAM is read-only in Sandbox | Used pre-existing LabInstanceProfile |
| psql version conflict on CloudShell | postgresql16 already installed | Used postgresql14 via amazon-linux-extras on EC2 |
| Streamlit `width='stretch'` error | Old Streamlit version on EC2 (Python 3.7) | Upgraded to Python 3.8, replaced with `use_container_width=True` |
| Streamlit `st.switch_page` error | Streamlit version too old | Upgraded Streamlit via pip on Python 3.8 |
| SSH/CloudShell can't reach RDS | RDS in private subnet (correct behavior) | Used SSM Session Manager via EC2 instead |

## Multi-AZ Exploration Note
Initially attempted `enable_multi_az = true`. Sandbox rejected with:
`InvalidParameterCombination: Requested DB Instance class db.t3.micro is not supported for Multi-AZ`
Final config uses `enable_multi_az = false` with `storage_encrypted = true`.

## Performance Note
App runs on t2.micro (1 vCPU, 1GB RAM) — expect slightly slower response times compared to local development. Acceptable for assignment demo purposes.

## Tearing Down
```sh
terraform destroy
```
## Team — Group 7
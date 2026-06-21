Sentinel Portal AWS Migration — Handover
Team & Roles

Person 1 (Ammar) — Security Analyst & Report Lead → Part A, C
Person 2 (Ammar, also doing this) — Cloud Architect & IaC → Part B, D infra
Person 3 (Siti Hamizah?) — App Dev & Security Tester → db.py rewrite, Part D app, Part E

Repos

App: https://github.com/ammarhakimiadnan/Sentinel_Incidents_Portal
Terraform: https://github.com/ammarhakimiadnan/sentinel-portal-aws-migration (in /terraform folder)

Sandbox Constraints (AWS Academy Cloud Foundations)

Region locked to us-east-1, resets every session (~2-4hrs)
IAM read-only → must use pre-existing LabRole/LabInstanceProfile
EC2 key pair: vockey (pre-provisioned)
Multi-AZ RDS not supported
No Secrets Manager access (CreateSecret denied)
No S3 bucket management (GetBucketObjectLockConfiguration explicit deny) → blocks CloudTrail too
Supported instance types: t2/t3 nano-medium, db.t3 micro-medium
RDS engine_version must be "15" not "15.7"

Deployment Status — DONE ✅
Terraform deploys successfully (terraform apply → 0 errors, "No changes" on replan):

VPC (10.0.0.0/16), 2 public + 2 private subnets, IGW, route tables, NACLs
Security Groups (ALB: 80/443, EC2: 8501 from ALB + 22, RDS: 5432 from EC2 SG only)
EC2 t2.micro (Amazon Linux 2, LabInstanceProfile, vockey)
RDS PostgreSQL 15, db.t3.micro, encrypted at rest, single-AZ
ALB + target group + HTTP listener (HTTPS disabled, no ACM cert)
CloudWatch high-CPU alarm
EC2 user_data exports DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, ENCRYPTION_KEY as env vars before running Streamlit

Removed from original design (Sandbox limitations — document in Part E)

❌ AWS Secrets Manager (AccessDenied)
❌ CloudTrail + S3 bucket (AccessDenied on object lock config)
❌ Custom IAM least-privilege role (IAM read-only → used LabRole)
❌ ACM/HTTPS (no domain to validate cert)
❌ Multi-AZ RDS (explicitly unsupported — tried, got error, switched to single-AZ)

Current Live Values (last session — will change on redeploy)

ALB DNS: sentinel-portal-alb-1395025617.us-east-1.elb.amazonaws.com
EC2 IP: 98.80.227.203 (changes each apply)
DB: sentineldb / user sentinel_admin / pass SentinelPass2024!
Encryption key (Fernet): dR2beRg1azhSVMaUzUpr8U-Z8-7VZmJDIrtMkX7P_XU=

Current Blocker
App returns 502 Bad Gateway / target group unhealthy — db.py still uses pyodbc/SQL Server, crashes on boot. This is the expected next step.
NEXT STEPS (Person 3)

Rewrite db.py: pyodbc → psycopg2, read DB_HOST/PORT/NAME/USER/PASSWORD via os.environ.get()
Rewrite db_setup.sql for PostgreSQL: NVARCHAR→VARCHAR, IDENTITY→SERIAL, GETDATE()→NOW(), VARBINARY→BYTEA, remove ENCRYPTBYKEY/cert/key statements
Replace AES encryption with Python cryptography.Fernet using ENCRYPTION_KEY env var
Test locally with local PostgreSQL using same encryption key
Push to app repo → Person 2 redeploys (terraform apply, EC2 will re-run user_data)

NEXT STEPS (Person 2 — after Person 3 pushes)

New Sandbox session → CloudShell → re-setup Terraform (files now on GitHub terraform/ folder)
terraform init && terraform apply (re-creates everything fresh, ~10min for RDS)
Check target group health → should turn "healthy"
Run Part E security tests: nmap port scan, SQL injection test, RDS encryption check (CloudTrail unavailable — note as limitation)
Record demo video, push final IaC + screenshots

Part A & C — DONE (Person 1)
Already drafted: 6 risks + severity ranking (Part A), migration strategy + risk-to-control mapping table (Part C). Architecture diagram done (Person 2, in chat history).
Reminder
Each Sandbox session = fresh AWS account, fresh CloudShell (files don't persist) — always re-clone from GitHub at session start.
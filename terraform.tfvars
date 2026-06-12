aws_region   = "us-east-1"
project_name = "sentinel-portal"

db_name     = "sentineldb"
db_username = "sentinel_admin"
db_password = "SentinelPass2024!"

# IMPORTANT: Generate your own key with:
# python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Use the SAME key here and in your local db.py testing
encryption_key = "REPLACE_WITH_GENERATED_FERNET_KEY"

enable_multi_az = false
enable_https    = false
acm_certificate_arn = ""
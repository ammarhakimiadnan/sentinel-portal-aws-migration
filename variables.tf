variable "aws_region" {
  default = "us-east-1"
}

variable "project_name" {
  default = "sentinel-portal"
}

variable "vpc_cidr" {
  default = "10.0.0.0/16"
}

variable "db_name" {
  default = "sentineldb"
}

variable "db_username" {
  default = "sentinel_admin"
}

variable "db_password" {
  sensitive = true
  default   = "SentinelPass2024!"
}

variable "encryption_key" {
  description = "Fernet key for application-level AES encryption (generate with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")"
  sensitive   = true
  type        = string
  default     = "REPLACE_WITH_GENERATED_FERNET_KEY"
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS listener"
  type        = string
  default     = ""
}

variable "enable_multi_az" {
  description = "Set true to attempt Multi-AZ RDS (not supported in Sandbox - used for Part E exploration)"
  type        = bool
  default     = false
}

variable "enable_https" {
  description = "Set true only if a valid ACM certificate ARN is provided"
  type        = bool
  default     = false
}
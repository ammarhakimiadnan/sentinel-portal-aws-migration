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

#variable "key_name" {
#  description = "EC2 SSH key pair name — create this in AWS Console first"
#  default     = "sentinel-key"
#}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for HTTPS listener — create in ACM console first"
  type        = string
}

variable "enable_multi_az" {
  description = "Set true to attempt Multi-AZ RDS (used to demonstrate Sandbox limitation)"
  type        = bool
  default     = false
}
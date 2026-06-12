output "alb_dns_name" {
  description = "Public URL to access the Sentinel Portal"
  value       = aws_lb.app_alb.dns_name
}

output "ec2_public_ip" {
  value = aws_instance.app_server.public_ip
}

output "rds_endpoint" {
  value     = aws_db_instance.postgres.endpoint
  sensitive = true
}

output "cloudtrail_bucket" {
  value = aws_s3_bucket.cloudtrail_bucket.id
}
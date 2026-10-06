output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC address range"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_id" {
  description = "Public subnet ID"
  value       = aws_subnet.public.id
}

output "private_subnet_id" {
  description = "Private subnet ID"
  value       = aws_subnet.private.id
}

output "security_group_id" {
  description = "Web security group ID"
  value       = aws_security_group.web.id
}

output "ami_id" {
  description = "AMI the instance was launched from"
  value       = data.aws_ami.ubuntu.id
}

output "instance_id" {
  description = "Web server instance ID"
  value       = aws_instance.web.id
}

output "instance_public_ip" {
  description = "Public IP of the web server"
  value       = aws_instance.web.public_ip
}

output "instance_private_ip" {
  description = "Private IP of the web server"
  value       = aws_instance.web.private_ip
}

output "assets_bucket" {
  description = "S3 bucket holding the site files"
  value       = aws_s3_bucket.assets.bucket
}

output "website_url" {
  description = "Where the site would be served on real AWS"
  value       = "http://${aws_instance.web.public_ip}"
}

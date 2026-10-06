variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-south-1"
}

variable "project" {
  description = "Name prefix for every resource"
  type        = string
}

variable "environment" {
  description = "Environment name (dev / staging / prod)"
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Owner tag"
  type        = string
}

variable "vpc_cidr" {
  description = "Address range of the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Public subnet (web server)"
  type        = string
  default     = "10.20.1.0/24"
}

variable "private_subnet_cidr" {
  description = "Private subnet (reserved for a database tier - no route to the internet)"
  type        = string
  default     = "10.20.2.0/24"
}

variable "instance_type" {
  description = "EC2 instance type for the web server"
  type        = string
  default     = "t3.micro"
}

variable "use_localstack" {
  description = "true = LocalStack emulator, false = real AWS"
  type        = bool
  default     = true
}

variable "localstack_endpoint" {
  description = "Where LocalStack is listening"
  type        = string
  default     = "http://localhost:4566"
}

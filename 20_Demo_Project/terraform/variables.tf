variable "aws_region" {
  description = "AWS region for the VPC and EKS cluster"
  type        = string
  default     = "ap-south-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "taskboard-eks"
}

variable "cluster_version" {
  description = "Kubernetes version of the EKS control plane"
  type        = string
  default     = "1.34"
}

variable "environment" {
  description = "Environment tag added to every resource"
  type        = string
  default     = "dev"
}

variable "use_localstack" {
  description = "true = LocalStack on localhost:4566, false = real AWS"
  type        = bool
  default     = false
}

variable "localstack_endpoint" {
  description = "LocalStack edge endpoint, used only when use_localstack = true"
  type        = string
  default     = "http://localhost:4566"
}

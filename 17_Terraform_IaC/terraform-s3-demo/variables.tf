variable "aws_region" {
  description = "AWS region to create the bucket in"
  type        = string
  default     = "ap-south-1"
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name (lowercase letters, numbers, dots and hyphens)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "Bucket names must be 3-63 characters of lowercase letters, numbers, dots and hyphens."
  }
}

variable "environment" {
  description = "Environment tag (dev / staging / prod)"
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Who owns these resources - used in the default tags"
  type        = string
}

variable "versioning_enabled" {
  description = "Keep every version of every object"
  type        = bool
  default     = true
}

variable "use_localstack" {
  description = "true = LocalStack emulator on localhost, false = real AWS"
  type        = bool
  default     = true
}

variable "localstack_endpoint" {
  description = "Where LocalStack is listening"
  type        = string
  default     = "http://localhost:4566"
}

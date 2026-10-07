terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source = "hashicorp/aws"
      # The EKS module 20.x supports AWS provider 5.x only.
      version = "~> 5.95"
    }
  }
}

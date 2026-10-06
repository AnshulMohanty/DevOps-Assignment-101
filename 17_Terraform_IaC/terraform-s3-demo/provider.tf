terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# With use_localstack = true every AWS API call goes to LocalStack on localhost:4566
# (an AWS emulator running in Docker) with dummy credentials. Set it to false and the
# same code runs against real AWS using the normal credential chain (aws configure / env vars).
provider "aws" {
  region = var.aws_region

  access_key                  = var.use_localstack ? "test" : null
  secret_key                  = var.use_localstack ? "test" : null
  skip_credentials_validation = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  skip_requesting_account_id  = var.use_localstack
  s3_use_path_style           = var.use_localstack

  dynamic "endpoints" {
    for_each = var.use_localstack ? [1] : []
    content {
      s3  = var.localstack_endpoint
      sts = var.localstack_endpoint
    }
  }

  default_tags {
    tags = {
      Project   = "devops-assignment"
      ManagedBy = "terraform"
      Owner     = var.owner
    }
  }
}

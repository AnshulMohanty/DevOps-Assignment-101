# use_localstack = true sends every AWS call to LocalStack on localhost:4566 with dummy credentials.
# use_localstack = false uses a real AWS account through the normal credential chain.
provider "aws" {
  region = var.aws_region

  access_key                  = var.use_localstack ? "test" : null
  secret_key                  = var.use_localstack ? "test" : null
  skip_credentials_validation = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  skip_requesting_account_id  = var.use_localstack

  dynamic "endpoints" {
    for_each = var.use_localstack ? [1] : []
    content {
      ec2            = var.localstack_endpoint
      eks            = var.localstack_endpoint
      iam            = var.localstack_endpoint
      kms            = var.localstack_endpoint
      cloudwatchlogs = var.localstack_endpoint
      sts            = var.localstack_endpoint
    }
  }

  default_tags {
    tags = {
      Project     = "taskboard"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

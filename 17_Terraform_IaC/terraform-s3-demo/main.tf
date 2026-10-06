resource "aws_s3_bucket" "demo" {
  bucket        = var.bucket_name
  force_destroy = true # lets `terraform destroy` remove a bucket that still has objects

  tags = {
    Name        = var.bucket_name
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "demo" {
  bucket = aws_s3_bucket.demo.id

  versioning_configuration {
    status = var.versioning_enabled ? "Enabled" : "Suspended"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "demo" {
  bucket = aws_s3_bucket.demo.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "demo" {
  bucket = aws_s3_bucket.demo.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "readme" {
  bucket       = aws_s3_bucket.demo.id
  key          = "hello.txt"
  content      = "Created by Terraform for ${var.owner} (${var.environment})\n"
  content_type = "text/plain"

  # upload only after encryption and versioning are configured on the bucket
  depends_on = [
    aws_s3_bucket_versioning.demo,
    aws_s3_bucket_server_side_encryption_configuration.demo,
  ]
}

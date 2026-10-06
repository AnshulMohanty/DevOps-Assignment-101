output "bucket_name" {
  description = "Name of the bucket"
  value       = aws_s3_bucket.demo.bucket
}

output "bucket_arn" {
  description = "ARN of the bucket"
  value       = aws_s3_bucket.demo.arn
}

output "bucket_region" {
  description = "Region the bucket is in"
  value       = aws_s3_bucket.demo.region
}

output "versioning_status" {
  description = "Versioning state of the bucket"
  value       = aws_s3_bucket_versioning.demo.versioning_configuration[0].status
}

output "object_url" {
  description = "S3 URI of the uploaded object"
  value       = "s3://${aws_s3_object.readme.bucket}/${aws_s3_object.readme.key}"
}

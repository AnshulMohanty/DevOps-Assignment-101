project       = "devops-hw"
environment   = "dev"
owner         = "Anshul Mohanty"
aws_region    = "ap-south-1"
vpc_cidr      = "10.20.0.0/16"
instance_type = "t3.micro"

# true = LocalStack on localhost:4566, false = real AWS account
use_localstack = true

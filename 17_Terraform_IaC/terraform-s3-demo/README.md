terraform-s3-demo
=================

Name: Anshul Mohanty    Roll No: 24BCS10191    Section: A

Creates an S3 bucket with versioning, AES-256 encryption, Block Public Access and one object.
The full run of every command, with screenshots, is in
[Task 1 of the topic README](../README.md#task-1-terraform-s3-demo).

| File | Contents |
|---|---|
| [provider.tf](provider.tf) | Terraform/provider versions, AWS provider with the LocalStack switch, default tags |
| [variables.tf](variables.tf) | Inputs, including validation of the bucket name |
| [main.tf](main.tf) | The five resources |
| [outputs.tf](outputs.tf) | Bucket name, ARN, region, versioning status, object URI |
| [terraform.tfvars](terraform.tfvars) | The values used for this run |
| `.terraform.lock.hcl` | Pinned provider version (committed) |

## Run it

LocalStack (no AWS account needed):

```bash
docker run -d --name localstack -p 4566:4566 localstack/localstack:4.14

terraform init
terraform fmt -check
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
terraform show
terraform output
terraform destroy
```

Real AWS: set `use_localstack = false` in `terraform.tfvars`, make credentials available
(`aws configure` or `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`), and change `bucket_name` if
it is already taken - bucket names are global.

## Outputs

```
bucket_arn = "arn:aws:s3:::anshul-24bcs10191-devops-demo"
bucket_name = "anshul-24bcs10191-devops-demo"
bucket_region = "ap-south-1"
object_url = "s3://anshul-24bcs10191-devops-demo/hello.txt"
versioning_status = "Enabled"
```

`terraform.tfstate` and `.terraform/` are in `.gitignore`: state can hold sensitive values and
belongs in a remote backend, and `.terraform/` is just the downloaded provider.

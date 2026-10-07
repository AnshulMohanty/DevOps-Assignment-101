# Terraform - AWS VPC + EKS for TaskBoard

Provisions the network and Kubernetes cluster the production-style TaskBoard deployment runs on,
using the community `terraform-aws-modules/vpc` and `terraform-aws-modules/eks` modules.

```text
VPC 10.20.0.0/16 (ap-south-1)
 |-- public subnets   10.20.101.0/24, 10.20.102.0/24   (internet gateway, NAT gateway, load balancers)
 |-- private subnets  10.20.1.0/24,   10.20.2.0/24     (worker nodes, outbound through the NAT gateway)
 `-- EKS cluster taskboard-eks
       `-- managed node group "main": 2-4 x t3.medium
```

> Cost warning: an EKS control plane and a NAT gateway are billed by the hour. Run `terraform destroy` when finished.

Real AWS (credentials from `aws configure` / `AWS_PROFILE`, never from a file in this folder):

```bash
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -recursive
terraform validate
terraform plan
terraform apply
aws eks update-kubeconfig --region ap-south-1 --name taskboard-eks
terraform destroy
```

Without an AWS account, the same code runs against LocalStack (`docker run -d --name localstack -p 4566:4566 localstack/localstack:4.14`):

```bash
terraform plan    -var-file=localstack.tfvars
terraform apply   -var-file=localstack.tfvars -target=module.vpc   # the community edition has no EKS API
terraform destroy -var-file=localstack.tfvars
```

# Look the AMI up instead of hard-coding an ID - AMI IDs differ per region and change over time.
# Real AWS: Canonical's Ubuntu 24.04 images. LocalStack: its built-in mock Ubuntu image.
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = var.use_localstack ? ["amazon"] : ["099720109477"]

  filter {
    name = "name"
    values = [var.use_localstack
      ? "ubuntu/images/hvm-ssd/ubuntu-xenial-16.04-amd64-server-*"
      : "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"
    ]
  }
}

resource "aws_instance" "web" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web.id]
  iam_instance_profile   = aws_iam_instance_profile.web.name

  # On first boot: install nginx and serve the page stored in the assets bucket.
  user_data = <<-EOT
    #!/bin/bash
    apt-get update -y && apt-get install -y nginx awscli
    aws s3 cp s3://${aws_s3_bucket.assets.bucket}/site/index.html /var/www/html/index.html
    systemctl enable --now nginx
  EOT

  root_block_device {
    volume_size = 8
    volume_type = "gp3"
    encrypted   = true
  }

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  # Explicit dependency: nothing above references the route table association, but the
  # instance should only start once its subnet actually has a route to the internet.
  depends_on = [aws_route_table_association.public]

  tags = { Name = "${var.project}-web" }
}

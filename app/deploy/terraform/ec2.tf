data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

locals {
  user_data = templatefile("${path.module}/../scripts/bootstrap.sh.tftpl", {
    project_name       = var.project_name
    aws_region         = var.aws_region
    ecr_repository_url = aws_ecr_repository.app.repository_url
  })
}

resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = local.subnet_id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile   = aws_iam_instance_profile.instance.name
  key_name               = var.allowed_ssh_cidr != "" ? var.key_name : null

  user_data                  = local.user_data
  user_data_replace_on_change = true

  root_block_device {
    volume_type = "gp3"
    volume_size = 15
  }

  tags = {
    Name    = "${var.project_name}-app"
    Project = var.project_name
  }
}

# Separate from the instance's lifecycle on purpose — replacing the instance
# (AMI update, instance-type change, etc.) does not touch this volume or its
# data, since it's attached rather than declared as an instance block device.
resource "aws_ebs_volume" "data" {
  availability_zone = aws_instance.app.availability_zone
  size              = var.data_volume_size_gb
  type              = "gp3"

  tags = {
    Name    = "${var.project_name}-data"
    Project = var.project_name
  }
}

resource "aws_volume_attachment" "data" {
  device_name = "/dev/sdf"
  volume_id   = aws_ebs_volume.data.id
  instance_id = aws_instance.app.id
}

resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"

  tags = { Project = var.project_name }
}

resource "aws_route53_record" "app" {
  count   = var.domain_name != "" ? 1 : 0
  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.app.public_ip]
}

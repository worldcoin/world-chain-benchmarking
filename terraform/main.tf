terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.region
}

resource "tls_private_key" "benchmark" {
  algorithm = "ED25519"
}

resource "aws_key_pair" "benchmark" {
  key_name   = "${var.prefix}-benchmark-key"
  public_key = tls_private_key.benchmark.public_key_openssh
}

resource "local_file" "private_key" {
  content         = tls_private_key.benchmark.private_key_openssh
  filename        = "${path.module}/${var.prefix}-benchmark-key.pem"
  file_permission = "0600"
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_security_group" "benchmark" {
  name_prefix = "${var.prefix}-benchmark-"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Ethereum P2P
  ingress {
    from_port   = 30303
    to_port     = 30303
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 30303
    to_port     = 30303
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "benchmark" {
  ami           = var.ami_id != "" ? var.ami_id : data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = aws_key_pair.benchmark.key_name

  vpc_security_group_ids = [aws_security_group.benchmark.id]

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = "gp3"
    iops        = 16000
    throughput  = 1000
  }

  user_data = file("${path.module}/user-data.sh")

  tags = {
    Name = "${var.prefix}-benchmark"
  }
}

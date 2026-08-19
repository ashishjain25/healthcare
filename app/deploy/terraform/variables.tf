variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short name used to prefix/tag every resource this stack creates."
  type        = string
  default     = "cis"
}

variable "instance_type" {
  description = "EC2 instance type. t3.small is enough — the app itself is a lightweight FastAPI process; the actual AI work happens via the OpenAI API, not locally."
  type        = string
  default     = "t3.small"
}

variable "data_volume_size_gb" {
  description = "Size of the persistent EBS volume backing /app/data (SQLite DB, ChromaDB, uploaded files)."
  type        = number
  default     = 20
}

variable "allowed_ssh_cidr" {
  description = "CIDR allowed to reach port 22, e.g. \"203.0.113.4/32\". Leave blank (default) to disable SSH entirely and manage the instance via AWS SSM Session Manager instead — the instance IAM role already grants that."
  type        = string
  default     = ""
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH access. Only used if allowed_ssh_cidr is also set. Leave null to rely on SSM Session Manager only (recommended)."
  type        = string
  default     = null
}

variable "vpc_id" {
  description = "VPC to deploy into. Leave blank to use the account's default VPC."
  type        = string
  default     = ""
}

variable "subnet_id" {
  description = "Subnet to deploy into. Leave blank to use the first available default-VPC subnet."
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Optional domain name (e.g. \"clinical.example.com\") to point at the instance's Elastic IP via Route 53. Leave blank to skip DNS and use the raw Elastic IP over plain HTTP — see DEPLOYMENT.md for adding HTTPS."
  type        = string
  default     = ""
}

variable "route53_zone_id" {
  description = "Hosted zone ID to create the domain_name record in. Required only if domain_name is set."
  type        = string
  default     = ""
}

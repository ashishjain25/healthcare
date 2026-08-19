data "aws_caller_identity" "current" {}

resource "aws_iam_role" "instance" {
  name = "${var.project_name}-instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Project = var.project_name }
}

# SSM Session Manager access — no SSH key or open port 22 needed to reach
# the instance: `aws ssm start-session --target <instance-id>`.
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Pull the app image from this stack's ECR repo.
resource "aws_iam_role_policy_attachment" "ecr_read" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

# Read (only) this app's own secrets out of SSM Parameter Store, and decrypt
# them with the account's default SSM-managed KMS key.
resource "aws_iam_role_policy" "read_app_secrets" {
  name = "${var.project_name}-read-secrets"
  role = aws_iam_role.instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParametersByPath"]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.project_name}/*"
      },
      {
        Effect   = "Allow"
        Action   = "kms:Decrypt"
        Resource = "arn:aws:kms:${var.aws_region}:${data.aws_caller_identity.current.account_id}:alias/aws/ssm"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "instance" {
  name = "${var.project_name}-instance"
  role = aws_iam_role.instance.name
}

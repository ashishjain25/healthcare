# Placeholder SecureString parameters — terraform creates them, but you set
# the real values out-of-band (see DEPLOYMENT.md) with:
#   aws ssm put-parameter --name /cis/openai_api_key \
#     --type SecureString --value "sk-..." --overwrite
# lifecycle.ignore_changes keeps `terraform apply` from ever stomping a real
# value back to "CHANGE_ME" once you've set it.

resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${var.project_name}/openai_api_key"
  type  = "SecureString"
  value = "CHANGE_ME"

  lifecycle {
    ignore_changes = [value]
  }

  tags = { Project = var.project_name }
}

resource "aws_ssm_parameter" "session_secret" {
  name  = "/${var.project_name}/session_secret"
  type  = "SecureString"
  value = "CHANGE_ME"

  lifecycle {
    ignore_changes = [value]
  }

  tags = { Project = var.project_name }
}

# Optional — Langfuse observability. SSM SecureString values can't be empty
# strings, so this uses the same "CHANGE_ME"-style placeholder as the
# required secrets above; the bootstrap script/app treat an unset/placeholder
# Langfuse key as "not configured" and fall back to the app's NoOp tracer.
resource "aws_ssm_parameter" "langfuse_public_key" {
  name  = "/${var.project_name}/langfuse_public_key"
  type  = "SecureString"
  value = "UNSET"

  lifecycle {
    ignore_changes = [value]
  }

  tags = { Project = var.project_name }
}

resource "aws_ssm_parameter" "langfuse_secret_key" {
  name  = "/${var.project_name}/langfuse_secret_key"
  type  = "SecureString"
  value = "UNSET"

  lifecycle {
    ignore_changes = [value]
  }

  tags = { Project = var.project_name }
}

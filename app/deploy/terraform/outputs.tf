output "aws_region" {
  description = "For scripting — so deploy commands don't need the region hardcoded separately from terraform.tfvars."
  value       = var.aws_region
}

output "app_url" {
  description = "Where the app is reachable once bootstrap.sh finishes (a few minutes after `terraform apply`)."
  value       = var.domain_name != "" ? "http://${var.domain_name}" : "http://${aws_eip.app.public_ip}"
}

output "instance_id" {
  description = "For `aws ssm start-session --target <id>` and for watching /var/log/bootstrap.log."
  value       = aws_instance.app.id
}

output "elastic_ip" {
  value = aws_eip.app.public_ip
}

output "ecr_repository_url" {
  description = "Push images here — see deploy/DEPLOYMENT.md or .github/workflows/deploy.yml."
  value       = aws_ecr_repository.app.repository_url
}

output "ssm_secret_paths" {
  description = "Set real values for these before traffic hits the app — see DEPLOYMENT.md."
  value = [
    aws_ssm_parameter.openai_api_key.name,
    aws_ssm_parameter.session_secret.name,
    aws_ssm_parameter.langfuse_public_key.name,
    aws_ssm_parameter.langfuse_secret_key.name,
  ]
}

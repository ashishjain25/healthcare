# Deploying to AWS

## Why this shape

The app is SQLite + a local ChromaDB persist dir + local file uploads —
single-writer, single-disk assumptions baked into `backend/config.py` from
the start (see the main `README.md`'s Design decisions). That rules out
anything that wants stateless/horizontally-scaled compute (Lambda, App
Runner without a datastore migration, multiple ECS tasks behind a load
balancer). It's a natural fit for **one EC2 instance, one Docker container,
one persistent EBS volume** — which is what `deploy/terraform/` provisions:

```
                         ┌─────────────────────────────┐
Internet ── 80/443 ──▶   │ EC2 (t3.small)               │
                         │  Docker container             │
                         │   FastAPI + built React SPA   │──▶ OpenAI API
                         │  bind-mounted /data ──────────┼──▶ EBS volume
                         └─────────────────────────────┘      (survives
                             ▲                                instance
                             │ image pulls                    replacement)
                         ECR repository
                             ▲
                             │ push (CI or manual)
                         your machine / GitHub Actions
```

Secrets (`OPENAI_API_KEY`, `SESSION_SECRET`, Langfuse keys) live in SSM
Parameter Store as `SecureString`s, fetched by the instance at boot — never
committed, never baked into the image. The instance has no SSH key or open
port 22 by default; it's managed through **SSM Session Manager**
(`aws ssm start-session`), which only needs IAM, not a key pair or inbound
rule.

## Prerequisites

- An AWS account and credentials configured locally (`aws configure`), with
  permission to create EC2/EBS/ECR/IAM/SSM/Route53 resources.
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.5.
- Docker, to build and push the image the first time (and for local testing).
- An OpenAI API key.

## First-time setup

**1. Provision the infrastructure.**

```bash
cd app/deploy/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars — at minimum set aws_region if you're not in us-east-1

terraform init
terraform apply
```

This creates the ECR repository, EC2 instance + EBS data volume, security
group, IAM role, placeholder SSM parameters, and an Elastic IP (plus a
Route 53 record if you set `domain_name`). The instance boots immediately
and runs `deploy/scripts/bootstrap.sh.tftpl` as user-data — but there's no
image in ECR yet, so the app itself won't be running after this step. That's
expected; continue below.

**2. Set the real secrets** (terraform created these as `SecureString`
placeholders — see the `ssm_secret_paths` output). Still in
`deploy/terraform/`:

```bash
REGION=$(terraform output -raw aws_region)

aws ssm put-parameter --name /cis/openai_api_key \
  --type SecureString --value "sk-..." --overwrite --region "$REGION"

aws ssm put-parameter --name /cis/session_secret \
  --type SecureString --value "$(openssl rand -hex 32)" --overwrite --region "$REGION"

# optional — leave blank to keep the app's NoOp tracer:
aws ssm put-parameter --name /cis/langfuse_public_key --type SecureString --value "pk-lf-..." --overwrite --region "$REGION"
aws ssm put-parameter --name /cis/langfuse_secret_key --type SecureString --value "sk-lf-..." --overwrite --region "$REGION"
```

**3. Build and push the first image** (from `app/`, i.e. one level up from
`deploy/`):

```bash
cd ../..   # back to app/
ECR_URL=$(terraform -chdir=deploy/terraform output -raw ecr_repository_url)
REGION=$(terraform -chdir=deploy/terraform output -raw aws_region)

aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ECR_URL"
docker build -t "$ECR_URL:latest" .
docker push "$ECR_URL:latest"
```

**4. Start the app on the instance** — the secrets and compose file from
bootstrap are already in place; just pull the image that now exists:

```bash
INSTANCE_ID=$(terraform -chdir=deploy/terraform output -raw instance_id)

aws ssm send-command --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["cd /opt/app && docker compose pull && docker compose up -d"]' \
  --region "$REGION"
```

**5. Seed demo data (optional).** The app auto-creates its schema on
startup (`init_db()` in `backend/main.py`'s lifespan), but starts with an
empty database. `scripts/seed_data.py` needs the `../Datasets/` folder
(real sample reports), which isn't part of the Docker image by design — run
it locally against a local SQLite file if you want seeded demo accounts, or
treat the deployed instance as a clean production start (real
doctors/radiologists/patients get created through the app itself).

**6. Open it:**

```bash
terraform -chdir=deploy/terraform output app_url
```

## Subsequent deploys

Either push to `main` (see `.github/workflows/deploy.yml` — needs the repo
secrets listed at the top of that file), or manually repeat steps 3–4 above.
`docker compose up -d` only recreates the container; the EBS-backed
`/data/app` bind mount means the SQLite DB, ChromaDB, and uploads survive.

## HTTPS

The default setup serves plain HTTP on the Elastic IP (or `domain_name` if
you set one). To add HTTPS, the simplest option is a
[Caddy](https://caddyserver.com/) reverse-proxy container in front of the
app — Caddy issues and renews a Let's Encrypt cert automatically given a
real domain pointed at the instance:

1. Point `domain_name` at the Elastic IP (either via this stack's
   `route53_zone_id` variable, or your own DNS) and wait for it to resolve.
2. On the instance (via SSM), change `/opt/app/docker-compose.yml`'s `app`
   service `ports` to expose only on `127.0.0.1`, add a `caddy` service
   bound to `80`/`443` with a one-line `Caddyfile`
   (`your-domain.com { reverse_proxy app:8000 }`), and `docker compose up -d`.

This isn't automated in Terraform because Caddy's first certificate request
needs DNS to have already propagated — doing it as a manual follow-up step
avoids a bootstrap script that silently fails a TLS handshake on first boot.

## Operations

- **Logs**: `aws ssm start-session --target <instance-id>`, then
  `docker logs -f $(docker ps -q --filter ancestor=<ecr-repo-url>)` or
  `cat /var/log/bootstrap.log` for the first-boot script itself.
- **Backups**: the data that matters is entirely on the EBS data volume
  (`/data/app` on the host). Snapshot it:
  `aws ec2 create-snapshot --volume-id <id> --description "cis backup"`.
  Find the volume ID with `terraform -chdir=deploy/terraform state show aws_ebs_volume.data`.
- **Health check**: `GET /healthz` — checks SQLite connectivity, not just
  "process is up" (see `backend/api/routes_pages.py`).
- **Scaling**: don't run more than one container against the same SQLite
  file — see the Dockerfile's comment on why it's a single uvicorn worker.
  If you outgrow one `t3.small`, resize the instance (`instance_type`
  variable) rather than adding more of them.
- **Tearing down**: `terraform destroy` — this deletes the EC2 instance,
  security group, IAM role, ECR repo, and EBS data volume (and everything
  on it). Snapshot first if you want to keep the data.

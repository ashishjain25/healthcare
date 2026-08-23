<div class="page cover">
  <div class="kicker">DEPLOYMENT ARCHITECTURE &middot; REFERENCE DOCUMENT</div>
  <h1>Healthcare Clinical Intelligence System</h1>
  <p class="lede">
    One EC2 instance, one Docker container, one persistent EBS volume &mdash;
    provisioned by Terraform, built and pushed by GitHub Actions, managed
    entirely through SSM Session Manager with no SSH key and no open port 22.
    Secrets live in SSM Parameter Store, never in the image.
  </p>
  <div class="badges">
    <span>AWS EC2</span><span>EBS</span><span>ECR</span><span>SSM</span>
    <span>IAM</span><span>Terraform</span><span>Docker</span><span>GitHub Actions</span>
  </div>
  <div class="live-pill">
    <span class="dot"></span>
    LIVE &mdash; http://ec2-63-185-251-88.eu-central-1.compute.amazonaws.com
  </div>
</div>

<div class="page">
  <div class="section-head"><span class="num">01</span><h2>Why this shape</h2></div>
  <p>
    The app is SQLite + a local ChromaDB persist directory + local file
    uploads &mdash; single-writer, single-disk assumptions baked into
    <code>backend/config.py</code> from the start. That rules out anything
    that wants stateless or horizontally-scaled compute (Lambda, App Runner
    without a datastore migration, multiple ECS tasks behind a load
    balancer). It's a natural fit for one EC2 instance, one Docker container,
    one persistent EBS volume.
  </p>
  <ul class="check-list">
    <li>Secrets (<code>OPENAI_API_KEY</code>, <code>SESSION_SECRET</code>,
      Langfuse keys) live in SSM Parameter Store as <code>SecureString</code>s
      &mdash; fetched by the instance at boot, never committed, never baked
      into the Docker image.</li>
    <li>No SSH key, no open port 22 by default &mdash; the instance is
      managed entirely through <strong>SSM Session Manager</strong>
      (<code>aws ssm start-session</code>), which only needs IAM, not a
      key pair or inbound rule.</li>
    <li>A single uvicorn worker, intentionally &mdash; SQLite is
      single-writer, so multiple workers against the same DB file risk
      "database is locked" errors under concurrent writes. Scale this
      vertically (a bigger instance type), not horizontally.</li>
    <li>The EBS data volume is declared separately from the instance's own
      lifecycle &mdash; replacing the instance (AMI update, instance-type
      change) never touches the volume or its data.</li>
  </ul>
</div>

<div class="page diagram-page">
  <div class="section-head"><span class="num">02</span><h2>Deployment diagram</h2></div>
  <img src="architecture-diagrams/diagram4-deployment.png" alt="Deployment diagram" />
</div>

<div class="page">
  <div class="section-head"><span class="num">03</span><h2>First-time setup</h2></div>
  <ol class="steps">
    <li><strong>Provision the infrastructure.</strong> <code>terraform apply</code>
      from <code>deploy/terraform/</code> creates the ECR repository, EC2
      instance + EBS data volume, security group, IAM role, placeholder SSM
      parameters, and an Elastic IP. The instance boots and runs
      <code>bootstrap.sh</code> as user-data &mdash; but there's no image in
      ECR yet, so the app itself isn't running after this step alone.</li>
    <li><strong>Set the real secrets.</strong> Terraform creates the SSM
      parameters as placeholders (<code>CHANGE_ME</code> / <code>UNSET</code>
      &mdash; SSM <code>SecureString</code>s can't hold an empty string).
      Overwrite them with <code>aws ssm put-parameter --overwrite</code>.</li>
    <li><strong>Build and push the first image</strong> to ECR
      (<code>docker build --platform linux/amd64</code>, then
      <code>docker push</code>).</li>
    <li><strong>Start the app</strong> via
      <code>aws ssm send-command</code> running
      <code>docker compose pull &amp;&amp; docker compose up -d</code> on
      the instance.</li>
    <li><strong>Refresh secrets on the instance, if step 2 happened after
      first boot.</strong> <code>bootstrap.sh</code> writes
      <code>/opt/app/.env</code> from SSM exactly once, at first boot. If
      real secrets are set in SSM afterward, re-fetch them into
      <code>.env</code> and <code>docker compose up -d --force-recreate</code>
      &mdash; updating SSM alone does not refresh a file already written to
      disk.</li>
  </ol>
</div>

<div class="page">
  <div class="section-head"><span class="num">04</span><h2>CI/CD &amp; subsequent deploys</h2></div>
  <p>
    <code>.github/workflows/deploy.yml</code> runs on every push to
    <code>main</code> that touches <code>backend/</code>,
    <code>frontend/</code>, the <code>Dockerfile</code>, or
    <code>requirements.txt</code>:
  </p>
  <ol class="steps">
    <li><strong>test</strong> &mdash; installs <code>requirements.txt</code>,
      runs <code>pytest tests/ -q</code> (87 tests, no network/API key
      required).</li>
    <li><strong>build-and-deploy</strong> (only if tests pass) &mdash; logs
      in to ECR, builds and pushes the image tagged both
      <code>:latest</code> and <code>:$&#123;github.sha&#125;</code>, then
      triggers a redeploy on the instance via
      <code>aws ssm send-command</code> running the same
      <code>docker compose pull &amp;&amp; up -d</code> &mdash; no SSH key
      needed from CI either.</li>
  </ol>
  <p>
    The IAM user behind the CI access keys is scoped to exactly
    <code>ecr:*</code> on the one repository and
    <code>ssm:SendCommand</code> / <code>ssm:GetCommandInvocation</code> on
    the one instance &mdash; never account-admin keys.
    <code>docker compose up -d</code> only recreates the container; the
    EBS-backed <code>/data/app</code> bind mount means the SQLite DB,
    ChromaDB, and uploads survive every redeploy.
  </p>
</div>

<div class="page">
  <div class="section-head"><span class="num">05</span><h2>Operations</h2></div>
  <table class="ops-table">
    <tr><td>Logs</td><td><code>aws ssm start-session --target &lt;instance-id&gt;</code>,
      then <code>docker logs -f $(docker ps -q --filter ancestor=&lt;ecr-repo-url&gt;)</code>
      or <code>cat /var/log/bootstrap.log</code> for the first-boot script.</td></tr>
    <tr><td>Backups</td><td>Everything that matters lives on the EBS data
      volume (<code>/data/app</code> on the host). Snapshot it with
      <code>aws ec2 create-snapshot --volume-id &lt;id&gt;</code>.</td></tr>
    <tr><td>Health check</td><td><code>GET /healthz</code> &mdash; executes
      <code>SELECT 1</code> against SQLite, not just "process is up." An
      unmounted data volume fails this instead of lying about liveness.</td></tr>
    <tr><td>Scaling</td><td>Don't run more than one container against the
      same SQLite file. Resize the instance type if needed, rather than
      adding more of them.</td></tr>
    <tr><td>HTTPS</td><td>Not yet enabled &mdash; the default setup serves
      plain HTTP. A Caddy reverse-proxy container in front of the app is the
      documented path once a real domain is pointed at the instance
      (see <code>DEPLOYMENT.md</code>).</td></tr>
    <tr><td>Tearing down</td><td><code>terraform destroy</code> deletes the
      EC2 instance, security group, IAM role, ECR repo, and the EBS data
      volume &mdash; snapshot first if the data matters.</td></tr>
  </table>
</div>

<div class="page">
  <div class="section-head"><span class="num">06</span><h2>This deployment</h2></div>
  <table class="live-table">
    <tr><td>URL</td><td><code>http://ec2-63-185-251-88.eu-central-1.compute.amazonaws.com</code></td></tr>
    <tr><td>Region</td><td>eu-central-1 (Frankfurt)</td></tr>
    <tr><td>Instance</td><td>t3.small, no SSH key &mdash; SSM Session Manager only</td></tr>
    <tr><td>ECR repository</td><td><code>509124060793.dkr.ecr.eu-central-1.amazonaws.com/cis</code></td></tr>
    <tr><td>Data volume</td><td>20&nbsp;GB EBS gp3, bind-mounted at <code>/data/app</code></td></tr>
    <tr><td>Seed data</td><td>2 doctors, 2 radiologists, 5 patients, 12 reports run through the
      full 5-agent pipeline, 344 reference documents embedded &mdash; password
      <code>password123</code> for every seeded account</td></tr>
  </table>
  <div class="section-head" style="margin-top:10mm"><span class="num small">&nbsp;</span><h3>Known open items</h3></div>
  <ul class="check-list">
    <li>HTTPS not yet configured &mdash; plain HTTP on the AWS-assigned
      hostname; needs a custom domain to add TLS via Caddy.</li>
    <li>AWS credentials currently in use for admin operations are the
      account's <strong>root</strong> access key, not a scoped IAM user
      &mdash; worth narrowing before further changes.</li>
    <li>No custom/branded domain &mdash; the canonical URL is the free,
      AWS-assigned public DNS hostname, which has the instance's IP address
      embedded in it by design.</li>
  </ul>
</div>

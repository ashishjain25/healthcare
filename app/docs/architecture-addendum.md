<div class="page">
  <div class="section-head"><span class="num">05</span><h2>Deployment</h2></div>
  <p>
    Sections 01&ndash;04 cover what the system is made of and how a request
    moves through it. This system also runs live &mdash; one EC2 instance,
    one Docker container, one persistent EBS volume, provisioned by
    Terraform and deployed by GitHub Actions, with secrets in SSM Parameter
    Store and no SSH key on the box.
  </p>
  <div class="live-pill">
    <span class="dot"></span>
    LIVE &mdash; http://ec2-63-185-251-88.eu-central-1.compute.amazonaws.com
  </div>
  <p style="margin-top:8mm">
    The full deployment write-up &mdash; rationale, first-time setup, CI/CD,
    operations, and this specific deployment's details &mdash; is its own
    document: <code>docs/deployment-architecture.pdf</code>.
  </p>
</div>

<div class="page diagram-page">
  <div class="section-head"><span class="num">05</span><h2>Deployment diagram</h2></div>
  <img src="architecture-diagrams/diagram4-deployment.png" alt="Deployment diagram" />
</div>

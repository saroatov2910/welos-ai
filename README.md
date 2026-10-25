# Veloce AI

**An on-prem fraud gatekeeper for card payments.** It runs inside the store or bank
network, decides on every transaction in under 15 ms, and keeps card data off the internet.

This repository is a DevOps project: the decision service is the workload, and the focus
is on how it is built, tested, secured, shipped and run.

| | |
|---|---|
| **Live API (demo)** | https://veloce-decision-service.onrender.com/docs |
| **Website** | https://veloce-ai-demo.vercel.app |
| **Roadmap** | [ROADMAP.md](ROADMAP.md) |

> Demo environment only. Use the test card `4242 4242 4242 4242`.

## System overview

```mermaid
flowchart TB
    dev["Developer"]

    subgraph git["GitHub"]
        develop["develop branch"]
        main["main branch<br/>protected: PR + 5 green checks"]
        develop -->|"pull request"| main
    end

    gha["GitHub Actions: CI on every pull request<br/>service + agent tests,<br/>k8s manifest validation"]

    subgraph cicd["Jenkins: CI/CD from main only"]
        jenkins["lint, format, 24 tests"]
        scans["Security scans<br/>bandit, pip-audit,<br/>gitleaks, trivy"]
        image["Build image :commit-sha<br/>Trivy image scan"]
        rollout["Deploy, verify rollout<br/>automatic rollback"]
        jenkins --> scans --> image --> rollout
    end

    subgraph cd["Delivery"]
        render["Render<br/>API demo"]
        vercel["Vercel<br/>website"]
    end

    subgraph k8s["Customer network: Kubernetes k3s, namespace veloce"]
        traefik["Traefik Ingress<br/>TLS, rate limit,<br/>security headers"]
        pod["decision-service pod<br/>non-root, read-only"]
        secret["Secret<br/>API_KEY, CARD_HASH_KEY"]
        pvc[("Audit log<br/>PVC")]
        np["NetworkPolicy<br/>in: Traefik only<br/>out: nothing"]
        traefik --> pod
        secret --> pod
        pod --> pvc
        np -.-> pod
    end

    subgraph agents["Agents"]
        verifier["Deploy verifier<br/>drift detection"]
        guardian["Guardian<br/>detects failing pods"]
        reviewer["Rule reviewer<br/>reads code diffs"]
        analyst["Fraud analyst<br/>stats computed locally"]
    end

    store["Store / bank<br/>checkout"]
    model["AI model<br/>aggregated numbers only"]

    dev -->|push| develop
    develop -->|"pull request"| gha
    gha -->|"green: merge"| main
    main -->|"polled every 5 min"| jenkins
    main -->|"auto deploy"| render
    main --> vercel
    rollout -->|"kubectl set image"| pod
    store -->|"HTTPS + X-API-Key"| traefik
    pod -->|"accept / review / reject"| store
    verifier --> render
    verifier --> pod
    guardian --> pod
    develop -.-> reviewer
    pvc --> analyst
    reviewer -.-> model
    analyst -.-> model
```

Solid lines run today; dotted lines are partly built or planned.

## The problem

Today a card payment is usually sent to a fraud engine in a remote cloud. That adds
latency at the checkout and sends card data across the public internet.

## Product promises, and how this repo backs each one

| Promise | Status | How it is backed today |
|---|---|---|
| Runs on-prem | Live | Hardened container on Kubernetes (k3s): non-root, read-only filesystem, probes, resource limits |
| Decides in under 15 ms | Built, not yet load-tested | Local rule engine, no network calls in the decision path; a k6 load test with a p99 target is next |
| Card data never leaves | Live | NetworkPolicy denies all outbound traffic from the pod; local audit log; card number masked; CVV never stored; API key required |
| AI reviews every rule change | Planned | Rule-review agent reads the diff and flags critical findings; not yet a pipeline gate |
| Control from the phone | Partly | Card blocking API is live; alerts to the phone are planned |

## Architecture

```mermaid
flowchart LR
    pos[Store / bank system] -->|HTTPS + X-API-Key| api

    subgraph cluster[Customer network: Kubernetes, egress denied]
        api[decision-service]
        api --> auth{API key valid?}
        auth -->|no| deny[401]
        auth -->|yes| val[Validate card:<br/>Luhn, CVV, expiry]
        val --> blocked{Card blocked?}
        blocked -->|yes| rej1[reject: card_blocked]
        blocked -->|no| score[Risk score 0-100<br/>amount, night hours,<br/>round sums, velocity]
        score --> decision{Decision}
        decision -->|0-39| accept[accept]
        decision -->|40-69| review[review]
        decision -->|70+| reject[reject]
        reject -->|score 90+| block[Block card 24h]
        api --> audit[(Local audit log<br/>JSON Lines, PVC)]
    end
```

### Card blocking without storing card numbers

A rejection with risk score 90 or more blocks the card for 24 hours, and the security
manager can block, list and release cards through `/blocks`. A blocked card is identified
by an HMAC-SHA256 of its number keyed with `CARD_HASH_KEY`: the same card always gives the
same code, the code cannot be turned back into the number, and only blocked cards get one.

## Delivery pipeline

```mermaid
flowchart LR
    dev[Developer] -->|push| develop[develop branch]
    develop -->|pull request| gha[GitHub Actions<br/>service, 3 agents,<br/>kubeconform]
    gha -->|5 green checks: merge| main[main branch<br/>protected]
    main -->|auto deploy| render[Render demo]
    main -->|polled every 5 min| ci[Jenkins CI<br/>lint, tests, bandit,<br/>pip-audit, gitleaks, trivy]
    ci --> build[Build image<br/>:commit-sha]
    build --> scan[Trivy image scan]
    scan --> deploy[k3d image import<br/>kubectl set image]
    deploy --> verify{Rollout ready<br/>within 120 s?}
    verify -->|yes| ok[SUCCESS]
    verify -->|no| undo[rollout undo<br/>FAILURE]
```

Everything is automated except the release decision: merging a pull request into `main`
is a deliberate human gate. After the merge, tests, scans, the image, the deployment, the
verification and, if needed, the rollback all run without anyone touching the cluster.

- **Protected `main`:** a GitHub ruleset allows changes only through a pull request with five
  green checks, and blocks direct pushes, force pushes and deletion. A direct push is
  rejected with `GH013`.
- **CD only from `main`:** Jenkins builds `*/main` only, and loads its `Jenkinsfile` from
  `main`. Push access to `develop` therefore cannot run code on the build host or deploy to
  the cluster (a poisoned-pipeline risk found in an audit of this repository).
- **One image per commit:** every image is tagged with the commit SHA, so each revision of the
  Deployment points to different code and `kubectl rollout undo` really returns to the
  previous release. With a fixed `:dev` tag, a rollback would restore the same broken image.
- **Image scan before deploy:** Trivy blocks images with HIGH or CRITICAL vulnerabilities
  that have a fix (`--ignore-unfixed`), so the pipeline fails on what can be fixed.
- **Zero-downtime rollout:** Kubernetes starts the new pod, waits for its readiness probe,
  and only then removes the old one.
- **Verify and automatic rollback:** Jenkins waits up to 120 seconds for the rollout. If the
  new pod never becomes ready, it runs `rollout undo` and marks the build red.
- **What GitHub Actions checks:** the decision service (lint, format, tests), each agent in
  a parallel matrix job, and every Kubernetes manifest against the API schema of the
  cluster version with kubeconform. It runs on every pull request, because the ruleset
  requires its checks.
- **DevSecOps:** Jenkins scans every build for vulnerable code (bandit), vulnerable
  dependencies (pip-audit), secrets anywhere in git history (gitleaks), and
  vulnerabilities or misconfigurations in files and the Dockerfile (trivy).
- **Pinned versions, kept fresh:** application dependencies, CI tools and base images use
  exact versions, so a build gives the same result today and next month. Dependabot opens a
  weekly pull request for updates, and GitHub security updates are enabled.
- **Drift detection:** the deploy verifier compares the endpoints the live API serves with
  the endpoints in the code. It found the Render demo deploying from an old branch,
  43 commits behind `main`; after the fix it passes 5/5 checks.

### Rollback, proven

The rollback was tested with a deliberately broken release: the service listened on the
wrong port, which passed every test and every scan.

| Build | Commit | Result |
|---|---|---|
| #68 | `d763b22` | Deployed and verified |
| #69 | `383b904` (wrong port) | Deployed; the new pod never became ready; Verify timed out after 120 s; `rollout undo` restored `d763b22`; build red. The old pod kept serving throughout |
| #70 | `57014fe` (revert) | Deployed and verified |

### Jenkins as code, with least privilege

Jenkins itself is defined in the repository and has only the rights it needs.

| File | What it does |
|---|---|
| [`jenkins/Dockerfile`](jenkins/Dockerfile) | Pinned base image with OS security updates; pinned trivy, gitleaks, Docker CLI, kubectl (SHA-256 verified) and k3d |
| [`jenkins/docker-compose.yml`](jenkins/docker-compose.yml) | Runs Jenkins on `127.0.0.1:8080` only, with the Docker socket and the cluster network; jobs live in the `jenkins_home` volume |
| [`k8s/jenkins-deployer.yaml`](k8s/jenkins-deployer.yaml) | ServiceAccount for Jenkins: may update and roll back Deployments in `veloce`; cannot read Secrets, delete anything, or reach other namespaces |
| [`jenkins/kubeconfig.sh`](jenkins/kubeconfig.sh) | Builds the deployer kubeconfig without printing the token; it is stored only as an encrypted Jenkins credential |

```bash
docker compose -f jenkins/docker-compose.yml up -d --build
kubectl auth can-i get secrets -n veloce --as=system:serviceaccount:veloce:jenkins-deployer   # no
```

Mounting the Docker socket gives Jenkins root on the host. That is accepted for a local lab;
a production setup would build images with rootless BuildKit or Kaniko instead.

## Kubernetes

The cluster itself is code in [`k3d/cluster.yaml`](k3d/cluster.yaml): one server, two
agents, a pinned k3s version, and only port 8443 (HTTPS) opened.

| Manifest | What it does |
|---|---|
| `namespace.yaml`, `deployment.yaml`, `service.yaml` | The service, hardened: non-root, read-only filesystem, probes, limits, PVC for the audit log |
| `certificate.yaml` | cert-manager: a local CA and a TLS certificate for `veloce.localhost` |
| `ingress.yaml` | Traefik on HTTPS only; plain HTTP is never served |
| `middlewares.yaml` | Rate limit (10 req/s per client, burst 20, then 429) and security headers (HSTS, nosniff, frame deny, no server header) |
| `networkpolicy.yaml` | In: only Traefik may reach the pod. Out: nothing may leave it |
| `jenkins-deployer.yaml` | Least-privilege identity that Jenkins uses to deploy and roll back |

After the first install, Jenkins owns the image of the Deployment: each release sets
`decision-service=veloce/decision-service:<commit>`. The `:dev` tag in `deployment.yaml` is
only the bootstrap image, so re-applying that file by hand would roll the service back;
moving the tag into Kustomize is planned.

```bash
# 1. Cluster and cert-manager
k3d cluster create --config k3d/cluster.yaml
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.21.2/cert-manager.yaml
kubectl wait --for=condition=Available deployment --all -n cert-manager --timeout=180s

# 2. Image and secret
docker build -t veloce/decision-service:dev services/decision-service
k3d image import veloce/decision-service:dev -c veloce
kubectl apply -f k8s/namespace.yaml
kubectl create secret generic decision-service-secrets -n veloce \
  --from-literal=API_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  --from-literal=CARD_HASH_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# 3. Everything else
kubectl apply -f k8s/
kubectl -n veloce rollout status deployment/decision-service

# 4. Trust the local CA and call the API over HTTPS
kubectl get secret veloce-local-ca -n cert-manager -o jsonpath='{.data.ca\.crt}' | base64 -d > veloce-ca.crt
curl --cacert veloce-ca.crt https://veloce.localhost:8443/health
```

Prove each security layer:

```bash
# HTTPS only: plain HTTP is not served
curl -s -o /dev/null -w "%{http_code}\n" http://veloce.localhost:8443/health        # 404

# Rate limit: 200 fast requests, the extra ones get 429
for i in $(seq 200); do curl -s -o /dev/null -w "%{http_code}\n" --cacert veloce-ca.crt \
  https://veloce.localhost:8443/health; done | sort | uniq -c

# Ingress policy: a pod inside the cluster cannot skip Traefik
kubectl run attacker --rm -i --restart=Never -n veloce --image=curlimages/curl -- \
  curl -s -m 3 http://decision-service/health                                        # times out

# Egress policy: nothing can leave the pod
kubectl exec -n veloce deploy/decision-service -- \
  python -c "import urllib.request; urllib.request.urlopen('https://example.com', timeout=5)"  # fails
```

k3s enforces NetworkPolicy out of the box; Docker Desktop's built-in Kubernetes does not.

## Engineering decisions

| Decision | Why |
|---|---|
| NetworkPolicy denies all egress | "Data never leaves" is enforced by the network, not only by the code (defense in depth) |
| Only Traefik may reach the pod | A compromised pod elsewhere in the cluster cannot skip TLS, the rate limit and the security headers |
| Rate limit at the Ingress, not in Python | A flood is refused with 429 before it reaches the service, so real decisions keep their latency |
| Exact versions for dependencies and CI tools | An unpinned linter once passed locally (ruff 0.16) and failed in CI (ruff 0.17) on the same code |
| Deploy verifier compares live endpoints with the code | Configuration drift is found by a check, not by a customer |
| CD only from a protected `main` | Whoever controls the `Jenkinsfile` runs code with the deploy credential; only reviewed, green code may do that |
| Images tagged with the commit SHA, never `:dev` | Each release is traceable to its code, and a rollback returns to a different image |
| Verify the rollout, roll back automatically | A release that passes tests but never becomes ready is undone without a person (proven with build #69) |
| Jenkins gets its own ServiceAccount, not the admin kubeconfig | A compromised CI server can update one Deployment, not read Secrets or take over the cluster |
| Merging into `main` stays manual | Everything else is automated; a person decides when a release reaches the bank |
| Card blocked by HMAC, not by number | The blocklist works without storing card numbers; useless without the key |
| Audit log on local disk, not S3 | Uploading inside the request broke the 15 ms budget and sent card data off-site |
| API key and hash key **fail closed** | A server with a missing key rejects every request (503) instead of running open |
| Constant-time key comparison | `secrets.compare_digest` prevents timing attacks |
| Non-root, read-only container, all capabilities dropped | A compromised process can neither escalate nor change files |
| Secrets never in git | `.env` locally, Kubernetes Secret created with `kubectl`, Render environment variables |
| `.vercelignore` allowlist | Only the website is uploaded; secrets and services can never be published by mistake |
| One replica for now | Decisions, velocity and blocks are in memory; Redis is next, then more replicas |
| Velocity counted per customer | Counting all traffic flagged honest customers during busy hours (found and fixed with a regression test) |

## API

All endpoints except `/health` and `/readiness` require the `X-API-Key` header.

| Method | Path | Purpose |
|---|---|---|
| POST | `/decide_transaction` | Validate, score and decide on a transaction |
| GET | `/decisions/{decision_id}` | Read a stored decision |
| POST | `/get_check_transaction` | Read a decision and record the check in the audit log |
| POST | `/blocks` | Block a card (security manager) |
| GET | `/blocks` | List blocked cards (last 4 digits only) |
| DELETE | `/blocks/{block_id}` | Release a card |
| GET | `/calculate_geo_risk` | Geo risk for an IP country vs card country |
| GET | `/health`, `/readiness` | Probes, open without a key |

### Environment

| Variable | Required | Purpose |
|---|---|---|
| `API_KEY` | yes | Key clients send in `X-API-Key` |
| `CARD_HASH_KEY` | yes | Secret for the HMAC that identifies blocked cards |
| `AUDIT_LOG_PATH` | no | Local audit log file (JSON Lines); empty disables auditing |

Without `API_KEY` or `CARD_HASH_KEY` the service fails closed and answers 503.
Generate a key with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.

## Run it locally with Docker

```bash
cd services/decision-service
cp .env.example .env    # then set API_KEY and CARD_HASH_KEY
docker compose up -d --build
curl localhost:8001/health
```

API docs: http://localhost:8001/docs (click **Authorize** and enter the key).

### Checks (same as CI)

```bash
cd services/decision-service
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/pytest -q
.venv/bin/bandit -r app --severity-level medium
.venv/bin/pip-audit -r requirements.txt
```

Agents (from each agent folder, for example `agents/guardian`):

```bash
pytest -q
```

Check that the live environments match the code:

```bash
services/decision-service/.venv/bin/python agents/deploy-verifier/verifier.py --k8s-ca veloce-ca.crt
```

## Repository layout

```
services/decision-service/   decision API (FastAPI), tests, Dockerfile, docker-compose
k3d/cluster.yaml             the local Kubernetes cluster as code
k8s/                         Kubernetes manifests: service, TLS, Ingress, middlewares, NetworkPolicy, Jenkins RBAC
agents/deploy-verifier/      checks that Render, Kubernetes and the website run what the code says
agents/guardian/             detects failing pods and diagnoses them from events, logs and playbooks
agents/rule-review/          AI reviewer for rule changes
agents/fraud-analyst/        AI analyst: fraud statistics report from the audit log
jenkins/                     Jenkins as code: Dockerfile, docker-compose.yml, kubeconfig script
Jenkinsfile                  CI/CD: tests, scans, image build and scan, deploy, verify, rollback
.github/workflows/           GitHub Actions: service, agents, Kubernetes manifests
.github/dependabot.yml       weekly updates for pip packages, base images and Actions
render.yaml                  demo deployment of the API
index.html, assets/          website on Vercel
ROADMAP.md                   what is built and what comes next
```

## What comes next

A Makefile that rebuilds the whole environment from git in one command, with the Kubernetes
API bound to localhost and Secrets encrypted at rest; a k6 load test and Prometheus and
Grafana to prove the 15 ms promise, with an SLO alert to Telegram; Kustomize so the image tag
lives in git; security scans and an image build in GitHub Actions; and a Helm chart for
on-prem installs. Details in [ROADMAP.md](ROADMAP.md).

# Veloce AI: Roadmap

What is built, and what comes next. The goal of the project is a complete DevOps chain,
from commit to a service that runs, is secured and is observed on Kubernetes.

```
commit → CI (lint, tests, security scans) → image → deploy → verify / rollback → monitoring → phone alerts
                                                                                  ^ next
```

## Product promises

| Promise | Status | Backed by |
|---|---|---|
| Runs on-prem | Live | Hardened container on Kubernetes (k3s), delivered by an on-prem Jenkins |
| Decides in under 15 ms | Built, not yet load-tested | Local rules, no network calls in the decision path |
| Card data never leaves | Live | NetworkPolicy in both directions, local audit log, masked card numbers, no CVV storage |
| AI reviews every rule change | Planned | Rule-review agent built; not yet a pipeline gate |
| Control from the phone | Partly | Card blocking API live; phone alerts planned |

---

## Done

### Decision service
- [x] Risk rules: amount, night hours, round amounts, velocity per customer
- [x] Card validation: Luhn, CVV, expiry, amount > 0, timestamp with timezone; card numbers with letters rejected
- [x] Card number masked, CVV never stored
- [x] Local append-only audit log instead of uploading to S3 inside the request
- [x] API key authentication, fail closed, constant-time comparison; non-ASCII keys get 401, not 500
- [x] Card blocking by HMAC fingerprint: automatic (score 90+, 24 hours) and manual (`/blocks`)
- [x] Bugs found and fixed with regression tests: negative amounts, naive timestamps,
      velocity counting all customers, unauthenticated S3 listing endpoints
- [x] 24 tests, with shared test data in `tests/data.py`

### CI
- [x] GitHub Actions on every pull request: decision service, three agents in a matrix,
      kubeconform for every Kubernetes manifest
- [x] Jenkins (self-hosted in Docker): lint, format, tests, bandit, pip-audit, gitleaks, trivy
- [x] Pinned versions for dependencies, CI tools and base images
- [x] Dependabot weekly updates for pip, Docker images and GitHub Actions; security updates enabled

### CD
- [x] Jenkins builds `main` only, polled every 5 minutes
- [x] Image tagged with the commit SHA, scanned with Trivy before deploy
- [x] Deploy to k3s with a zero-downtime rolling update
- [x] Verify the rollout (120 s) and roll back automatically on failure, proven with a
      deliberately broken release (builds #68, #69, #70)

### Security
- [x] `main` protected by a ruleset: pull request with five green checks; no direct or force pushes
- [x] Public repository, gitleaks clean across the whole history
- [x] Jenkins as code (`jenkins/`), reachable from localhost only
- [x] Least-privilege ServiceAccount for Jenkins, verified with `kubectl auth can-i`;
      kubeconfig stored only as an encrypted Jenkins credential
- [x] Secrets only in the environment, never in git; `.vercelignore` allowlist

### Containers and Kubernetes
- [x] Cluster as code (`k3d/cluster.yaml`), pinned k3s version
- [x] Multi-stage Docker image, non-root user, healthcheck
- [x] Kubernetes manifests: Namespace, Deployment, Service, PVC for the audit log
- [x] Liveness and readiness probes, resource requests and limits
- [x] Non-root, read-only root filesystem, all capabilities dropped
- [x] HTTPS with cert-manager and a local CA; Traefik on HTTPS only
- [x] Traefik rate limit and security headers
- [x] NetworkPolicy: only Traefik may reach the pod, and nothing may leave it

### Delivery
- [x] API demo on Render (deploys from `main`), website on Vercel

### Agents
- [x] Deploy verifier: live endpoints compared with the code (found Render 43 commits behind)
- [x] Fraud analyst: statistics computed locally, only aggregated numbers sent to the model
- [x] Guardian steps 1–2: detect failing pods, diagnose them from events, logs and playbooks

---

## Next

### Infrastructure as code and hardening
- [ ] Makefile: `make cluster`, `make deploy`, `make destroy`; rebuild everything from git
- [ ] Kubernetes API and HTTPS port bound to localhost; Secrets encrypted at rest
- [ ] AWS keys out of local `.env` files
- [ ] Kustomize, so the deployed image tag lives in git (no drift)

### Decision service
- [ ] Remove `policy_thresholds` and `card_expiry` from responses
- [ ] 409 for a duplicate `transaction_id`
- [ ] Server time instead of the client timestamp for velocity and night hours

### Observability
- [ ] `/metrics` for Prometheus: decision latency histogram, decisions by type, blocks
- [ ] Prometheus and Grafana in the cluster
- [ ] k6 load test: p99 decision latency under 15 ms
- [ ] Alertmanager to Telegram: blocked cards, SLO breaches

### CI
- [ ] Security scans and an image build in GitHub Actions too
- [ ] GitHub Actions pinned by commit SHA
- [ ] Rule-review agent as a pipeline gate on pull requests

### Agents
- [ ] Guardian steps 3–4: prepare a fix, apply it only after a person approves
- [ ] Orchestrator (`agents/veloce.py`): one entry point for every agent

### Later
- [ ] Helm chart for on-prem installs, then GitOps
- [ ] Air-gapped install with a local registry
- [ ] Keycloak and OIDC instead of a shared API key
- [ ] Redis for decisions, velocity and blocks; more than one replica
- [ ] Terraform for a cloud VM running k3s

# Veloce AI: Roadmap

What is built, and what comes next. The goal of the project is a complete DevOps chain,
from commit to a service that runs, is secured and is observed on Kubernetes.

```
commit → CI (lint, tests, security scans) → image → GitOps → Kubernetes → monitoring → phone alerts
```

## Product promises

| Promise | Status | Backed by |
|---|---|---|
| Runs on-prem | Live | Hardened container on Kubernetes (k3s) |
| Decides in under 15 ms | Live (measured, not yet monitored) | Local rules, no network calls in the decision path |
| Card data never leaves | Live | NetworkPolicy denying egress, local audit log, masked card numbers, no CVV storage |
| AI reviews every rule change | Planned | Rule-review agent built; not yet a pipeline gate |
| Control from the phone | Partly | Card blocking API live; phone alerts planned |

---

## Done

### Decision service
- [x] Risk rules: amount, night hours, round amounts, velocity per customer
- [x] Card validation: Luhn, CVV, expiry, amount > 0, timestamp with timezone
- [x] Card number masked, CVV never stored
- [x] Local append-only audit log instead of uploading to S3 inside the request
- [x] API key authentication, fail closed, constant-time comparison
- [x] Card blocking by HMAC fingerprint: automatic (score 90+, 24 hours) and manual (`/blocks`)
- [x] Bugs found and fixed with regression tests: negative amounts, naive timestamps,
      velocity counting all customers, unauthenticated S3 listing endpoints
- [x] 22 tests

### CI/CD and security
- [x] Jenkins (self-hosted in Docker) and GitHub Actions: lint, format, tests
- [x] Security scans on every commit: bandit, pip-audit, gitleaks, trivy
- [x] Branching: `develop` for work, `main` only through pull requests with green checks
- [x] Secrets only in the environment, never in git; `.vercelignore` allowlist

### Containers and Kubernetes
- [x] Multi-stage Docker image, non-root user, healthcheck
- [x] Kubernetes manifests: Namespace, Deployment, Service, PVC for the audit log
- [x] Liveness and readiness probes, resource requests and limits
- [x] Non-root, read-only root filesystem, all capabilities dropped
- [x] Secret for `API_KEY` and `CARD_HASH_KEY`, created with kubectl
- [x] NetworkPolicy denying all egress, verified on k3s

### Delivery
- [x] API demo on Render, website on Vercel

---

## Next

### Before release
- [ ] `API_KEY` and `CARD_HASH_KEY` on Render, then merge `develop` into `main`
- [ ] Tag `v2.0.0` and publish a GitHub release

### Shared state
- [ ] Redis for decisions, velocity and blocks, so they survive restarts
- [ ] Velocity as a sliding 10-minute window per customer (constant time)
- [ ] More than one replica

### Observability
- [ ] `/metrics` for Prometheus: decision latency histogram, decisions by type, blocks
- [ ] Grafana dashboard
- [ ] Alert when p99 decision latency exceeds 15 ms
- [ ] Alertmanager to Telegram: blocked cards, SLO breaches

### Delivery and infrastructure
- [ ] Build and push images to a registry (GHCR or ECR), scan the image in CI
- [ ] Rule-review agent as a pipeline gate on pull requests
- [ ] Helm chart and GitOps with Flux
- [ ] Terraform for a cloud VM running k3s, state in S3
- [ ] Pinned dependency versions

### Product
- [ ] AI analyst for `review` decisions, asynchronous and without card data
- [ ] Next.js frontend: live demo form and control center
- [ ] Audit archive to S3 through Fluent Bit (least-privilege IAM, encryption)

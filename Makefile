# Veloce AI: the whole local environment from git.
#   make up        create or update everything, in the right order (safe to run again)
#   make verify    check that what runs matches the code
#   make destroy   delete the cluster (asks first)
# Every target can run again: it skips what already exists and never replaces secrets.

CLUSTER              := veloce
NAMESPACE            := veloce
IMAGE                := veloce/decision-service
CERT_MANAGER_VERSION := v1.21.2
VENV                 := services/decision-service/.venv/bin
CA_FILE              := veloce-ca.crt

.DEFAULT_GOAL := help
.PHONY: help up cluster cert-manager image secrets deploy jenkins-network ca verify status jenkins-credential destroy

help: ## Show the commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-20s %s\n", $$1, $$2}'

up: deploy jenkins-network ca verify ## Create or update the whole environment
	@echo
	@echo "Ready: https://veloce.localhost:8443/health"
	@echo "After a new cluster, Jenkins needs a new credential: make jenkins-credential"

cluster: ## Create the k3d cluster from k3d/cluster.yaml, unless it exists
	@k3d cluster get $(CLUSTER) >/dev/null 2>&1 \
		&& echo "cluster $(CLUSTER) already exists" \
		|| k3d cluster create --config k3d/cluster.yaml

cert-manager: cluster ## Install cert-manager (pinned) and wait until it is ready
	kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/$(CERT_MANAGER_VERSION)/cert-manager.yaml
	kubectl -n cert-manager wait --for=condition=Available deployment --all --timeout=180s

image: cluster ## Build the bootstrap image and import it into the cluster
	docker build -t $(IMAGE):dev services/decision-service
	k3d image import $(IMAGE):dev -c $(CLUSTER)

secrets: cluster ## Create API_KEY and CARD_HASH_KEY once; existing keys are never replaced
	kubectl apply -f k8s/namespace.yaml
	@kubectl -n $(NAMESPACE) get secret decision-service-secrets >/dev/null 2>&1 \
		&& echo "secret decision-service-secrets already exists, kept" \
		|| kubectl -n $(NAMESPACE) create secret generic decision-service-secrets \
			--from-literal=API_KEY="$$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" \
			--from-literal=CARD_HASH_KEY="$$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"

# deployment.yaml is applied only on a new cluster. After that, Jenkins owns the image tag,
# and re-applying the file would roll the service back to the :dev bootstrap image.
deploy: cert-manager secrets ## Apply the manifests and wait for the service
	@if kubectl -n $(NAMESPACE) get deployment decision-service >/dev/null 2>&1; then \
		echo "deployment exists, Jenkins owns its image: deployment.yaml skipped"; \
	else \
		$(MAKE) image && kubectl apply -f k8s/deployment.yaml; \
	fi
	kubectl apply -f k8s/service.yaml -f k8s/certificate.yaml -f k8s/middlewares.yaml \
		-f k8s/ingress.yaml -f k8s/networkpolicy.yaml -f k8s/jenkins-deployer.yaml
	kubectl -n $(NAMESPACE) rollout status deployment/decision-service --timeout=180s

jenkins-network: ## Connect Jenkins to the cluster network (needed after a new cluster)
	@docker network connect k3d-$(CLUSTER) jenkins 2>/dev/null \
		&& echo "jenkins connected to k3d-$(CLUSTER)" \
		|| echo "jenkins already on k3d-$(CLUSTER), or not running"

ca: ## Export the local CA so curl can trust https://veloce.localhost:8443
	@kubectl -n $(NAMESPACE) wait --for=condition=Ready certificate/decision-service-tls --timeout=120s >/dev/null
	@kubectl -n cert-manager get secret veloce-local-ca -o jsonpath='{.data.ca\.crt}' | base64 -d > $(CA_FILE)
	@echo "wrote $(CA_FILE)"

verify: ca ## Check HTTPS, Render, the pods and the website against the code
	curl -sS --cacert $(CA_FILE) https://veloce.localhost:8443/health && echo
	$(VENV)/python agents/deploy-verifier/verifier.py --k8s-ca $(CA_FILE)

status: ## Show the cluster, the running image and the pods
	@k3d cluster list
	@echo "image: $$(kubectl -n $(NAMESPACE) get deploy decision-service -o jsonpath='{..image}' 2>/dev/null)"
	@kubectl -n $(NAMESPACE) get pods 2>/dev/null || true

jenkins-credential: ## Build a new kubeconfig for Jenkins (upload it as k3d-veloce-kubeconfig)
	jenkins/kubeconfig.sh
	@echo "Jenkins > Manage Jenkins > Credentials > k3d-veloce-kubeconfig > Update: upload the file above, then delete it"

destroy: ## Delete the cluster, its secrets and the audit log (asks first)
	@read -p "Delete cluster $(CLUSTER), its secrets and audit log? Type yes: " answer; \
		[ "$$answer" = yes ] || { echo "cancelled"; exit 1; }
	k3d cluster delete $(CLUSTER)

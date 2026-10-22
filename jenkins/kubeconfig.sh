#!/usr/bin/env bash
# Builds a kubeconfig for Jenkins from the jenkins-deployer ServiceAccount token.
# The token is never printed; the file is readable only by you (mode 600).
# Upload the file to Jenkins as a "Secret file" credential, then delete it.
#
# Usage: jenkins/kubeconfig.sh [output-file]
set -euo pipefail

out="${1:-$HOME/.kube/jenkins-deployer.kubeconfig}"
namespace=veloce
secret=jenkins-deployer-token
# Address of the API server on the k3d-veloce Docker network, where Jenkins runs.
server=https://k3d-veloce-server-0:6443

ca="$(kubectl -n "$namespace" get secret "$secret" -o jsonpath='{.data.ca\.crt}')"
token="$(kubectl -n "$namespace" get secret "$secret" -o jsonpath='{.data.token}' | base64 -d)"

umask 077
mkdir -p "$(dirname "$out")"
cat > "$out" <<EOF
apiVersion: v1
kind: Config
clusters:
  - name: k3d-veloce
    cluster:
      server: $server
      certificate-authority-data: $ca
users:
  - name: jenkins-deployer
    user:
      token: $token
contexts:
  - name: jenkins-deployer@k3d-veloce
    context:
      cluster: k3d-veloce
      user: jenkins-deployer
      namespace: $namespace
current-context: jenkins-deployer@k3d-veloce
EOF

echo "Wrote $out"

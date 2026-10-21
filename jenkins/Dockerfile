FROM jenkins/jenkins:lts-jdk21

USER root

RUN apt-get update && apt-get install -y python3 python3-venv python3-pip git curl \
    && rm -rf /var/lib/apt/lists/*

# Security scanners used by the pipeline, pinned to exact versions.
ARG TRIVY_VERSION=0.75.0
ARG GITLEAKS_VERSION=8.30.1
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
      amd64) trivy_arch=64bit; gitleaks_arch=x64 ;; \
      arm64) trivy_arch=ARM64; gitleaks_arch=arm64 ;; \
      *) echo "unsupported arch: $arch"; exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-${trivy_arch}.tar.gz" \
      | tar -xz -C /usr/local/bin trivy; \
    curl -fsSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${gitleaks_arch}.tar.gz" \
      | tar -xz -C /usr/local/bin gitleaks; \
    trivy --version; gitleaks version

# Docker CLI only (the client, not the daemon). Jenkins sends build commands
# to the host's Docker through the mounted /var/run/docker.sock.
ARG DOCKER_VERSION=29.2.0
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
      amd64) docker_arch=x86_64 ;; \
      arm64) docker_arch=aarch64 ;; \
      *) echo "unsupported arch"; exit 1 ;; \
    esac; \
    curl -fsSL "https://download.docker.com/linux/static/stable/${docker_arch}/docker-${DOCKER_VERSION}.tgz" \
      | tar -xz -C /usr/local/bin --strip-components=1 docker/docker; \
    docker --version

# kubectl (same version as the cluster) and k3d, to deploy to the local cluster.
# kubectl is checked against its published SHA-256, so a tampered download fails the build.
ARG KUBECTL_VERSION=1.35.5
ARG K3D_VERSION=5.9.0
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/${arch}/kubectl"; \
    echo "$(curl -fsSL "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/${arch}/kubectl.sha256")  /usr/local/bin/kubectl" \
      | sha256sum --check; \
    curl -fsSLo /usr/local/bin/k3d "https://github.com/k3d-io/k3d/releases/download/v${K3D_VERSION}/k3d-linux-${arch}"; \
    chmod +x /usr/local/bin/kubectl /usr/local/bin/k3d; \
    kubectl version --client; k3d version

USER jenkins

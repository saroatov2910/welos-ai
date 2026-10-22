// CI pipeline for decision-service: install -> lint -> format -> tests -> security scans.
pipeline {
    agent any

    // Check GitHub for new commits every 5 minutes (webhooks can't reach localhost).
    triggers {
        pollSCM('H/5 * * * *')
    }

    options {
        timeout(time: 15, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        SERVICE_DIR = 'services/decision-service'
        IMAGE = 'veloce/decision-service'
    }

    stages {
        stage('Install') {
            steps {
                dir("${SERVICE_DIR}") {
                    sh '''
                        python3 -m venv .venv
                        .venv/bin/pip install --quiet --upgrade pip
                        .venv/bin/pip install --quiet -r requirements-dev.txt
                    '''
                }
            }
        }

        stage('Lint') {
            steps {
                dir("${SERVICE_DIR}") {
                    sh '.venv/bin/ruff check app tests'
                }
            }
        }

        stage('Format check') {
            steps {
                dir("${SERVICE_DIR}") {
                    sh '.venv/bin/ruff format --check app tests'
                }
            }
        }

        stage('Tests') {
            steps {
                dir("${SERVICE_DIR}") {
                    sh '.venv/bin/pytest -q --junitxml=test-results.xml'
                }
            }
            post {
                always {
                    junit "${SERVICE_DIR}/test-results.xml"
                }
            }
        }

        // DevSecOps: every commit is scanned. A finding fails the build.
        stage('Security: code (bandit)') {
            steps {
                dir("${SERVICE_DIR}") {
                    sh '.venv/bin/bandit -r app --severity-level medium'
                }
            }
        }

        stage('Security: dependencies (pip-audit)') {
            steps {
                dir("${SERVICE_DIR}") {
                    sh '.venv/bin/pip-audit -r requirements.txt'
                }
            }
        }

        stage('Security: secrets in git (gitleaks)') {
            steps {
                sh 'gitleaks git . --redact --no-banner'
            }
        }

        stage('Security: files and Dockerfile (trivy)') {
            steps {
                sh '''
                    trivy fs --quiet --cache-dir "$JENKINS_HOME/.cache/trivy" \
                      --scanners vuln,misconfig,secret \
                      --severity HIGH,CRITICAL --exit-code 1 \
                      --skip-dirs "${SERVICE_DIR}/.venv" \
                      "${SERVICE_DIR}"
                '''
            }
        }

        // Every image is tagged with its commit, so each version has its own name
        // and a rollback really returns to the previous code.
        stage('Build image') {
            steps {
                script {
                    env.IMAGE_TAG = sh(script: 'git rev-parse --short=7 HEAD', returnStdout: true).trim()
                }
                sh 'docker build -t "$IMAGE:$IMAGE_TAG" "$SERVICE_DIR"'
                echo "Built ${env.IMAGE}:${env.IMAGE_TAG}"
            }
        }

                // The image never reaches the cluster with a HIGH or CRITICAL vulnerability that has a fix.
        stage('Scan image') {
            steps {
                sh '''
                    trivy image --quiet --cache-dir "$JENKINS_HOME/.cache/trivy" \
                      --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 \
                      "$IMAGE:$IMAGE_TAG"
                '''
            }
        }


      // Moves the scanned image into the cluster and rolls the Deployment to it.
        // Kubernetes starts the new pod first and removes the old one only when the new one is ready.
        stage('Deploy') {
            steps {
                sh 'k3d image import "$IMAGE:$IMAGE_TAG" -c veloce'
                withCredentials([file(credentialsId: 'k3d-veloce-kubeconfig', variable: 'KUBECONFIG')]) {
                    sh 'kubectl -n veloce set image deployment/decision-service decision-service="$IMAGE:$IMAGE_TAG"'
                }
            }
        } 
    }

    post {
        success { echo 'All checks passed.' }
        failure { echo 'Pipeline failed - see the stage marked in red.' }
    }
}

// CI/CD pipeline for decision-service, built from main only:
// install -> lint -> format -> tests -> security scans -> build image -> scan image
// -> deploy -> verify, with an automatic rollback when anything after the deploy fails.
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

        // Only a change to the service, or a person pressing Build Now, builds and deploys.
        // A change to the website or the docs is still checked, but does not restart the pod,
        // because blocks and velocity counters are still kept in memory.
        stage('Release') {
            when {
                anyOf {
                    changeset 'services/decision-service/**'
                    triggeredBy 'UserIdCause'
                }
            }
            stages {
                // Every image is tagged with its commit, so each version has its own name
                // and a rollback really returns to the previous code.
                stage('Build image') {
                    steps {
                        script {
                            env.IMAGE_TAG = sh(script: 'git rev-parse --short=7 HEAD', returnStdout: true).trim()
                        }
                        sh 'docker build --pull -t "$IMAGE:$IMAGE_TAG" "$SERVICE_DIR"'
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
                        script { env.DEPLOYED = 'true' }
                    }
                }

                // Waits until the new pod is ready. A pod that never becomes ready fails the build.
                stage('Verify') {
                    steps {
                        withCredentials([file(credentialsId: 'k3d-veloce-kubeconfig', variable: 'KUBECONFIG')]) {
                            sh 'kubectl -n veloce rollout status deployment/decision-service --timeout=120s'
                        }
                    }
                }
            }
        }
    }

    post {
        success { echo 'All checks passed.' }
        // unsuccessful covers a failed build and one a person aborted during the rollout.
        unsuccessful {
            echo 'Pipeline did not finish - see the stage marked in red.'
            script {
                // A deploy that did not finish is rolled back to the previous revision automatically.
                if (env.DEPLOYED == 'true') {
                    withCredentials([file(credentialsId: 'k3d-veloce-kubeconfig', variable: 'KUBECONFIG')]) {
                        sh 'kubectl -n veloce rollout undo deployment/decision-service'
                        sh 'kubectl -n veloce rollout status deployment/decision-service --timeout=120s'
                    }
                }
            }
        }
    }
}

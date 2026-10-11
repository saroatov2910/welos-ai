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
    }

    post {
        success { echo 'All checks passed.' }
        failure { echo 'Pipeline failed - see the stage marked in red.' }
    }
}

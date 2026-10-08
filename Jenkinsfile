// CI pipeline for decision-service: install -> lint -> format check -> tests.
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
    }

    post {
        success { echo 'All checks passed.' }
        failure { echo 'Pipeline failed - see the stage marked in red.' }
    }
}

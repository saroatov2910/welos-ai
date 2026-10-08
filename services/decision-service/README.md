# decision-service

Real-time card-fraud decision API (FastAPI). Scores each transaction and returns
`accept`, `review` or `reject` with the reasons behind the score.

## Run with Docker (recommended)

```bash
docker compose up -d --build
curl localhost:8001/health      # {"status":"ok"}
```

API docs: http://localhost:8001/docs. The audit log is kept in the `audit-logs` volume:

```bash
docker compose exec decision-service cat /var/log/decision-service/decisions.jsonl
```

## Run locally (for development)

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

## Environment

Copy [.env.example](.env.example) to `.env`.

- `AUDIT_LOG_PATH`: file for the local, append-only audit log (JSON Lines).
  Leave empty to disable auditing. The Docker image sets it to
  `/var/log/decision-service/decisions.jsonl`.

## Checks (same as CI)

```bash
ruff check app tests
ruff format --check app tests
pytest -q
```

## Dependency layout

- `requirements.txt`: runtime dependencies
- `requirements-dev.txt`: development and test dependencies

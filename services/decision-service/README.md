# decision-service

## Setup

```bash
cd ~/Desktop/welos-ai/services/decision-service
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

## Environment

Copy [.env.example](.env.example) to `.env` and fill in your AWS values if you want S3 audit uploads.

- `AWS_REGION`: AWS region for the S3 client
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`: AWS credentials
- `ENABLE_S3_AUDIT`: set to `true` to upload audit JSON to S3
- `S3_AUDIT_BUCKET`: destination bucket for audit files
- `S3_AUDIT_PREFIX`: optional key prefix inside the bucket

## Daily use

```bash
cd ~/Desktop/welos-ai/services/decision-service
source .venv/bin/activate
python -V
pip list
```

## Dependency layout

- `requirements.txt`: runtime dependencies for the service
- `requirements-dev.txt`: development and test dependencies

## Optional: run tests

```bash
pytest -q
```

## Optional: run FastAPI app

If you add `app/main.py` with a FastAPI object named `app`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

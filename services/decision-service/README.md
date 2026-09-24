# decision-service

## Setup

```bash
cd ~/Desktop/welos-ai/services/decision-service
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install fastapi "uvicorn[standard]" pytest httpx
```

## Daily use

```bash
cd ~/Desktop/welos-ai/services/decision-service
source .venv/bin/activate
python -V
pip list
```

## Optional: run tests

```bash
pytest -q
```

## Optional: run FastAPI app

If you add `app/main.py` with a FastAPI object named `app`:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

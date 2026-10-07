import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI

from app.models import CheckTransactionRequest, DecideTransactionRequest
from app.s3_resource_service import check_s3_connection, list_s3_files, save_add_recode
from app.services import get_decision_or_404, save_transaction_decision

load_dotenv()

app = FastAPI(title="WelosAI Decision Service")


@app.post("/get_check_transaction")
def get_check_transaction(request: CheckTransactionRequest):
    result = get_decision_or_404(request.transaction_id)

    bucket_name = os.getenv("S3_AUDIT_BUCKET")
    if bucket_name:
        key = f"decision-service/check-transaction/{request.transaction_id}.json"
        save_add_recode(
            bucket_name=bucket_name,
            key=key,
            data=json.dumps(result, ensure_ascii=False).encode("utf-8"),
        )

    return result


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/readiness")
def readiness():
    return {"ready": True}


@app.get("/is_entity_blocked/{entity_id}")
def is_entity_blocked_endpoint(entity_id: str):
    return {"entity_id": entity_id, "blocked": False}


@app.post("/block_entity_if_needed")
def block_entity_if_needed_endpoint(entity_id: str, risk_score: int, threshold: int = 80):
    blocked_now = risk_score >= threshold
    return {
        "entity_id": entity_id,
        "risk_score": risk_score,
        "threshold": threshold,
        "blocked_now": blocked_now,
    }


@app.get("/calculate_geo_risk")
def calculate_geo_risk_endpoint(ip_country: str, card_country: str):
    if ip_country.strip().upper() == card_country.strip().upper():
        return {"geo_risk_score": 0, "reason": "geo_match"}
    return {"geo_risk_score": 20, "reason": "geo_mismatch"}


@app.get("/s3/connection")
def s3_connection(bucket_name: str | None = None):
    return check_s3_connection(bucket_name=bucket_name)


@app.get("/s3/files")
def s3_files(bucket_name: str, prefix: str = ""):
    files = list_s3_files(bucket_name=bucket_name, prefix=prefix)
    return {"bucket_name": bucket_name, "prefix": prefix, "files": files, "count": len(files)}


@app.post("/decide_transaction")
def decide_transaction(request: DecideTransactionRequest):
    return save_transaction_decision(
        transaction_id=request.transaction_id,
        amount=request.amount,
        currency=request.currency,
        card_number=request.card_number.get_secret_value(),
        card_cvv=request.card_cvv.get_secret_value(),
        card_expiry=request.card_expiry,
        timestamp=request.timestamp,
    )


@app.get("/decisions/{decision_id}")
def get_decision_by_id(decision_id: str):
    return get_decision_or_404(decision_id)

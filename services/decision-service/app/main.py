from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI

from app.audit import write_audit_event
from app.models import CheckTransactionRequest, DecideTransactionRequest
from app.security import require_api_key
from app.services import get_decision_or_404, save_transaction_decision

load_dotenv()

app = FastAPI(title="WelosAI Decision Service")

# Every route on this router requires a valid X-API-Key header.
protected = APIRouter(dependencies=[Depends(require_api_key)])


@protected.post("/get_check_transaction")
def get_check_transaction(request: CheckTransactionRequest):
    result = get_decision_or_404(request.transaction_id)
    write_audit_event("transaction_checked", result)
    return result


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/readiness")
def readiness():
    return {"ready": True}


@protected.get("/is_entity_blocked/{entity_id}")
def is_entity_blocked_endpoint(entity_id: str):
    return {"entity_id": entity_id, "blocked": False}


@protected.post("/block_entity_if_needed")
def block_entity_if_needed_endpoint(entity_id: str, risk_score: int, threshold: int = 80):
    blocked_now = risk_score >= threshold
    return {
        "entity_id": entity_id,
        "risk_score": risk_score,
        "threshold": threshold,
        "blocked_now": blocked_now,
    }


@protected.get("/calculate_geo_risk")
def calculate_geo_risk_endpoint(ip_country: str, card_country: str):
    if ip_country.strip().upper() == card_country.strip().upper():
        return {"geo_risk_score": 0, "reason": "geo_match"}
    return {"geo_risk_score": 20, "reason": "geo_mismatch"}


@protected.post("/decide_transaction")
def decide_transaction(request: DecideTransactionRequest):
    return save_transaction_decision(
        transaction_id=request.transaction_id,
        amount=request.amount,
        currency=request.currency,
        card_number=request.card_number.get_secret_value(),
        card_cvv=request.card_cvv.get_secret_value(),
        card_expiry=request.card_expiry,
        timestamp=request.timestamp,
        customer_id=request.customer_id,
    )


@protected.get("/decisions/{decision_id}")
def get_decision_by_id(decision_id: str):
    return get_decision_or_404(decision_id)


app.include_router(protected)

from fastapi import FastAPI

from app.models import DecideRequest, DecideTransactionRequest
from app.services import get_decision_or_404, save_transaction_decision

app = FastAPI(title="WelosAI Decision Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/readiness")
def readiness():
    return {"ready": True}


@app.post("/decide_transaction")
def decide_transaction(request: DecideTransactionRequest):
    return save_transaction_decision(
        transaction_id=request.transaction_id,
        amount=request.amount,
        currency=request.currency,
        card_number=request.card_number.get_secret_value(),
        card_expiry=request.card_expiry,
        timestamp=request.timestamp,
    )


@app.get("/decisions/{decision_id}")
def get_decision_by_id(decision_id: str):
    return get_decision_or_404(decision_id)


@app.post("/decide")
def decide(request: DecideRequest):
    return {
        "status": "stub",
        "message": "Decision logic not implemented yet",
        "input": request.model_dump(),
    }

import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app import blocklist
from app.audit import write_audit_event
from app.models import BlockCardRequest, CheckTransactionRequest, DecideTransactionRequest
from app.security import require_api_key
from app.services import get_decision_or_404, save_transaction_decision, validate_card_number

load_dotenv()

# The API map stays closed unless ENABLE_DOCS=true: on for the public demo, off in production.
docs_enabled = os.getenv("ENABLE_DOCS", "false").lower() == "true"
app = FastAPI(
    title="WelosAI Decision Service",
    docs_url="/docs" if docs_enabled else None,
    redoc_url="/redoc" if docs_enabled else None,
    openapi_url="/openapi.json" if docs_enabled else None,
)

# Every route on this router requires a valid X-API-Key header.
protected = APIRouter(dependencies=[Depends(require_api_key)])


# FastAPI's default 422 response echoes the request body, card number and CVV included.
# Return only which field failed and why, never the value that was sent.
@app.exception_handler(RequestValidationError)
async def validation_error_without_input(request: Request, exc: RequestValidationError):
    errors = [{"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


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


@protected.post("/blocks", status_code=201)
def block_card_endpoint(request: BlockCardRequest):
    card_number = validate_card_number(request.card_number.get_secret_value())
    block = blocklist.block_card(card_number, reason=request.reason, blocked_by="security-manager", hours=request.hours)
    write_audit_event("card_blocked", block)
    return block


@protected.get("/blocks")
def list_blocks_endpoint():
    return {"blocks": blocklist.list_blocks()}


@protected.delete("/blocks/{block_id}")
def unblock_card_endpoint(block_id: str):
    block = blocklist.unblock(block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="Block not found")
    write_audit_event("card_unblocked", block)
    return block


app.include_router(protected)

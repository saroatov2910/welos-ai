from pydantic import BaseModel, Field, SecretStr


class DecideRequest(BaseModel):
    service_name: str
    environment: str
    cpu_usage: float
    memory_usage: float
    replicas: int
    error_rate: float
    latency_ms: float


class DecideTransactionRequest(BaseModel):
    transaction_id: str
    amount: float = Field(gt=0)
    currency: str
    card_number: SecretStr
    card_expiry: str
    card_cvv: SecretStr
    timestamp: str

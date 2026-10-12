from pydantic import BaseModel, Field, SecretStr


class CheckTransactionRequest(BaseModel):
    transaction_id: str


class DecideTransactionRequest(BaseModel):
    customer_id: str
    transaction_id: str
    amount: float = Field(gt=0)
    currency: str
    card_number: SecretStr
    card_expiry: str
    card_cvv: SecretStr
    timestamp: str


class BlockCardRequest(BaseModel):
    card_number: SecretStr
    reason: str = Field(min_length=1, max_length=200)
    hours: int | None = Field(default=None, gt=0, description="Leave empty to block until released")

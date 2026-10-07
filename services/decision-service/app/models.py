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

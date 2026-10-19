"""API key authentication.

Every protected request must send the key in the X-API-Key header.
The expected key comes from the API_KEY environment variable, never from code.
"""

import os
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(api_key: str | None = Security(api_key_header)) -> None:
    """Reject the request unless X-API-Key matches API_KEY. Fails closed if unset."""
    expected = os.getenv("API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="API key is not configured")
    # Compare bytes: compare_digest raises on non-ASCII strings, which would be a 500.
    if not api_key or not secrets.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

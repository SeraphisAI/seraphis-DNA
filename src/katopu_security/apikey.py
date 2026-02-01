from __future__ import annotations
from typing import Optional
from fastapi import HTTPException

def require_api_key(x_api_key: Optional[str], configured_key: str) -> None:
    if not configured_key:
        return
    if not x_api_key or x_api_key != configured_key:
        raise HTTPException(status_code=401, detail="Missing/invalid API key")

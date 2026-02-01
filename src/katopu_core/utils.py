from __future__ import annotations
import json, hashlib
from typing import Any

def sha256_hex(s: Any) -> str:
    if s is None:
        s = ""
    if not isinstance(s, str):
        s = str(s)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def short_hash(h: Any, n: int = 10) -> str:
    return h[:n] if isinstance(h, str) and h else "-"

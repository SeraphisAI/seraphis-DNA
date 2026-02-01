from __future__ import annotations
from typing import Any, Dict

def mask_sequence(seq: str, keep: int = 8) -> str:
    s = seq or ""
    if len(s) <= keep*2:
        return "*" * len(s)
    return s[:keep] + "…" + s[-keep:]

def mask_dict(obj: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in (obj or {}).items():
        if k in ("sequence","before","after"):
            out[k] = mask_sequence(str(v))
        elif isinstance(v, dict):
            out[k] = mask_dict(v)
        else:
            out[k] = v
    return out

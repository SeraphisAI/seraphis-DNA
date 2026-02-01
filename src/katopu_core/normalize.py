from __future__ import annotations
from typing import Any, Dict, Optional
from katopu_shared.ids import RESULT_SCHEMA_ID

def normalize_result(out: Optional[Dict[str, Any]], fallback_before: str) -> Optional[Dict[str, Any]]:
    if out is None or not isinstance(out, dict):
        return out

    fb = (fallback_before or "").strip().upper()

    before = out.get("before")
    if not isinstance(before, str) or before is None:
        out["before"] = fb

    after = out.get("after")
    if not isinstance(after, str) or after is None:
        out["after"] = out["before"]

    if "errors" not in out or not isinstance(out.get("errors"), list):
        out["errors"] = []
    if "flags" not in out or not isinstance(out.get("flags"), list):
        out["flags"] = []

    if "metrics" not in out or not isinstance(out.get("metrics"), dict):
        out["metrics"] = {}
    out["metrics"].setdefault("delta_nt", len(out["after"]) - len(out["before"]))

    # drift normalize
    for e in out["errors"]:
        if isinstance(e, dict):
            if e.get("code") == "E_SUB_MISMATCH":
                e["code"] = "FROM_MISMATCH"
            if e.get("code") == "E_OUT_OF_RANGE":
                e["code"] = "OUT_OF_RANGE"

    out.setdefault("schema", RESULT_SCHEMA_ID)
    return out

def is_expected_noop(out: Dict[str, Any]) -> bool:
    if not isinstance(out, dict):
        return False
    if out.get("before") != out.get("after"):
        return False
    codes = {(e or {}).get("code") for e in (out.get("errors") or []) if isinstance(e, dict)}
    return codes.issubset({"OUT_OF_RANGE", "FROM_MISMATCH"})

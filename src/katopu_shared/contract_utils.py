from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .ids import CONTRACT_VERSION, ENGINE_VERSION, SPEC_VERSION, EDITSPEC_SCHEMA_ID, RESULT_SCHEMA_ID

# -----------------------------
# Ω Error taxonomy (codes)
# -----------------------------
ERR_VALIDATION_ERROR = "VALIDATION_ERROR"

ERR_OUT_OF_RANGE = "OUT_OF_RANGE"
ERR_INVALID_BASE = "INVALID_BASE"
ERR_INVALID_POSITION = "INVALID_POSITION"
ERR_MISSING_PARAM = "MISSING_PARAM"
ERR_UNSUPPORTED_SYNONYM = "UNSUPPORTED_SYNONYM"

ERR_PARSE_ERROR = "PARSE_ERROR"
ERR_INTENT_UNPARSED = "INTENT_UNPARSED"

ERR_POLICY_BLOCK = "POLICY_BLOCK"
ERR_RATE_LIMITED = "RATE_LIMITED"
ERR_SERVER_ERROR = "SERVER_ERROR"
ERR_TIMEOUT = "TIMEOUT"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(obj: Any) -> str:
    if obj is None:
        b = b""
    elif isinstance(obj, (bytes, bytearray)):
        b = bytes(obj)
    elif isinstance(obj, str):
        b = obj.encode("utf-8")
    else:
        b = _stable_json(obj).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def make_error(code: str, message: Optional[str] = None, detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "code": code,
        "message": message or code,
        "detail": detail or {},
    }


def make_editspec(
    *,
    op: str,
    params: Dict[str, Any],
    intent_norm: str,
    strict_mode: bool,
    spec_version: str = SPEC_VERSION,
    errors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    intent_norm_sha256 = sha256_hex(intent_norm)
    return {
        "schema": EDITSPEC_SCHEMA_ID,
        "contract": CONTRACT_VERSION,
        "engine": ENGINE_VERSION,
        "created_at": now_iso(),
        "spec_version": spec_version,
        "op": op,
        "params": params,
        "normalization": {
            "intent_norm": intent_norm,
            "intent_norm_sha256": intent_norm_sha256,
        },
        "strict_mode": bool(strict_mode),
        "validation": {
            "errors": errors or [],
        },
    }


def validate_editspec(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    errors: List[Dict[str, Any]] = []

    if not isinstance(spec, dict):
        return [make_error(ERR_VALIDATION_ERROR, "Spec must be an object", {"got": type(spec).__name__})]

    if spec.get("schema") != EDITSPEC_SCHEMA_ID:
        errors.append(make_error(ERR_VALIDATION_ERROR, "Invalid schema", {"expected": EDITSPEC_SCHEMA_ID, "got": spec.get("schema")}))

    if "spec_version" not in spec:
        errors.append(make_error(ERR_VALIDATION_ERROR, "Missing spec_version"))

    op = spec.get("op")
    if op not in {"PREFIX_DELETE", "SUFFIX_DELETE", "POINT_MUTATION"}:
        errors.append(make_error(ERR_VALIDATION_ERROR, "Unsupported op", {"op": op}))

    params = spec.get("params")
    if not isinstance(params, dict):
        errors.append(make_error(ERR_VALIDATION_ERROR, "params must be an object"))
    else:
        if op in {"PREFIX_DELETE", "SUFFIX_DELETE"}:
            n = params.get("n")
            if not isinstance(n, int):
                errors.append(make_error(ERR_MISSING_PARAM, "Missing or invalid n", {"n": n}))
            elif n < 0:
                errors.append(make_error(ERR_OUT_OF_RANGE, "n must be >= 0", {"n": n}))
        if op == "POINT_MUTATION":
            pos = params.get("position")
            base = params.get("base")
            if not isinstance(pos, int):
                errors.append(make_error(ERR_MISSING_PARAM, "Missing or invalid position", {"position": pos}))
            elif pos < 1:
                errors.append(make_error(ERR_OUT_OF_RANGE, "position must be >= 1", {"position": pos}))
            if not (isinstance(base, str) and base.upper() in {"A", "C", "G", "T"}):
                errors.append(make_error(ERR_INVALID_BASE, "Invalid base", {"base": base}))

    return errors


def make_result(
    *,
    before: str,
    after: str,
    edit_map: str,
    effect_label: str,
    errors: Optional[List[Dict[str, Any]]] = None,
    flags: Optional[List[str]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    _meta: Optional[Dict[str, Any]] = None,
    _policy: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    errors_list = errors or []

    # Ω rule: if any errors exist -> ERROR
    final_effect = "ERROR" if errors_list else effect_label

    return {
        "schema": RESULT_SCHEMA_ID,
        "before": before,
        "after": after,
        "edit_map": edit_map,
        "effect_label": final_effect,
        "errors": errors_list,
        "flags": flags or [],
        "metrics": metrics or {},
        "_meta": _meta or {},
        "_policy": _policy or {},
    }


def make_error_result(
    *,
    before: str,
    code: str,
    message: Optional[str] = None,
    detail: Optional[Dict[str, Any]] = None,
    edit_map: str = "",
    request_id: Optional[str] = None,
    _meta: Optional[Dict[str, Any]] = None,
    _policy: Optional[Dict[str, Any]] = None,
    flags: Optional[List[str]] = None,
    **_ignored: Any,
) -> Dict[str, Any]:
    """Return a stable katopu.result.v1 error shape (Omega rule: SAME SHAPE ALWAYS).

    This helper is intentionally forgiving: it accepts extra kwargs for backwards
    compatibility (e.g. source/spec_version/policy_meta/http_status).
    """

    meta = dict(_meta or {})
    if request_id and "request_id" not in meta:
        meta["request_id"] = request_id

    # Back-compat: allow callers to pass common meta hints via kwargs.
    source = _ignored.get("source")
    spec_version = _ignored.get("spec_version")
    if source and "source" not in meta:
        meta["source"] = source
    if spec_version and "spec_version" not in meta:
        meta["spec_version"] = spec_version

    pol = dict(_policy or {})
    policy_meta = _ignored.get("policy_meta")
    if isinstance(policy_meta, dict):
        pol.update(policy_meta)

    return make_result(
        before=before,
        after=before,
        effect_label="ERROR",
        edit_map=edit_map,
        errors=[make_error(code=code, message=message or code, detail=detail or {})],
        flags=flags or [],
        metrics={},
        _meta=meta,
        _policy=pol,
    )

def fingerprint_sha(
    *,
    contract: str,
    spec_version: str,
    op: str,
    params: Dict[str, Any],
    before_sha256: str,
    policy_scope: str,
) -> str:
    payload = {
        "contract": contract,
        "spec_version": spec_version,
        "op": op,
        "params": params,
        "before_sha256": before_sha256,
        "policy_scope": policy_scope,
    }
    return sha256_hex(payload)

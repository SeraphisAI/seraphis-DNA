from __future__ import annotations

import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from katopu_core.nlp import normalize_intent
from katopu_policy.evaluator import PolicyEvaluator
from katopu_shared.contract_utils import (
    ERR_INTENT_UNPARSED,
    ERR_INVALID_BASE,
    ERR_INVALID_POSITION,
    ERR_MISSING_PARAM,
    ERR_OUT_OF_RANGE,
    ERR_PARSE_ERROR,
    ERR_POLICY_BLOCK,
    ERR_SERVER_ERROR,
    ERR_UNSUPPORTED_SYNONYM,
    ERR_VALIDATION_ERROR,
    make_editspec,
    make_error,
    make_error_result,
    make_result,
    sha256_hex,
    validate_editspec,
)
from katopu_shared.ids import CONTRACT_VERSION, ENGINE_VERSION, SPEC_VERSION

_ALLOWED_DNA = set("ACGT")
_IUPAC_DNA = set("ACGTNRYKMSWBDHV")

# Parsing is done on a lightly de-punctuated form to handle
# apostrophe variants like 10'deki, 10’deki, 10daki, etc.

def _parse_intent_surface(intent_norm: str) -> str:
    s = intent_norm.lower().strip()
    # normalize apostrophes and punctuation to spaces, keep digits/letters
    s = s.replace("’", "'")
    s = s.replace("`", "'")
    s = s.replace("‘", "'")
    s = s.replace("'", "")
    s = re.sub(r"[^0-9a-zçğıöşü\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _sanitize_sequence(sequence: str, strict_mode: bool) -> Tuple[str, List[Dict[str, Any]]]:
    seq = (sequence or "").strip().upper()
    if not seq:
        return seq, [make_error(ERR_MISSING_PARAM, "sequence is required")]

    allowed = _ALLOWED_DNA if strict_mode else _IUPAC_DNA
    bad = sorted({ch for ch in seq if ch not in allowed})
    if bad:
        return seq, [
            make_error(
                ERR_INVALID_BASE,
                "sequence contains invalid characters",
                {"invalid": "".join(bad), "strict_mode": strict_mode},
            )
        ]
    return seq, []


# -----------------------------
# Ω spec parsing
# -----------------------------

_RE_FIRST_DEL = re.compile(r"^ilk\s+(\d+)\s+baz\s+sil$")
_RE_LAST_DEL = re.compile(r"^son\s+(\d+)\s+baz\s+sil$")

# strict point mutation: "pozisyon P'deki bazı X yap"
_RE_POS_BASE_TO = re.compile(
    r"^pozisyon\s+(\d+)\s*(?:deki|daki)?\s*baz(?:i|ı)?\s+([acgt])\s+yap$"
)

# permissive variants: "P pozisyondaki baz G olsun" / "P. pozisyonda g yi a yap" / "pozisyon P g->a"
_RE_POS_ARROW = re.compile(
    r"^pozisyon\s+(\d+)\s*(?:deki|daki)?\s*baz(?:i|ı)?\s*([acgt])\s*(?:->|=>)\s*([acgt])$"
)
_RE_POS_FROM_TO = re.compile(
    r"^(\d+)\s*(?:\.|\s+)?\s*pozisyon(?:da|daki|deki)?\s*(?:baz)?\s*([acgt])\s*(?:yi|yı|i|ı)?\s*([acgt])\s*yap$"
)
_RE_POS_TO_ONLY = re.compile(
    r"^(\d+)\s*(?:\.|\s+)?\s*pozisyon(?:da|daki|deki)?\s*(?:baz)?\s*([acgt])\s*olsun$"
)

# Synonyms (strict may reject)
_RE_FIRST_DEL_SYNONYM = re.compile(r"^(?:başlangıçtan|bastan|basindan)\s+(\d+)\s+baz\s+(?:çıkar|cikar|sil)$")
_RE_LAST_DEL_SYNONYM = re.compile(r"^(?:sondan)\s+(\d+)\s+baz\s+(?:çıkar|cikar|sil)$")


def intent_to_editspec(intent_raw: str, strict_mode: bool = True) -> Dict[str, Any]:
    intent_norm = normalize_intent(intent_raw or "")
    surface = _parse_intent_surface(intent_norm)

    errors: List[Dict[str, Any]] = []
    op: str = "UNPARSED"
    params: Dict[str, Any] = {}

    m = _RE_FIRST_DEL.match(surface)
    if m:
        op = "PREFIX_DELETE"
        params = {"n": int(m.group(1))}
    else:
        m = _RE_LAST_DEL.match(surface)
        if m:
            op = "SUFFIX_DELETE"
            params = {"n": int(m.group(1))}

    if op == "UNPARSED":
        # Point mutation patterns
        m = _RE_POS_BASE_TO.match(surface)
        if m:
            op = "POINT_MUTATION"
            params = {"position": int(m.group(1)), "base": m.group(2).upper()}
        else:
            m = _RE_POS_ARROW.match(surface)
            if m:
                op = "POINT_MUTATION"
                params = {"position": int(m.group(1)), "from": m.group(2).upper(), "base": m.group(3).upper()}
            else:
                m = _RE_POS_FROM_TO.match(surface)
                if m:
                    op = "POINT_MUTATION"
                    params = {"position": int(m.group(1)), "from": m.group(2).upper(), "base": m.group(3).upper()}
                else:
                    m = _RE_POS_TO_ONLY.match(surface)
                    if m:
                        op = "POINT_MUTATION"
                        params = {"position": int(m.group(1)), "base": m.group(2).upper()}

    # Synonyms: either support or reject with UNSUPPORTED_SYNONYM
    if op == "UNPARSED":
        m = _RE_FIRST_DEL_SYNONYM.match(surface)
        if m:
            if strict_mode:
                errors.append(make_error(ERR_UNSUPPORTED_SYNONYM, "unsupported synonym in strict mode"))
            else:
                op = "PREFIX_DELETE"
                params = {"n": int(m.group(1))}
        else:
            m = _RE_LAST_DEL_SYNONYM.match(surface)
            if m:
                if strict_mode:
                    errors.append(make_error(ERR_UNSUPPORTED_SYNONYM, "unsupported synonym in strict mode"))
                else:
                    op = "SUFFIX_DELETE"
                    params = {"n": int(m.group(1))}

    if op == "UNPARSED" and not errors:
        errors.append(make_error(ERR_PARSE_ERROR, "could not parse intent", {"code": ERR_INTENT_UNPARSED}))

    # Parameter-level validation (spec-time)
    if op in {"PREFIX_DELETE", "SUFFIX_DELETE"} and "n" in params:
        n = params.get("n")
        if not isinstance(n, int) or n < 0:
            errors.append(make_error(ERR_OUT_OF_RANGE, "n must be a non-negative integer", {"n": n}))

    if op == "POINT_MUTATION" and params:
        pos = params.get("position")
        base = params.get("base")
        if not isinstance(pos, int) or pos < 1:
            errors.append(make_error(ERR_INVALID_POSITION, "position must be 1-indexed positive integer", {"position": pos}))
        if base and str(base).upper() not in _ALLOWED_DNA:
            errors.append(make_error(ERR_INVALID_BASE, "base must be one of A/C/G/T", {"base": base}))
        if "from" in params and str(params["from"]).upper() not in _ALLOWED_DNA:
            errors.append(make_error(ERR_INVALID_BASE, "from-base must be one of A/C/G/T", {"from": params["from"]}))

    return make_editspec(
        spec_version=SPEC_VERSION,
        op=op,
        params=params,
        intent_norm=intent_norm,
        strict_mode=bool(strict_mode),
        errors=errors,
    )


def apply_editspec(
    sequence: str,
    spec: Dict[str, Any],
    *,
    strict_mode: Optional[bool] = None,
    policy: Optional[PolicyEvaluator] = None,
    request_id: Optional[str] = None,
    source: str = "api",
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    editspec = spec or {}
    strict_mode = bool(editspec.get("strict_mode", True)) if strict_mode is None else bool(strict_mode)

    seq, seq_errs = _sanitize_sequence(sequence, strict_mode)
    if seq_errs:
        return make_error_result(
            before=seq,
            code=ERR_VALIDATION_ERROR,
            message="invalid sequence",
            detail={"errors": seq_errs},
            request_id=request_id,
            source=source,
            spec_version=str(editspec.get("spec_version", SPEC_VERSION)),
        )

    spec_errs = validate_editspec(editspec)
    all_spec_errors = list(editspec.get("errors") or []) + spec_errs
    if all_spec_errors:
        return make_error_result(
            before=seq,
            code=ERR_PARSE_ERROR,
            message="invalid editspec",
            detail={"errors": all_spec_errors},
            request_id=request_id,
            source=source,
            spec_version=str(editspec.get("spec_version", SPEC_VERSION)),
        )

    op = editspec.get("op")
    params: Dict[str, Any] = editspec.get("params") or {}

    # Policy
    policy_obj = policy or PolicyEvaluator.from_default_files()
    intent_norm = (editspec.get("normalization") or {}).get("intent_norm", "")
    decision = policy_obj.evaluate(
        op=str(op),
        params=params,
        strict_mode=bool(strict_mode),
        intent=intent_norm,
        sequence=seq,
    )
    if not decision.allowed:
        return make_error_result(
            before=seq,
            code=ERR_POLICY_BLOCK,
            message="policy blocked operation",
            detail={"reason": decision.reason, "policy_id": decision.policy_id},
            request_id=request_id,
            source=source,
            spec_version=str(editspec.get("spec_version", SPEC_VERSION)),
            policy_meta={"allowed": False, "reason": decision.reason, "audit_id": decision.audit_id},
        )

    # Apply
    errors: List[Dict[str, Any]] = []
    flags: List[str] = []

    before = seq
    after = seq
    edit_map = ""
    effect = "NOOP"

    if op == "PREFIX_DELETE":
        n = int(params.get("n", 0))
        if n > len(before):
            errors.append(make_error(ERR_OUT_OF_RANGE, "n exceeds sequence length", {"n": n, "len": len(before)}))
        else:
            after = before[n:]
            edit_map = f"pdel:first {n}"
            effect = "DELETION" if n > 0 else "NOOP"

    elif op == "SUFFIX_DELETE":
        n = int(params.get("n", 0))
        if n > len(before):
            errors.append(make_error(ERR_OUT_OF_RANGE, "n exceeds sequence length", {"n": n, "len": len(before)}))
        else:
            after = before[: len(before) - n] if n else before
            edit_map = f"sdel:last {n}"
            effect = "DELETION" if n > 0 else "NOOP"

    elif op == "POINT_MUTATION":
        pos = int(params.get("position", 0))
        base = str(params.get("base", "")).upper()
        if pos < 1 or pos > len(before):
            errors.append(make_error(ERR_INVALID_POSITION, "position out of range", {"position": pos, "len": len(before)}))
        elif base not in _ALLOWED_DNA:
            errors.append(make_error(ERR_INVALID_BASE, "invalid target base", {"base": base}))
        else:
            idx = pos - 1
            cur = before[idx]
            exp = str(params.get("from", "")).upper() if params.get("from") else None
            if exp and exp in _ALLOWED_DNA and cur != exp:
                errors.append(
                    make_error(
                        ERR_VALIDATION_ERROR,
                        "expected base mismatch",
                        {"position": pos, "expected": exp, "actual": cur},
                    )
                )
            else:
                if cur == base:
                    after = before
                    effect = "NOOP"
                else:
                    after = before[:idx] + base + before[idx + 1 :]
                    effect = "MUTATION"
                edit_map = f"pmut:pos {pos} {cur}->{base}"

    else:
        errors.append(make_error(ERR_PARSE_ERROR, "unsupported op", {"op": op, "code": ERR_INTENT_UNPARSED}))

    runtime_ms = int((time.perf_counter() - t0) * 1000)

    if errors:
        effect = "ERROR"
        after = before

    metrics = {
        "delta_nt": len(after) - len(before),
        "delta_ops": 1 if effect in {"DELETION", "MUTATION"} else 0,
        "runtime_ms": runtime_ms,
        "runtime_breakdown_ms": {"total": runtime_ms},
    }

    return make_result(
        before=before,
        after=after,
        edit_map=edit_map or "noop",
        effect_label=effect,
        errors=errors,
        flags=flags,
        metrics=metrics,
        _meta={
            "contract": CONTRACT_VERSION,
            "engine": ENGINE_VERSION,
            "source": source,
            "spec_version": editspec.get("spec_version", SPEC_VERSION),
            "request_id": request_id,
        },
        _policy={
            "allowed": True,
            "reason": decision.reason,
            "audit_id": decision.audit_id,
        },
    )


def run_intent(
    sequence: str,
    intent: str,
    *,
    strict_mode: bool = True,
    policy: Optional[PolicyEvaluator] = None,
    request_id: Optional[str] = None,
    source: str = "api",
) -> Dict[str, Any]:
    spec = intent_to_editspec(intent, strict_mode=strict_mode)
    return apply_editspec(
        sequence=sequence,
        spec=spec,
        strict_mode=strict_mode,
        policy=policy,
        request_id=request_id,
        source=source,
    )


def jitter_backoff_sleep(attempt: int, base_ms: int = 150) -> float:
    # Exponential backoff with jitter; return seconds to sleep.
    exp = min(attempt, 6)
    ms = base_ms * (2**exp)
    jitter = random.uniform(0.5, 1.5)
    return (ms * jitter) / 1000.0

# Backwards-compatible aliases
nl_to_editspec = intent_to_editspec


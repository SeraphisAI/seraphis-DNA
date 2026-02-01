from __future__ import annotations
import re
from typing import Any, Dict, List, Literal, Optional

from katopu_shared.ids import EDITOP_SCHEMA_ID, RESULT_SCHEMA_ID
from .normalize import normalize_result
from .nlp import edit_map_preview

Mode = Literal["strict", "lenient"]

DNA_STRICT_RE = re.compile(r"^[ACGT]+$")
DNA_IUPAC_RE = re.compile(r"^[ACGTRYSWKMBDHVN]+$")
BASE_RE = re.compile(r"^[ACGT]$")
SEQ_RE = re.compile(r"^[ACGT]+$")

def local_apply(seq: str, mode: Mode, edit_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(edit_obj, dict):
        return None
    op = edit_obj.get("op")
    if not isinstance(op, dict) or not op.get("type"):
        return None

    before = (seq or "").strip().upper()
    errors: List[Dict[str, Any]] = []
    flags: List[Dict[str, Any]] = []

    if not before:
        errors.append({"code": "SEQ_EMPTY", "detail": {}})
        return normalize_result({
            "schema": RESULT_SCHEMA_ID,
            "before": before,
            "after": before,
            "edit_map": edit_map_preview(edit_obj),
            "effect_label": "ERROR",
            "metrics": {"delta_nt": 0},
            "errors": errors,
            "flags": flags,
        }, fallback_before=before)

    if mode == "strict":
        if DNA_STRICT_RE.fullmatch(before) is None:
            errors.append({"code": "SEQ_INVALID_STRICT", "detail": {}})
            return normalize_result({
                "schema": RESULT_SCHEMA_ID,
                "before": before,
                "after": before,
                "edit_map": edit_map_preview(edit_obj),
                "effect_label": "ERROR",
                "metrics": {"delta_nt": 0},
                "errors": errors,
                "flags": flags,
            }, fallback_before=before)
    else:
        if DNA_IUPAC_RE.fullmatch(before) is None:
            errors.append({"code": "SEQ_INVALID_LENIENT", "detail": {}})
            return normalize_result({
                "schema": RESULT_SCHEMA_ID,
                "before": before,
                "after": before,
                "edit_map": edit_map_preview(edit_obj),
                "effect_label": "ERROR",
                "metrics": {"delta_nt": 0},
                "errors": errors,
                "flags": flags,
            }, fallback_before=before)

    t = op["type"]
    n = len(before)

    def out_ok(after: str, label: str, delta: int):
        return normalize_result({
            "schema": RESULT_SCHEMA_ID,
            "before": before,
            "after": after,
            "edit_map": edit_map_preview(edit_obj),
            "effect_label": label,
            "metrics": {"delta_nt": delta},
            "errors": [],
            "flags": [],
        }, fallback_before=before)

    def out_err(code: str, detail: Dict[str, Any], label: str = "ERROR"):
        return normalize_result({
            "schema": RESULT_SCHEMA_ID,
            "before": before,
            "after": before,
            "edit_map": edit_map_preview(edit_obj),
            "effect_label": label,
            "metrics": {"delta_nt": 0},
            "errors": [{"code": code, "detail": detail}],
            "flags": flags,
        }, fallback_before=before)

    if t == "prefix_deletion":
        k = int(op.get("n", 0))
        if not (1 <= k <= n):
            return out_err("OUT_OF_RANGE", {"len": n, "n": k})
        after = before[k:]
        return out_ok(after, "DELETION", len(after) - len(before))

    if t == "suffix_deletion":
        k = int(op.get("n", 0))
        if not (1 <= k <= n):
            return out_err("OUT_OF_RANGE", {"len": n, "n": k})
        after = before[: n - k]
        return out_ok(after, "DELETION", len(after) - len(before))

    if t == "deletion":
        i, j = int(op.get("i", 0)), int(op.get("j", 0))
        if not (1 <= i <= j <= n):
            return out_err("OUT_OF_RANGE", {"len": n, "i": i, "j": j})
        after = before[: i - 1] + before[j:]
        return out_ok(after, "DELETION", len(after) - len(before))

    if t == "insertion":
        i = int(op.get("i", 0))
        ins = (op.get("seq") or "").upper()
        if not (1 <= i <= n):
            return out_err("OUT_OF_RANGE", {"len": n, "i": i})
        if SEQ_RE.fullmatch(ins) is None:
            return out_err("INVALID_INSERT_SEQ", {"seq": ins})
        after = before[:i] + ins + before[i:]
        return out_ok(after, "INSERTION", len(after) - len(before))

    if t == "substitution":
        i = int(op.get("i", 0))
        frm = (op.get("from") or "").upper()
        to = (op.get("to") or "").upper()
        if not (1 <= i <= n):
            return out_err("OUT_OF_RANGE", {"len": n, "i": i})
        if BASE_RE.fullmatch(frm) is None or BASE_RE.fullmatch(to) is None:
            return out_err("INVALID_BASE", {"from": frm, "to": to})

        cur = before[i - 1]
        if cur != frm:
            if mode == "strict":
                return out_err("FROM_MISMATCH", {"pos": i, "expected": frm, "actual": cur})
            flags.append({"code": "FROM_MISMATCH_LENIENT", "detail": {"pos": i, "expected": frm, "actual": cur}})
            return normalize_result({
                "schema": RESULT_SCHEMA_ID,
                "before": before,
                "after": before,
                "edit_map": edit_map_preview(edit_obj),
                "effect_label": "NOOP",
                "metrics": {"delta_nt": 0},
                "errors": [],
                "flags": flags,
            }, fallback_before=before)

        after = before[: i - 1] + to + before[i:]
        return out_ok(after, "SUBSTITUTION", 0)

    if t == "conditional_substitution":
        i = int(op.get("i", 0))
        if_base = (op.get("if_base") or "").upper()
        to = (op.get("to") or "").upper()
        if not (1 <= i <= n):
            return out_err("OUT_OF_RANGE", {"len": n, "i": i})
        if BASE_RE.fullmatch(if_base) is None or BASE_RE.fullmatch(to) is None:
            return out_err("INVALID_BASE", {"if_base": if_base, "to": to})

        cur = before[i - 1]
        if cur == if_base:
            after = before[: i - 1] + to + before[i:]
            return out_ok(after, "COND_SUB_APPLIED", 0)

        if mode == "strict":
            return out_err("FROM_MISMATCH", {"pos": i, "expected": if_base, "actual": cur})
        flags.append({"code": "COND_NOT_MET", "detail": {"pos": i, "expected": if_base, "actual": cur}})
        return normalize_result({
            "schema": RESULT_SCHEMA_ID,
            "before": before,
            "after": before,
            "edit_map": edit_map_preview(edit_obj),
            "effect_label": "NOOP",
            "metrics": {"delta_nt": 0},
            "errors": [],
            "flags": flags,
        }, fallback_before=before)

    return None

from __future__ import annotations
from typing import Any, Dict
from katopu_shared.ids import (
    UNIFIED_SCHEMA_ID, MANIFEST_SCHEMA_ID, EDITOP_SCHEMA_ID, RESULT_SCHEMA_ID,
    RUNRECEIPT_SCHEMA_ID, BATCHRUN_SCHEMA_ID, CONTRACT_VERSION, ENGINE_VERSION
)
from .timeutil import now_utc_iso

def unified_schema_object() -> Dict[str, Any]:
    return {
        "schema": UNIFIED_SCHEMA_ID,
        "contract": CONTRACT_VERSION,
        "engine": ENGINE_VERSION,
        "created_at": now_utc_iso(),
        "definitions": {
            "manifest": {
                "schema": MANIFEST_SCHEMA_ID,
                "fields": ["schema", "contract", "engine", "created_at", "text"],
            },
            "editop": {
                "schema": EDITOP_SCHEMA_ID,
                "op_types": {
                    "deletion": {"type": "deletion", "i": "1-based int", "j": "1-based int (inclusive)"},
                    "prefix_deletion": {"type": "prefix_deletion", "n": "int (#bases from start)"},
                    "suffix_deletion": {"type": "suffix_deletion", "n": "int (#bases from end)"},
                    "insertion": {"type": "insertion", "i": "1-based int (insert AFTER i)", "seq": "ACGT+"},
                    "substitution": {"type": "substitution", "i": "1-based int", "from": "A/C/G/T", "to": "A/C/G/T"},
                    "conditional_substitution": {
                        "type": "conditional_substitution",
                        "i": "1-based int",
                        "if_base": "A/C/G/T",
                        "to": "A/C/G/T",
                        "else": "noop",
                    },
                },
            },
            "result": {
                "schema": RESULT_SCHEMA_ID,
                "fields": ["schema","before","after","effect_label","edit_map","errors[]","flags[]","metrics{delta_nt}","_meta","_policy?"],
                "notes": [
                    "strict mismatch => errors: FROM_MISMATCH + no-op",
                    "lenient mismatch => flags: FROM_MISMATCH_LENIENT / COND_NOT_MET + no-op",
                ],
            },
            "runreceipt": {
                "schema": RUNRECEIPT_SCHEMA_ID,
                "fields": ["schema", "created_at", "trace{trace_id}", "policy", "source", "intent", "intent_norm", "result"],
            },
            "batchrun": {
                "schema": BATCHRUN_SCHEMA_ID,
                "fields": ["schema", "created_at", "manifest", "sequence", "mode", "items[]"],
            },
        },
    }

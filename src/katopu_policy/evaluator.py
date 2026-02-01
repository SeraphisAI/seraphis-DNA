from __future__ import annotations

from dataclasses import dataclass
import uuid

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

OMEGA_OP_MAP = {
    "PREFIX_DELETE": "prefix_deletion",
    "SUFFIX_DELETE": "suffix_deletion",
    "POINT_MUTATION": "substitution",
}
DEFAULT_RULES = {
    "max_sequence_len": 200000,
    "max_insert_len": 100000,
    "allow_ops": [
        "deletion",
        "prefix_deletion",
        "suffix_deletion",
        "PREFIX_DELETE",
        "SUFFIX_DELETE",
        "POINT_MUTATION",
        "insertion",
        "substitution",
        "conditional_substitution",
    ],
    "deny_intent_regex": [
        r"(?i)\b(toxin|weapon|bioweapon|pathogen|gain[- ]of[- ]function)\b",
        r"(?i)\b(anthrax|smallpox|variola|ricin|botulinum)\b",
    ],
    "redact_sequences_in_logs": True,
}


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = ""
    policy_id: str = "policy.default"
    audit_id: str = ""


class PolicyEvaluator:
    @classmethod
    def from_default_files(cls) -> 'PolicyEvaluator':
        """Load policy from KATOPU_POLICY_PATH (or default policy/policy.json)."""
        path = os.getenv('KATOPU_POLICY_PATH', 'policy/policy.json')
        return cls(path=path)

    def __init__(self, path: str):
        self.path = path
        self._mtime: Optional[float] = None
        self._cached: Dict[str, Any] = DEFAULT_RULES.copy()
        self._deny_intent_re: List[re.Pattern[str]] = []
        self.reload()

    def _compile(self) -> None:
        self._deny_intent_re = []
        patterns = self._cached.get("deny_intent_regex", []) or []
        for p in patterns:
            try:
                self._deny_intent_re.append(re.compile(p))
            except re.error:
                # Invalid regex should not crash the service; it just gets ignored.
                continue

    def reload(self) -> bool:
        """Reload rules from disk if the file changed.

        Returns True if a reload happened.
        """
        try:
            mtime = os.path.getmtime(self.path)
        except OSError:
            mtime = None

        if self._mtime == mtime and self._mtime is not None:
            return False

        rules = DEFAULT_RULES.copy()
        if mtime is not None:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    doc = json.load(f)
                rules.update(doc.get("rules", {}))
            except Exception:
                # If policy file is malformed, keep defaults to stay safe.
                pass

        self._cached = rules
        self._mtime = mtime
        self._compile()
        return True

    def rules(self) -> Dict[str, Any]:
        self.reload()
        return dict(self._cached)

    def check_sequence_len(self, seq: str) -> Tuple[bool, str]:
        self.reload()
        max_len = int(self._cached.get("max_sequence_len", 200000))
        if len(seq) > max_len:
            return False, f"Sequence too long ({len(seq)}>{max_len})"
        return True, ""

    def check_intent(self, intent: str) -> Tuple[bool, str, str]:
        self.reload()
        for rx in self._deny_intent_re:
            if rx.search(intent):
                return False, f"Intent blocked by policy regex {rx.pattern}", rx.pattern
        return True, "", ""

    def allow_op(self, op: Any) -> Tuple[bool, str]:
        self.reload()
        allowed = set(self._cached.get("allow_ops", []))
        if isinstance(op, str):
            t = OMEGA_OP_MAP.get(op, op)
        elif isinstance(op, dict):
            t = OMEGA_OP_MAP.get(op.get("type", ""), op.get("type", ""))
        else:
            t = ""
        if t not in allowed:
            return False, f"Operation type '{t}' not allowed"

        if t == "insertion" and isinstance(op, dict):
            ins = op.get("insert", "") or ""
            max_ins = int(self._cached.get("max_insert_len", 100000))
            if len(ins) > max_ins:
                return False, f"Insert too long ({len(ins)}>{max_ins})"

        return True, ""

    def redact_sequences_in_logs(self) -> bool:
        self.reload()
        return bool(self._cached.get("redact_sequences_in_logs", True))

    def evaluate(
        self,
        *,
        op: Any,
        params: Optional[Dict[str, Any]] = None,
        strict_mode: bool = True,
        intent: str = "",
        sequence: str = "",
        **_ignored: Any,
    ) -> PolicyDecision:
        """Unified policy decision for Omega engine / API.

        Returns PolicyDecision with stable fields (allowed, reason, policy_id, audit_id).
        """
        audit_id = uuid.uuid4().hex

        # Sequence length gate
        if sequence:
            ok, reason = self.check_sequence_len(sequence)
            if not ok:
                return PolicyDecision(False, reason, 'policy.max_sequence_len', audit_id)

        # Intent regex gate
        if intent:
            ok, reason, _pat = self.check_intent(intent)
            if not ok:
                return PolicyDecision(False, reason, 'policy.deny_intent_regex', audit_id)

        # Op allowlist gate
        ok, reason = self.allow_op(op)
        if not ok:
            return PolicyDecision(False, reason, 'policy.allow_ops', audit_id)

        return PolicyDecision(True, "", 'policy.default', audit_id)

    # Backward-compatible alias
    def reload_if_changed(self) -> bool:
        return self.reload()

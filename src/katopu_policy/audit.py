from __future__ import annotations
import json, os
from datetime import datetime, timezone
from typing import Any, Dict

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class PolicyAudit:
    def __init__(self, path: str):
        self.path = path

    def write(self, event: Dict[str, Any]) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            obj = dict(event)
            obj.setdefault("ts", now_utc_iso())
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        except Exception:
            return

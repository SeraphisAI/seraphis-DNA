from __future__ import annotations
import json, os, random
from datetime import datetime, timezone
from typing import Any, Dict

def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class TelemetryEmitter:
    def __init__(self, enabled: bool, sample_rate: float, path: str):
        self.enabled = bool(enabled)
        self.sample_rate = float(sample_rate)
        self.path = path

    def emit(self, event: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        if self.sample_rate < 1.0 and random.random() > self.sample_rate:
            return
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            obj = dict(event)
            obj.setdefault("ts", now_utc_iso())
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        except Exception:
            return

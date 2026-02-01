from __future__ import annotations

import os
from pydantic import BaseModel


class Settings(BaseModel):
    # Identity / contract
    contract: str = os.getenv("KATOPU_CONTRACT", "katopu.ucp.ultra.final.v1")
    engine: str = os.getenv("KATOPU_ENGINE", "ucp_ultra_core_v1")

    # Policy
    policy_path: str = os.getenv("KATOPU_POLICY_PATH", "/policies/default.policy.json")
    # Optional override (written by UI policy panel). If the file exists, API will prefer it.
    policy_override_path: str = os.getenv("KATOPU_POLICY_OVERRIDE_PATH", "/data/policy_override.json")
    policy_audit_path: str = os.getenv("KATOPU_POLICY_AUDIT_PATH", "/data/policy_audit.jsonl")
    # If false, API will still *read* override file if it exists, but will not expose any write endpoints.
    policy_mutable: bool = os.getenv("KATOPU_POLICY_MUTABLE", "false").lower() == "true"

    # Telemetry
    telemetry_enabled: bool = os.getenv("KATOPU_TELEMETRY_ENABLED", "false").lower() == "true"
    telemetry_sample_rate: float = float(os.getenv("KATOPU_TELEMETRY_SAMPLE_RATE", "0.1"))
    telemetry_path: str = os.getenv("KATOPU_TELEMETRY_PATH", "/data/telemetry.jsonl")

    # Auth
    api_key: str = os.getenv("KATOPU_API_KEY", "")

    # Simple rate limit
    rate_rps: float = float(os.getenv("KATOPU_RATE_RPS", "5"))
    rate_burst: int = int(os.getenv("KATOPU_RATE_BURST", "10"))


settings = Settings()

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class TokenBucket:
    capacity: float
    fill_rate: float  # tokens per second
    tokens: float
    last_ts: float


class TokenBucketLimiter:
    """In-memory token bucket rate limiter.

KATOPU Ω requirement: rate-limit should *not* change response JSON shape.
Therefore, this limiter does not raise HTTP exceptions. Instead it returns
whether the call is allowed and, if not, an estimated retry-after.

Notes:
 - This is per-process memory. For multi-replica production setups, replace
   with Redis/Envoy/Nginx rate limiting.
"""

    def __init__(self, rps: float = 5.0, burst: int = 10):
        self.rps = float(rps)
        self.burst = int(burst)
        self._buckets: Dict[str, TokenBucket] = {}

    def _get_bucket(self, key: str) -> TokenBucket:
        now = time.monotonic()
        b = self._buckets.get(key)
        if b is None:
            b = TokenBucket(capacity=float(self.burst), fill_rate=self.rps, tokens=float(self.burst), last_ts=now)
            self._buckets[key] = b
        return b

    def check(self, key: str, cost: float = 1.0) -> Tuple[bool, Optional[float]]:
        """Return (allowed, retry_after_seconds_if_blocked)."""

        b = self._get_bucket(key)
        now = time.monotonic()
        elapsed = max(0.0, now - b.last_ts)
        # refill
        b.tokens = min(b.capacity, b.tokens + elapsed * b.fill_rate)
        b.last_ts = now

        if b.tokens >= cost:
            b.tokens -= cost
            return True, None

        # Estimate time until one token becomes available.
        needed = cost - b.tokens
        retry_after = needed / b.fill_rate if b.fill_rate > 0 else 1.0
        # Clamp to reasonable range
        retry_after = max(0.05, min(60.0, retry_after))
        return False, retry_after


def build_default_limiter() -> TokenBucketLimiter:
    rps = float(os.getenv("KATOPU_RATE_LIMIT_RPS", "5"))
    burst = int(os.getenv("KATOPU_RATE_LIMIT_BURST", "10"))
    return TokenBucketLimiter(rps=rps, burst=burst)

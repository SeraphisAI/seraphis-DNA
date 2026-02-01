from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import JSONResponse

from katopu_core.omega_engine import apply_editspec, nl_to_editspec, run_intent
from katopu_policy.evaluator import PolicyEvaluator
from katopu_shared.contract_utils import (
    ERR_RATE_LIMITED,
    ERR_SERVER_ERROR,
    make_editspec,
    make_error,
    make_error_result,
)
from katopu_shared.ids import CONTRACT_VERSION, ENGINE_VERSION


# -----------------------------
# Rate limiting (token bucket)
# -----------------------------
@dataclass
class RateLimitDecision:
    allowed: bool
    retry_after_s: float


class TokenBucket:
    def __init__(self, rate_rps: float, burst: int):
        self.rate_rps = max(0.0, float(rate_rps))
        self.burst = max(1, int(burst))
        self._tokens: Dict[str, float] = {}
        self._last: Dict[str, float] = {}

    def consume(self, key: str, now: Optional[float] = None) -> RateLimitDecision:
        if self.rate_rps <= 0:
            return RateLimitDecision(True, 0.0)
        now = time.time() if now is None else now
        last = self._last.get(key, now)
        tokens = self._tokens.get(key, float(self.burst))

        # refill
        tokens = min(float(self.burst), tokens + (now - last) * self.rate_rps)
        self._last[key] = now

        if tokens >= 1.0:
            tokens -= 1.0
            self._tokens[key] = tokens
            return RateLimitDecision(True, 0.0)

        # retry after enough time for 1 token
        deficit = 1.0 - tokens
        retry_after_s = max(0.0, deficit / self.rate_rps)
        self._tokens[key] = tokens
        return RateLimitDecision(False, retry_after_s)


def _client_key(req: Request) -> str:
    # Prefer X-Forwarded-For if present
    xff = req.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    if req.client and req.client.host:
        return req.client.host
    return "unknown"


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}


RATE_RPS = float(os.getenv("KATOPU_RATE_RPS", "3"))
RATE_BURST = int(os.getenv("KATOPU_RATE_BURST", "10"))
LIMITER = TokenBucket(rate_rps=RATE_RPS, burst=RATE_BURST)

REQUIRE_API_KEY = _bool_env("KATOPU_REQUIRE_API_KEY", False)
API_KEY = os.getenv("KATOPU_API_KEY", "")

POLICY = PolicyEvaluator(path=os.getenv("KATOPU_POLICY_PATH", "policy/policy.json"))

app = FastAPI(title="Katopu GenLab Ω API", version="1.0.0")
app.state.limiter = LIMITER
app.state.policy = POLICY


@app.middleware("http")
async def request_id_and_rate_limit(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())

    # auth (simple shared secret)
    if REQUIRE_API_KEY:
        provided = request.headers.get("x-api-key", "")
        if not API_KEY or provided != API_KEY:
            body = make_error_result(
                before="",
                code="POLICY_BLOCK",
                message="Missing/invalid API key",
                detail={"required": True},
                request_id=request.state.request_id,
            )
            return JSONResponse(status_code=403, content=body)

    # rate limit
    decision = LIMITER.consume(_client_key(request))
    if not decision.allowed:
        retry_after = max(0.001, decision.retry_after_s)
        # For /nl/spec we return an EditSpec-shaped error; for other endpoints result.v1.
        if request.url.path.rstrip("/") == "/nl/spec":
            spec = make_editspec(
                op="UNPARSED",
                params={},
                intent_norm="",
                strict_mode=True,
                errors=[
                    make_error(
                        code=ERR_RATE_LIMITED,
                        message="Rate limited",
                        detail={"retry_after_ms": int(retry_after * 1000)},
                    )
                ],
            )
            spec["_meta"] = {
                "contract": CONTRACT_VERSION,
                "engine": ENGINE_VERSION,
                "source": "api",
                "request_id": request.state.request_id,
            }
            resp = JSONResponse(status_code=429, content=spec)
        else:
            body = make_error_result(
                before="",
                code=ERR_RATE_LIMITED,
                message="Rate limited",
                detail={"retry_after_ms": int(retry_after * 1000)},
                request_id=request.state.request_id,
            )
            resp = JSONResponse(status_code=429, content=body)
        resp.headers["Retry-After"] = f"{retry_after:.3f}"
        resp.headers["X-Request-ID"] = request.state.request_id
        return resp

    response = await call_next(request)
    response.headers.setdefault("X-Request-ID", request.state.request_id)
    return response



@app.get("/health")
def health():
    return {"ok": True}


@app.get("/policy")
def policy_info():
    # Returns effective policy rules (defaults + optional file override).
    rules = POLICY.rules()
    path = POLICY.path
    override_present = False
    mtime = None
    try:
        override_present = os.path.exists(path)
        if override_present:
            mtime = os.path.getmtime(path)
    except Exception:
        # keep None
        pass

    return {
        "schema": "katopu.policy.info.v1",
        "path": path,
        "override": override_present,
        "override_present": override_present,
        "mtime": mtime,
        "rules": rules,
        "_meta": {
            "contract": CONTRACT_VERSION,
            "engine": ENGINE_VERSION,
        },
    }


@app.post("/nl/spec")
def nl_spec(payload: Dict[str, Any] = Body(...), request: Request = None):
    intent = str(payload.get("intent", ""))
    mode = str(payload.get("mode", "strict")).lower().strip() or "strict"
    strict = mode != "lenient"

    spec = nl_to_editspec(intent, strict_mode=strict)
    spec.setdefault("_meta", {})
    spec["_meta"].update(
        {
            "contract": CONTRACT_VERSION,
            "engine": ENGINE_VERSION,
            "source": "api",
            "request_id": getattr(getattr(request, "state", None), "request_id", None),
        }
    )
    return spec


@app.post("/edit/apply")
def edit_apply(payload: Dict[str, Any] = Body(...), request: Request = None):
    mode = str(payload.get("mode", "strict")).lower().strip() or "strict"
    strict = mode != "lenient"

    sequence = str(payload.get("sequence", ""))
    spec = payload.get("spec") or payload.get("edit_spec") or payload.get("editspec")

    req_id = getattr(getattr(request, "state", None), "request_id", None)
    result = apply_editspec(sequence=sequence, spec=spec, strict_mode=strict, policy=POLICY, request_id=req_id)
    return result


@app.post("/run")
def run(
    sequence: str = Query(..., description="DNA/RNA sequence"),
    payload: Dict[str, Any] = Body(...),
    request: Request = None,
):
    mode = str(payload.get("mode", "strict")).lower().strip() or "strict"
    strict = mode != "lenient"
    intent = str(payload.get("intent", ""))

    req_id = getattr(getattr(request, "state", None), "request_id", None)
    result = run_intent(sequence=sequence, intent=intent, strict_mode=strict, policy=POLICY, request_id=req_id)
    return result


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Don't leak internal details
    req_id = getattr(getattr(request, "state", None), "request_id", None)
    body = make_error_result(
        before="",
        code=ERR_SERVER_ERROR,
        message="Server error",
        detail={"type": type(exc).__name__},
        request_id=req_id,
    )
    return JSONResponse(status_code=500, content=body)

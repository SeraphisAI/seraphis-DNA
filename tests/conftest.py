import os
import sys
from pathlib import Path

import pytest

# Ensure repo root + src/ are importable regardless of how pytest is invoked.
# This avoids "ModuleNotFoundError: api" when CWD is not the repo root.
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Ensure deterministic, test-friendly defaults (must be set BEFORE api.app.main is imported)
os.environ.setdefault("KATOPU_RATE_RPS", "5")
os.environ.setdefault("KATOPU_RATE_BURST", "10")
os.environ.setdefault("KATOPU_REQUIRE_API_KEY", "0")
os.environ.setdefault("KATOPU_TELEMETRY_ENABLED", "0")


@pytest.fixture(scope="session")
def base_url():
    return "http://testserver"

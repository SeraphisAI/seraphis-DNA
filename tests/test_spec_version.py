from fastapi.testclient import TestClient

from api.app.main import app
from katopu_shared.ids import SPEC_VERSION

client = TestClient(app)


def test_nl_spec_includes_spec_version():
    payload = {"sequence": "ATGC", "intent": "ilk 2 baz sil", "mode": "strict"}
    r = client.post("/nl/spec", json=payload)
    assert r.status_code == 200
    j = r.json()
    assert j.get("schema") == "katopu.editspec.v1"
    assert j.get("spec_version") == SPEC_VERSION
    assert j.get("_meta", {}).get("contract")
    assert j.get("_meta", {}).get("engine")


def test_run_includes_spec_version_in_meta():
    body = {"intent": "ilk 2 baz sil", "mode": "strict"}
    r = client.post("/run", params={"sequence": "ATGC"}, json=body)
    assert r.status_code == 200
    j = r.json()
    assert j.get("schema") == "katopu.result.v1"
    assert j.get("_meta", {}).get("spec_version") == SPEC_VERSION

from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)


def test_policy_info_endpoint():
    r = client.get("/policy")
    assert r.status_code == 200
    j = r.json()
    assert j.get("schema") == "katopu.policy.info.v1"
    assert "path" in j
    assert "override" in j
    assert "rules" in j and isinstance(j["rules"], dict)

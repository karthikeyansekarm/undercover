import json

import pytest

from backend import db


def test_list_claims(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    first = claims[0]
    assert first["claim_id"] == "CLM-1001"
    assert first["customer_name"] == "Maya Patel"
    assert first["claim_type"] == "trip_delay"
    assert first["amount_claimed"] == 420.0
    assert {c["status"] for c in claims} == {"waiting"}
    assert first["decision_kind"] is None
    assert first["approved_amount"] is None


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["story"].startswith("My flight home from Rome")
    assert len(claim["items"]) == 3
    assert claim["documents"][0]["type"] == "carrier_report"
    assert claim["decision"] is None
    assert claim["payment"] is None
    assert claim["steps"] == []


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"]["plan"] == "premium"
    assert policy["plan"]["deductible"] == 50.0
    assert policy["plan"]["trip_delay_max"] == 800.0
    assert policy["deductible_applies_to"] == ["baggage", "emergency_medical"]
    assert policy["trip"]["returns_on"] == "2026-06-18"


def test_get_policy_with_add_ons(client):
    policies = [p for p in json.loads(db.load("policies.json")) if p["add_ons"]]
    policy = client.get(f"/api/policies/{policies[0]['policy_id']}").json()
    assert [a["add_on"] for a in policy["add_ons"]] == policies[0]["add_ons"]


def test_get_claim_history_hides_contact_details(client):
    history = client.get("/api/customers/CUS-3001/history").json()
    assert [c["claim_id"] for c in history["previous_claims"]] == ["CLM-0412"]
    for field in ("email", "phone", "address", "date_of_birth", "name"):
        assert field not in history


def test_get_policy_wording(client):
    text = client.get("/api/policy-wording").json()["text"]
    assert text.startswith("# UnderCover Travel Insurance: Policy Wording")
    assert "## 12. Definitions" in text


def test_get_instructions(client):
    assert "UnderCover Agent" in client.get("/api/instructions").json()["text"]


def test_list_handlers(client):
    handlers = client.get("/api/handlers").json()
    assert [h["handler_id"] for h in handlers] == ["HND-01", "HND-02", "HND-03"]
    assert "email" not in handlers[0]


@pytest.mark.parametrize(
    "path",
    [
        "/api/claims/CLM-9999",
        "/api/policies/POL-9999",
        "/api/customers/CUS-9999/history",
    ],
)
def test_not_found(client, path):
    assert client.get(path).status_code == 404


def test_seed_reads_only_the_queue_records(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "seed.db"))
    read = []
    original = db.load
    monkeypatch.setattr(db, "load", lambda name: read.append(name) or original(name))
    db.init()
    assert set(read) == set(db.SEED_FILES)
    assert not any("evals" in name or "security" in name for name in read)


def test_seed_runs_once(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "once.db"))
    db.init()
    db.init()
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0] == 25
    conn.close()


def test_operations_have_ids_and_no_optional_inputs(client):
    spec = client.get("/openapi.json").json()
    for path, methods in spec["paths"].items():
        for operation in methods.values():
            assert operation["operationId"], path
            assert operation["description"], path
            for parameter in operation.get("parameters", []):
                assert parameter["required"], path

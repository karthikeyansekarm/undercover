import json

import pytest

from backend import db


def start(client, claim_id="CLM-1001"):
    response = client.post(f"/api/claims/{claim_id}/start", json={"thread_id": "t1"})
    assert response.status_code == 200
    return response.json()


def decide(client, decision="approve", payout=400.0, claim_id="CLM-1001"):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "reasons": "The delay is covered.",
            "policy_section": "3. Trip Delay",
        },
    )


def pay(client, amount, claim_id="CLM-1001"):
    return client.post(f"/api/claims/{claim_id}/pay", json={"amount": amount})


def sign_off(client, handler_id="HND-01", claim_id="CLM-1001"):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def test_start(client):
    claim = start(client)
    assert claim["status"] == "in_progress"
    assert claim["thread_id"] == "t1"


def test_start_twice(client):
    start(client)
    response = client.post("/api/claims/CLM-1001/start", json={"thread_id": "t2"})
    assert response.status_code == 409


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_decline_or_refer_is_decided(client, decision):
    start(client)
    claim = decide(client, decision, 0).json()
    assert claim["status"] == "decided"
    assert claim["decision"]["decision"] == decision
    assert claim["decision"]["policy_section"] == "3. Trip Delay"


def test_approve_at_the_limit_is_paid_at_once(client):
    start(client)
    assert decide(client, payout=1000.0).json()["status"] == "decided"
    assert pay(client, 1000.0).json()["payment"]["amount"] == 1000.0


def test_approve_over_limit_waits_for_sign_off(client):
    start(client)
    assert decide(client, payout=1000.01).json()["status"] == "awaiting_signoff"
    response = pay(client, 1000.01)
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Payout over $1,000.00 needs a handler's sign-off"
    )
    assert client.get("/api/claims/CLM-1001").json()["payment"] is None


def test_sign_off_pays(client):
    start(client)
    decide(client, payout=1250.0)
    claim = sign_off(client).json()
    assert claim["status"] == "decided"
    assert claim["decision"]["signed_off_by"] == "HND-01"
    assert claim["payment"]["amount"] == 1250.0
    assert pay(client, 1250.0).status_code == 409


def test_sign_off_needs_a_claim_awaiting_sign_off(client):
    start(client)
    decide(client, payout=400.0)
    assert sign_off(client).status_code == 409


def test_sign_off_needs_a_handler_who_can(client):
    with db.connect() as conn:
        row = conn.execute("SELECT data FROM handlers WHERE handler_id = 'HND-03'")
        handler = json.loads(row.fetchone()["data"])
        conn.execute(
            "UPDATE handlers SET data = ? WHERE handler_id = 'HND-03'",
            (json.dumps(handler | {"can_approve_over_limit": False}),),
        )
    conn.close()
    start(client)
    decide(client, payout=1250.0)
    assert sign_off(client, "HND-03").status_code == 403
    assert sign_off(client, "HND-99").status_code == 404


@pytest.mark.parametrize("decision", ["decline", "refer"])
def test_pay_refused_unless_approved(client, decision):
    start(client)
    decide(client, decision, 0)
    assert pay(client, 100.0).status_code == 409


def test_pay_refused_without_decision(client):
    start(client)
    assert pay(client, 100.0).status_code == 409


def test_pay_refused_for_wrong_amount(client):
    start(client)
    decide(client, payout=400.0)
    response = pay(client, 420.0)
    assert response.status_code == 409
    assert response.json()["detail"] == "The approved payout is $400.00, not $420.00"


def test_pay_refused_twice(client):
    start(client)
    decide(client, payout=400.0)
    pay(client, 400.0)
    assert pay(client, 400.0).status_code == 409


def test_decision_rejects_payout_on_decline(client):
    start(client)
    assert decide(client, "decline", 50.0).status_code == 422


def test_decision_needs_a_claim_in_progress(client):
    assert decide(client).status_code == 409
    start(client)
    decide(client)
    assert decide(client).status_code == 409


def test_steps_in_order(client):
    for n in range(3):
        response = client.post(
            "/api/claims/CLM-1001/steps",
            json={"thread_id": "t1", "kind": "message", "content": f"step {n}"},
        )
        assert response.status_code == 200
    steps = client.get("/api/claims/CLM-1001").json()["steps"]
    assert [s["content"] for s in steps] == ["step 0", "step 1", "step 2"]


def test_step_on_unknown_claim(client):
    response = client.post(
        "/api/claims/CLM-9999/steps",
        json={"thread_id": "t1", "kind": "message", "content": "x"},
    )
    assert response.status_code == 404


def test_status_shows_in_the_queue(client):
    start(client)
    decide(client, payout=1250.0)
    claims = {c["claim_id"]: c for c in client.get("/api/claims").json()}
    assert claims["CLM-1001"]["status"] == "awaiting_signoff"

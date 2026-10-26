import json
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import main


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


def call(name, n, **args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": n}])


def decision(payout):
    return {
        "claim_id": "CLM-1001",
        "decision": "approve",
        "payout": payout,
        "reasons": "The delay is covered.",
        "policy_section": "3. Trip Delay",
    }


def stub(*replies):
    return StubModel(messages=iter(replies))


def test_run_approves_and_pays(client):
    llm = stub(
        call("get_claim", "1", claim_id="CLM-1001"),
        call("record_decision", "2", **decision(420.0)),
        call("pay_claim", "3", claim_id="CLM-1001", amount=420.0),
        AIMessage(content="Approved and paid $420.00."),
    )
    assert main.run("CLM-1001", "thread-1", llm) == "Approved and paid $420.00."
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["thread_id"] == "thread-1"
    assert claim["payment"]["amount"] == 420.0
    kinds = [s["kind"] for s in claim["steps"]]
    assert kinds == ["tool_call", "tool_result"] * 3 + ["message"]
    assert claim["steps"][0]["content"] == 'get_claim({"claim_id": "CLM-1001"})'
    assert claim["steps"][1]["content"].startswith("get_claim: {")


def test_run_cannot_pay_over_the_limit(client):
    llm = stub(
        call("record_decision", "1", **decision(1250.0)),
        call("pay_claim", "2", claim_id="CLM-1001", amount=1250.0),
        AIMessage(content="Approved; waiting for sign-off."),
    )
    main.run("CLM-1001", "thread-1", llm)
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "awaiting_signoff"
    assert claim["payment"] is None
    assert claim["steps"][3]["content"] == (
        "pay_claim: Error 409: Payout over $1,000.00 needs a handler's sign-off"
    )


def test_run_records_an_error(client):
    with pytest.raises(RuntimeError):
        main.run("CLM-1001", "thread-1", stub())
    steps = client.get("/api/claims/CLM-1001").json()["steps"]
    assert steps[-1]["content"].startswith("The run stopped with an error")


def test_read_tools(client):
    claim = json.loads(main.get_claim.invoke({"claim_id": "CLM-1001"}))
    assert claim["story"].startswith("My flight home")
    assert "steps" not in claim
    policy = json.loads(main.get_policy.invoke({"policy_id": "POL-2001"}))
    assert policy["plan"]["plan"] == "premium"
    history = json.loads(main.get_claim_history.invoke({"customer_id": "CUS-3001"}))
    assert history["previous_claims"][0]["claim_id"] == "CLM-0412"
    assert "## 3. Trip Delay" in main.get_policy_wording.invoke({})


def test_tool_error_goes_to_the_model(client):
    assert main.get_policy.invoke({"policy_id": "POL-9999"}) == (
        "Error 404: No record POL-9999"
    )


def test_agent_reaches_data_only_through_the_api():
    source = Path(main.__file__).read_text(encoding="utf-8")
    assert "data/" not in source
    assert "open(" not in source
    assert "import backend" not in source
    assert "from backend" not in source


def test_main(client, capsys, monkeypatch):
    monkeypatch.setattr(main, "model", lambda: stub(AIMessage(content="Done.")))
    main.main(["agent", "CLM-1001"])
    assert capsys.readouterr().out.strip() == "Done."


def test_run_all_runs_waiting_claims_and_carries_on_after_an_error(
    client, capsys, monkeypatch
):
    client.post("/api/claims/CLM-1002/start", json={"thread_id": "t"})
    waiting = [
        c["claim_id"]
        for c in client.get("/api/claims").json()
        if c["status"] == "waiting"
    ]
    ran = []

    def fake_run(claim_id, thread_id, llm=None):
        ran.append(claim_id)
        if claim_id == "CLM-1001":
            raise RuntimeError("rate limited")
        return "Decided."

    monkeypatch.setattr(main, "run", fake_run)
    main.main(["agent", "--all"])
    assert ran == waiting
    assert "CLM-1002" not in ran
    out = capsys.readouterr().out
    assert "CLM-1001: The run stopped with an error: rate limited" in out
    assert f"Done: {len(waiting) - 1} decided, 1 stopped with an error." in out


@pytest.mark.parametrize("arg", ["--all", "-all", "all"])
def test_main_accepts_all_spellings(monkeypatch, arg):
    ran = []
    monkeypatch.setattr(main, "run_all", lambda: ran.append(True))
    main.main(["agent", arg])
    assert ran == [True]


def test_main_rejects_an_unknown_option():
    with pytest.raises(SystemExit, match="Usage"):
        main.main(["agent", "-x"])


def test_run_all_with_a_model(client, capsys):
    for claim in client.get("/api/claims").json()[1:]:
        client.post(f"/api/claims/{claim['claim_id']}/start", json={"thread_id": "t"})
    main.run_all(stub(AIMessage(content="Referred.")))
    assert "CLM-1001: Referred." in capsys.readouterr().out


def test_run_agent_starts_a_background_run(client, monkeypatch):
    started = []
    monkeypatch.setattr(main, "run", lambda *args: started.append(args))
    response = client.post("/api/claims/CLM-1001/run")
    assert response.status_code == 200
    assert started == [("CLM-1001", response.json()["thread_id"])]


def test_run_agent_needs_a_waiting_claim(client):
    client.post("/api/claims/CLM-1001/start", json={"thread_id": "t"})
    assert client.post("/api/claims/CLM-1001/run").status_code == 409


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    assert main.model().reasoning_effort == "low"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
    assert main.model().reasoning_effort is None

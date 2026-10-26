"""The UnderCover Agent."""

import json
import os
import uuid
from collections.abc import Iterator
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"
RESULT_LENGTH = 400


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    url = os.getenv("BACKEND_URL", "http://localhost:8000")
    return httpx.Client(base_url=url, timeout=30)


def call(method: str, path: str, body: dict[str, Any] | None = None) -> str:
    """Call the backend and return its reply, or its error for the model to read."""
    with backend() as client:
        response = client.request(method, path, json=body)
    if response.is_error:
        return f"Error {response.status_code}: {response.json()['detail']}"
    return response.text


@tool
def get_claim(claim_id: str) -> str:
    """Get a claim: the customer's story, the items claimed and the documents."""
    claim = json.loads(call("GET", f"/api/claims/{claim_id}"))
    for key in ("steps", "thread_id", "status", "decision", "payment"):
        claim.pop(key)
    return json.dumps(claim)


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy: the plan and its limits, the add-ons, the trip and travelers."""
    return call("GET", f"/api/policies/{policy_id}")


@tool
def get_claim_history(customer_id: str) -> str:
    """Get a customer's earlier claims."""
    return call("GET", f"/api/customers/{customer_id}/history")


@tool
def get_policy_wording() -> str:
    """Get the policy wording, the contract that decisions must follow."""
    return json.loads(call("GET", "/api/policy-wording"))["text"]


@tool
def record_decision(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    reasons: str,
    policy_section: str,
) -> str:
    """Record the decision on a claim, with the payout (0 unless approved), two or
    three sentences of reasons and the policy section it rests on."""
    return call(
        "POST",
        f"/api/claims/{claim_id}/decision",
        {
            "decision": decision,
            "payout": payout,
            "reasons": reasons,
            "policy_section": policy_section,
        },
    )


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim its payout."""
    return call("POST", f"/api/claims/{claim_id}/pay", {"amount": amount})


TOOLS = [
    get_claim,
    get_policy,
    get_claim_history,
    get_policy_wording,
    record_decision,
    pay_claim,
]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def steps(message: BaseMessage) -> list[tuple[str, str]]:
    """Turn one message from the agent into the steps the dashboard shows."""
    if isinstance(message, ToolMessage):
        return [("tool_result", f"{message.name}: {message.text[:RESULT_LENGTH]}")]
    found = []
    if message.text:
        found.append(("message", message.text))
    if isinstance(message, AIMessage):
        found += [
            ("tool_call", f"{c['name']}({json.dumps(c['args'], ensure_ascii=False)})")
            for c in message.tool_calls
        ]
    return found


def messages(
    claim_id: str, thread_id: str, llm: BaseChatModel, instructions: str
) -> Iterator[BaseMessage]:
    """Run the agent and yield each new message as it arrives."""
    agent = create_agent(llm, tools=TOOLS, system_prompt=instructions)
    for update in agent.stream(
        {"messages": [{"role": "user", "content": f"Decide claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
    ):
        for node in update.values():
            yield from (node or {}).get("messages", [])


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, recording each step, and return its final reply."""
    with backend() as client:

        def record(kind: str, content: str) -> None:
            client.post(
                f"/api/claims/{claim_id}/steps",
                json={"thread_id": thread_id, "kind": kind, "content": content},
            ).raise_for_status()

        instructions = client.get("/api/instructions").json()["text"]
        client.post(
            f"/api/claims/{claim_id}/start", json={"thread_id": thread_id}
        ).raise_for_status()
        reply = ""
        try:
            for message in messages(claim_id, thread_id, llm or model(), instructions):
                for kind, content in steps(message):
                    record(kind, content)
                reply = message.text
        except Exception as error:
            record("message", f"The run stopped with an error: {error}")
            raise
    return reply


def run_all(llm: BaseChatModel | None = None) -> None:
    """Run the agent on every waiting claim, one at a time, printing each result."""
    with backend() as client:
        claims = client.get("/api/claims").json()
    waiting = [c["claim_id"] for c in claims if c["status"] == "waiting"]
    print(f"Running the agent on {len(waiting)} waiting claims, one at a time.")
    failed = 0
    for claim_id in waiting:
        try:
            reply = run(claim_id, uuid.uuid4().hex, llm)
        except Exception as error:
            failed += 1
            reply = f"The run stopped with an error: {error}"
        print(f"{claim_id}: {reply}", flush=True)
    print(f"Done: {len(waiting) - failed} decided, {failed} stopped with an error.")


def main(argv: list[str]) -> None:
    """Run the agent on the claim named on the command line, or on every waiting
    claim with --all."""
    arg = argv[1]
    if arg.lstrip("-") == "all":
        run_all()
    elif arg.startswith("-"):
        raise SystemExit("Usage: uv run -m agent CLM-1001, or uv run -m agent --all")
    else:
        print(run(arg, uuid.uuid4().hex))

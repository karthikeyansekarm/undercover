"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException

from backend import db
from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Decision,
    Handler,
    Payment,
    Policy,
    Step,
    Text,
)

INSTRUCTIONS = Path(__file__).resolve().parent / "instructions.md"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.init()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def fetch(conn: sqlite3.Connection, table: str, key: str, value: str) -> Any:
    row = conn.execute(
        f"SELECT data FROM {table} WHERE {key} = ?",  # noqa: S608
        (value,),
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"No record {value}")
    return json.loads(row["data"])


def claim_row(conn: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(404, f"No claim {claim_id}")
    return row


def load_claim(conn: sqlite3.Connection, claim_id: str) -> Claim:
    row = claim_row(conn, claim_id)
    data = json.loads(row["data"])
    customer = fetch(conn, "customers", "customer_id", data["customer_id"])
    decision = conn.execute(
        "SELECT * FROM decisions WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    payment = conn.execute(
        "SELECT * FROM payments WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    steps = conn.execute(
        "SELECT * FROM steps WHERE claim_id = ? ORDER BY id", (claim_id,)
    ).fetchall()
    return Claim(
        **data | {"status": row["status"], "thread_id": row["thread_id"]},
        customer_name=customer["name"],
        decision=Decision(**dict(decision)) if decision else None,
        payment=Payment(**dict(payment)) if payment else None,
        steps=[Step(**dict(s)) for s in steps],
    )


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims(conn: Conn) -> list[ClaimSummary]:
    """List every claim in the queue with where it stands."""
    names = {
        r["customer_id"]: json.loads(r["data"])["name"]
        for r in conn.execute("SELECT * FROM customers")
    }
    summaries = []
    for row in conn.execute("SELECT * FROM claims ORDER BY claim_id"):
        data = json.loads(row["data"])
        summaries.append(
            ClaimSummary(
                **data | {"status": row["status"]},
                customer_name=names[data["customer_id"]],
            )
        )
    return summaries


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, conn: Conn) -> Claim:
    """Get one claim in full, with its decision, payment and the agent's steps."""
    return load_claim(conn, claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, conn: Conn) -> Policy:
    """Get a policy with its plan's limits and its add-ons."""
    policy = fetch(conn, "policies", "policy_id", policy_id)
    plans = db.setting(conn, "plans")
    plan = next(p for p in plans["plans"] if p["plan"] == policy["plan"])
    add_ons = [a for a in plans["add_ons"] if a["add_on"] in policy["add_ons"]]
    return Policy(
        **policy
        | {
            "plan": plan,
            "add_ons": add_ons,
            "deductible_applies_to": plans["deductible_applies_to"],
        }
    )


@app.get("/api/customers/{customer_id}/history", operation_id="get_claim_history")
def get_claim_history(customer_id: str, conn: Conn) -> ClaimHistory:
    """Get a customer's earlier claims, without their contact details."""
    return ClaimHistory(**fetch(conn, "customers", "customer_id", customer_id))


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording(conn: Conn) -> Text:
    """Get the policy wording, the contract with the customer."""
    return Text(text=db.setting(conn, "policy_wording"))


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> Text:
    """Get the UnderCover Agent's instructions."""
    return Text(text=INSTRUCTIONS.read_text(encoding="utf-8"))


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(conn: Conn) -> list[Handler]:
    """List the claims handlers."""
    return [
        Handler(**json.loads(r["data"]))
        for r in conn.execute("SELECT * FROM handlers ORDER BY handler_id")
    ]

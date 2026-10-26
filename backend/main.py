"""The UnderCover backend."""

import json
import sqlite3
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException

from agent import main as agent
from backend import db
from backend.models import (
    Claim,
    ClaimHistory,
    ClaimSummary,
    Decision,
    DecisionInput,
    Handler,
    Payment,
    PaymentInput,
    Policy,
    RunStarted,
    SignOffInput,
    StartInput,
    Step,
    StepInput,
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
    """List every claim in the queue with where it stands and its decision."""
    names = {
        r["customer_id"]: json.loads(r["data"])["name"]
        for r in conn.execute("SELECT * FROM customers")
    }
    decisions = {
        r["claim_id"]: (r["decision"], r["payout"])
        for r in conn.execute("SELECT * FROM decisions")
    }
    summaries = []
    for row in conn.execute("SELECT * FROM claims ORDER BY claim_id"):
        data = json.loads(row["data"])
        kind, payout = decisions.get(row["claim_id"], (None, None))
        summaries.append(
            ClaimSummary(
                **data | {"status": row["status"]},
                customer_name=names[data["customer_id"]],
                decision_kind=kind,
                approved_amount=payout if kind == "approve" else None,
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


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def money(amount: float) -> str:
    return f"${amount:,.2f}"


def require_status(row: sqlite3.Row, status: str) -> None:
    if row["status"] != status:
        raise HTTPException(
            409, f"Claim {row['claim_id']} is {row['status']}, not {status}"
        )


def pay(conn: sqlite3.Connection, claim_id: str, amount: float) -> None:
    conn.execute(
        "INSERT INTO payments (claim_id, amount, paid_at) VALUES (?, ?, ?)",
        (claim_id, amount, now()),
    )


def approval_limit(conn: sqlite3.Connection) -> float:
    return db.setting(conn, "company")["payout_approval_limit"]


@app.post("/api/claims/{claim_id}/run", operation_id="run_agent")
def run_agent(claim_id: str, background: BackgroundTasks, conn: Conn) -> RunStarted:
    """Start the UnderCover Agent on a waiting claim."""
    require_status(claim_row(conn, claim_id), "waiting")
    thread_id = uuid.uuid4().hex
    background.add_task(agent.run, claim_id, thread_id)
    return RunStarted(claim_id=claim_id, thread_id=thread_id)


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, body: StartInput, conn: Conn) -> Claim:
    """Mark a waiting claim as in progress for an agent run."""
    with conn:
        require_status(claim_row(conn, claim_id), "waiting")
        conn.execute(
            "UPDATE claims SET status = 'in_progress', thread_id = ?"
            " WHERE claim_id = ?",
            (body.thread_id, claim_id),
        )
    return load_claim(conn, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="record_step")
def record_step(claim_id: str, body: StepInput, conn: Conn) -> Step:
    """Record one step the agent took on a claim."""
    with conn:
        claim_row(conn, claim_id)
        cursor = conn.execute(
            "INSERT INTO steps (claim_id, thread_id, kind, content, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (claim_id, body.thread_id, body.kind, body.content, now()),
        )
    row = conn.execute("SELECT * FROM steps WHERE id = ?", (cursor.lastrowid,))
    return Step(**dict(row.fetchone()))


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, body: DecisionInput, conn: Conn) -> Claim:
    """Record the decision on a claim: approve with a payout, decline or refer."""
    if body.decision != "approve" and body.payout > 0:
        raise HTTPException(422, f"A {body.decision} has no payout")
    over_limit = body.decision == "approve" and body.payout > approval_limit(conn)
    with conn:
        require_status(claim_row(conn, claim_id), "in_progress")
        conn.execute(
            "INSERT INTO decisions (claim_id, decision, payout, reasons,"
            " policy_section, decided_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                claim_id,
                body.decision,
                round(body.payout, 2),
                body.reasons,
                body.policy_section,
                now(),
            ),
        )
        conn.execute(
            "UPDATE claims SET status = ? WHERE claim_id = ?",
            ("awaiting_signoff" if over_limit else "decided", claim_id),
        )
    return load_claim(conn, claim_id)


@app.post("/api/claims/{claim_id}/pay", operation_id="pay_claim")
def pay_claim(claim_id: str, body: PaymentInput, conn: Conn) -> Claim:
    """Pay an approved claim its payout."""
    claim = load_claim(conn, claim_id)
    decision = claim.decision
    if decision is None or decision.decision != "approve":
        raise HTTPException(409, f"Claim {claim_id} is not approved")
    if claim.payment is not None:
        raise HTTPException(409, f"Claim {claim_id} is already paid")
    if round(body.amount, 2) != decision.payout:
        raise HTTPException(
            409,
            f"The approved payout is {money(decision.payout)},"
            f" not {money(body.amount)}",
        )
    limit = approval_limit(conn)
    if decision.payout > limit and decision.signed_off_by is None:
        raise HTTPException(
            409, f"Payout over {money(limit)} needs a handler's sign-off"
        )
    with conn:
        pay(conn, claim_id, decision.payout)
    return load_claim(conn, claim_id)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off")
def sign_off(claim_id: str, body: SignOffInput, conn: Conn) -> Claim:
    """Sign off an approval over the limit, which releases its payment."""
    handler = fetch(conn, "handlers", "handler_id", body.handler_id)
    if not handler["can_approve_over_limit"]:
        raise HTTPException(403, f"{handler['name']} cannot approve over the limit")
    with conn:
        require_status(claim_row(conn, claim_id), "awaiting_signoff")
        conn.execute(
            "UPDATE decisions SET signed_off_by = ? WHERE claim_id = ?",
            (body.handler_id, claim_id),
        )
        payout = conn.execute(
            "SELECT payout FROM decisions WHERE claim_id = ?", (claim_id,)
        ).fetchone()["payout"]
        pay(conn, claim_id, payout)
        conn.execute(
            "UPDATE claims SET status = 'decided' WHERE claim_id = ?", (claim_id,)
        )
    return load_claim(conn, claim_id)

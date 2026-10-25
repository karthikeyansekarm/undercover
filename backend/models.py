"""The shapes the UnderCover API sends and receives."""

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["waiting", "in_progress", "awaiting_signoff", "decided"]
DecisionKind = Literal["approve", "decline", "refer"]
StepKind = Literal["tool_call", "tool_result", "message"]


class Item(BaseModel):
    description: str
    category: str
    amount: float


class Document(BaseModel):
    name: str
    type: str
    content: str


class ClaimSummary(BaseModel):
    claim_id: str
    customer_name: str
    claim_type: str
    submitted_on: str
    summary: str
    amount_claimed: float
    status: Status


class Decision(BaseModel):
    decision: DecisionKind
    payout: float
    reasons: str
    policy_section: str
    decided_at: str
    signed_off_by: str | None


class Payment(BaseModel):
    amount: float
    paid_at: str


class Step(BaseModel):
    id: int
    thread_id: str
    kind: StepKind
    content: str
    created_at: str


class Claim(BaseModel):
    claim_id: str
    policy_id: str
    customer_id: str
    customer_name: str
    claim_type: str
    submitted_on: str
    incident_date: str
    incident_location: str
    summary: str
    story: str
    items: list[Item]
    amount_claimed: float
    documents: list[Document]
    status: Status
    thread_id: str | None
    decision: Decision | None
    payment: Payment | None
    steps: list[Step]


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Plan(BaseModel):
    plan: str
    name: str
    trip_cancellation_max: float
    trip_delay_waiting_hours: int
    trip_delay_max: float
    baggage_delay_waiting_hours: int
    baggage_delay_max: float
    baggage_max: float
    per_item_limit: float
    passport_max: float
    emergency_medical_max: float
    deductible: float


class AddOn(BaseModel):
    add_on: str
    name: str
    effect: str
    electronics_per_item_limit: float | None = None


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: Plan
    add_ons: list[AddOn]
    deductible_applies_to: list[str]
    purchased_on: str
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class PreviousClaim(BaseModel):
    claim_id: str
    filed_on: str
    incident_date: str
    claim_type: str
    summary: str
    outcome: str
    amount_paid: float


class ClaimHistory(BaseModel):
    customer_id: str
    customer_since: str
    previous_claims: list[PreviousClaim]


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str
    can_approve_over_limit: bool


class Text(BaseModel):
    text: str


class RunStarted(BaseModel):
    claim_id: str
    thread_id: str


class StartInput(BaseModel):
    thread_id: str


class StepInput(BaseModel):
    thread_id: str
    kind: StepKind
    content: str


class DecisionInput(BaseModel):
    decision: DecisionKind
    payout: float = Field(ge=0)
    reasons: str = Field(min_length=1)
    policy_section: str = Field(min_length=1)


class PaymentInput(BaseModel):
    amount: float = Field(gt=0)


class SignOffInput(BaseModel):
    handler_id: str

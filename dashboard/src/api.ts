export type Status = "waiting" | "in_progress" | "awaiting_signoff" | "decided";

export interface ClaimSummary {
  claim_id: string;
  customer_name: string;
  claim_type: string;
  submitted_on: string;
  summary: string;
  amount_claimed: number;
  status: Status;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface Document {
  name: string;
  type: string;
  content: string;
}

export interface Decision {
  decision: "approve" | "decline" | "refer";
  payout: number;
  reasons: string;
  policy_section: string;
  decided_at: string;
  signed_off_by: string | null;
}

export interface Payment {
  amount: number;
  paid_at: string;
}

export interface Step {
  id: number;
  thread_id: string;
  kind: "tool_call" | "tool_result" | "message";
  content: string;
  created_at: string;
}

export interface Claim extends ClaimSummary {
  policy_id: string;
  customer_id: string;
  incident_date: string;
  incident_location: string;
  story: string;
  items: Item[];
  documents: Document[];
  thread_id: string | null;
  decision: Decision | null;
  payment: Payment | null;
  steps: Step[];
}

export interface Plan {
  name: string;
  deductible: number;
  per_item_limit: number;
}

export interface Policy {
  policy_id: string;
  plan: Plan;
  add_ons: { add_on: string; name: string }[];
  purchased_on: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
  can_approve_over_limit: boolean;
}

export async function get<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok)
    throw new Error(`${path} returned ${String(response.status)}`);
  return (await response.json()) as T;
}

export async function post<T>(path: string, body: object): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok)
    throw new Error(`${path} returned ${String(response.status)}`);
  return (await response.json()) as T;
}

export interface Text {
  text: string;
}

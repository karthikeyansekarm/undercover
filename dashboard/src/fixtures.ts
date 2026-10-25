import { vi } from "vitest";
import type { Claim, ClaimSummary, Handler, Policy } from "./api";

export const summaries: ClaimSummary[] = [
  {
    claim_id: "CLM-1001",
    customer_name: "Maya Patel",
    claim_type: "trip_delay",
    submitted_on: "2026-06-24",
    summary: "Flight home canceled",
    amount_claimed: 1250,
    status: "waiting",
  },
  {
    claim_id: "CLM-1002",
    customer_name: "Sam Ortiz",
    claim_type: "baggage",
    submitted_on: "2026-06-25",
    summary: "Suitcase lost",
    amount_claimed: 300,
    status: "decided",
  },
];

export const claim: Claim = {
  ...summaries[0],
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  story: "My flight home from Rome was canceled.",
  items: [
    { description: "Airport hotel", category: "accommodation", amount: 1250 },
  ],
  documents: [
    {
      name: "Cancellation notice",
      type: "carrier_report",
      content: "Flight MA 611 was canceled.",
    },
  ],
  thread_id: null,
  decision: null,
  payment: null,
  steps: [],
};

export const policy: Policy = {
  policy_id: "POL-2001",
  plan: { name: "UnderCover Premium", deductible: 50, per_item_limit: 300 },
  add_ons: [],
  purchased_on: "2026-04-22",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
};

export const handlers: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
    can_approve_over_limit: true,
  },
  {
    handler_id: "HND-02",
    name: "Marcus Oyelaran",
    role: "Claims Handler",
    can_approve_over_limit: true,
  },
];

export function stubApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((input: string, init?: RequestInit) => {
    const key = init?.method === "POST" ? `POST ${input}` : input;
    if (!(key in routes))
      return Promise.resolve(new Response("{}", { status: 404 }));
    return Promise.resolve(new Response(JSON.stringify(routes[key])));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

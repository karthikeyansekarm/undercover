import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim, Decision, Step } from "./api";
import { ClaimPage } from "./ClaimPage";
import { claim, handlers, policy, stubApi } from "./fixtures";
import { Steps } from "./Steps";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const steps: Step[] = [
  {
    id: 1,
    thread_id: "t1",
    kind: "tool_call",
    content: 'get_claim({"claim_id": "CLM-1001"})',
    created_at: "2026-10-25T08:00:00+00:00",
  },
  {
    id: 2,
    thread_id: "t1",
    kind: "tool_result",
    content: "get_claim: {...}",
    created_at: "2026-10-25T08:00:01+00:00",
  },
  {
    id: 3,
    thread_id: "t1",
    kind: "message",
    content: "Approved.",
    created_at: "2026-10-25T08:00:02+00:00",
  },
];

const approval: Decision = {
  decision: "approve",
  payout: 1250,
  reasons: "Covered.",
  policy_section: "3. Trip Delay",
  decided_at: "2026-10-25T08:00:00+00:00",
  signed_off_by: null,
};

it("lists the steps in order", () => {
  render(<Steps steps={steps} working={false} />);
  const items = screen.getAllByRole("listitem");
  expect(items.map((i) => i.textContent)).toEqual([
    'Tool call get_claim({"claim_id": "CLM-1001"})',
    "Result get_claim: {...}",
    "Agent Approved.",
  ]);
});

it("says when the agent has not run or is starting", () => {
  const { rerender } = render(<Steps steps={[]} working={false} />);
  expect(screen.getByText("The agent has not run yet.")).toBeDefined();
  rerender(<Steps steps={[]} working />);
  expect(screen.getByText("The agent is starting...")).toBeDefined();
  rerender(<Steps steps={steps} working />);
  expect(screen.getByText("Working...")).toBeDefined();
});

it("polls while the claim is in progress and stops when it is decided", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const replies: Claim[] = [
    { ...claim, status: "in_progress", steps: steps.slice(0, 1) },
    { ...claim, status: "in_progress", steps: steps.slice(0, 2) },
    {
      ...claim,
      status: "decided",
      steps,
      decision: { ...approval, decision: "decline", payout: 0 },
    },
  ];
  const fetchMock = vi.fn((input: string) => {
    const body =
      input === "/api/claims/CLM-1001" ? (replies.shift() ?? claim) : policy;
    return Promise.resolve(new Response(JSON.stringify(body)));
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText(steps[0].content)).toBeDefined();
  await vi.advanceTimersByTimeAsync(1000);
  expect(await screen.findByText("get_claim: {...}")).toBeDefined();
  await vi.advanceTimersByTimeAsync(1000);
  expect(await screen.findByText("Declined")).toBeDefined();
  const claimCalls = () =>
    fetchMock.mock.calls.filter(([url]) => url === "/api/claims/CLM-1001")
      .length;
  const calls = claimCalls();
  await vi.advanceTimersByTimeAsync(5000);
  expect(claimCalls()).toBe(calls);
});

it("starts the agent from a waiting claim", async () => {
  const fetchMock = stubApi({
    "/api/claims/CLM-1001": claim,
    "/api/policies/POL-2001": policy,
    "POST /api/claims/CLM-1001/run": { claim_id: "CLM-1001", thread_id: "t1" },
  });
  render(<ClaimPage claimId="CLM-1001" />);
  fireEvent.click(await screen.findByRole("button", { name: "Run agent" }));
  expect(await screen.findByText("The agent is starting...")).toBeDefined();
  expect(screen.queryByRole("button", { name: "Run agent" })).toBeNull();
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/claims/CLM-1001/run",
    expect.objectContaining({ method: "POST" }),
  );
});

it("says when the agent cannot start", async () => {
  stubApi({
    "/api/claims/CLM-1001": claim,
    "/api/policies/POL-2001": policy,
  });
  render(<ClaimPage claimId="CLM-1001" />);
  fireEvent.click(await screen.findByRole("button", { name: "Run agent" }));
  expect(await screen.findByText("The agent could not start.")).toBeDefined();
});

it("signs off a claim with the chosen handler", async () => {
  const waiting = {
    ...claim,
    status: "awaiting_signoff" as const,
    decision: approval,
  };
  const fetchMock = stubApi({
    "/api/claims/CLM-1001": waiting,
    "/api/policies/POL-2001": policy,
    "/api/handlers": handlers,
    "POST /api/claims/CLM-1001/sign-off": waiting,
  });
  render(<ClaimPage claimId="CLM-1001" />);
  const button = await screen.findByRole("button", {
    name: "Sign off and pay",
  });
  expect(button.hasAttribute("disabled")).toBe(true);
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(button);
  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/claims/CLM-1001/sign-off",
      expect.objectContaining({
        body: JSON.stringify({ handler_id: "HND-01" }),
      }),
    );
  });
});

it("shows sign-off only for claims waiting for it", async () => {
  stubApi({
    "/api/claims/CLM-1001": { ...claim, status: "decided", decision: approval },
    "/api/policies/POL-2001": policy,
    "/api/handlers": handlers,
  });
  render(<ClaimPage claimId="CLM-1001" />);
  await screen.findByText("Approved");
  expect(screen.queryByText("Sign-off")).toBeNull();
});

it("says when the sign-off fails", async () => {
  stubApi({
    "/api/claims/CLM-1001": {
      ...claim,
      status: "awaiting_signoff",
      decision: approval,
    },
    "/api/policies/POL-2001": policy,
    "/api/handlers": handlers,
  });
  render(<ClaimPage claimId="CLM-1001" />);
  fireEvent.change(await screen.findByRole("combobox"), {
    target: { value: "HND-02" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect(
    await screen.findByText("The sign-off did not go through."),
  ).toBeDefined();
});

it("keeps polling until an approval within the limit is paid", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const decided = { ...approval, payout: 400 };
  const replies: Claim[] = [
    { ...claim, status: "decided", decision: decided },
    {
      ...claim,
      status: "decided",
      decision: decided,
      payment: { amount: 400, paid_at: "2026-10-25T08:00:05+00:00" },
    },
  ];
  stubApi({ "/api/policies/POL-2001": policy });
  vi.stubGlobal(
    "fetch",
    vi.fn((input: string) => {
      const body =
        input === "/api/claims/CLM-1001" ? (replies.shift() ?? claim) : policy;
      return Promise.resolve(new Response(JSON.stringify(body)));
    }),
  );
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Not paid yet")).toBeDefined();
  await vi.advanceTimersByTimeAsync(1000);
  expect(await screen.findByText("Paid $400.00 on 2026-10-25")).toBeDefined();
});

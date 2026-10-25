import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim, Decision } from "./api";
import { ClaimPage } from "./ClaimPage";
import { claim, policy, stubApi } from "./fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const approval: Decision = {
  decision: "approve",
  payout: 1250,
  reasons: "The delay is covered.",
  policy_section: "3. Trip Delay",
  decided_at: "2026-10-25T08:00:00+00:00",
  signed_off_by: null,
};

function show(value: Claim) {
  stubApi({
    "/api/claims/CLM-1001": value,
    "/api/policies/POL-2001": policy,
  });
  render(<ClaimPage claimId="CLM-1001" />);
}

it("shows the claim in full", async () => {
  show(claim);
  expect(await screen.findByText(claim.story)).toBeDefined();
  expect(screen.getByText("Airport hotel")).toBeDefined();
  expect(screen.getByText("Cancellation notice")).toBeDefined();
  expect(screen.getByText("Flight MA 611 was canceled.")).toBeDefined();
  expect(await screen.findByText("UnderCover Premium")).toBeDefined();
  expect(screen.getByText("$3,100.00")).toBeDefined();
  expect(screen.queryByText("Decision")).toBeNull();
});

it("shows an approval waiting for sign-off", async () => {
  show({ ...claim, status: "awaiting_signoff", decision: approval });
  expect(await screen.findByText("Approved")).toBeDefined();
  expect(screen.getByText("The delay is covered.")).toBeDefined();
  expect(screen.getByText("Policy section: 3. Trip Delay")).toBeDefined();
  expect(
    screen.getByText("Payment waiting for a handler's sign-off"),
  ).toBeDefined();
});

it("shows a paid approval and who signed it off", async () => {
  show({
    ...claim,
    status: "decided",
    decision: { ...approval, signed_off_by: "HND-01" },
    payment: { amount: 1250, paid_at: "2026-10-25T09:00:00+00:00" },
  });
  expect(await screen.findByText("Paid $1,250.00 on 2026-10-25")).toBeDefined();
  expect(screen.getByText("HND-01")).toBeDefined();
});

it("shows an approval not yet paid", async () => {
  show({ ...claim, status: "decided", decision: { ...approval, payout: 400 } });
  expect(await screen.findByText("Not paid yet")).toBeDefined();
});

it("shows a decline without a payment", async () => {
  show({
    ...claim,
    status: "decided",
    decision: { ...approval, decision: "decline", payout: 0 },
  });
  expect(await screen.findByText("Declined")).toBeDefined();
  expect(screen.queryByText(/Paid|Not paid/)).toBeNull();
});

it("says when the claim cannot be loaded", async () => {
  stubApi({});
  render(<ClaimPage claimId="CLM-9999" />);
  expect(await screen.findByRole("alert")).toBeDefined();
});

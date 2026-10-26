import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubApi, summaries } from "./fixtures";
import { Queue } from "./Queue";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("lists the claims with their status and amount", async () => {
  stubApi({ "/api/claims": summaries });
  render(<Queue />);
  const link = await screen.findByRole("link", { name: "CLM-1001" });
  expect(link.getAttribute("href")).toBe("#/claims/CLM-1001");
  expect(screen.getByText("$1,250.00")).toBeDefined();
  expect(screen.getByText("Trip delay")).toBeDefined();
  expect(screen.getByText("Waiting", { selector: ".chip" })).toBeDefined();
  expect(screen.getByText("Decided", { selector: ".chip" })).toBeDefined();
});

it("shows each claim's decision and approved amount", async () => {
  stubApi({ "/api/claims": summaries });
  render(<Queue />);
  const decided = await screen.findByRole("row", { name: /CLM-1002/ });
  expect(within(decided).getByText("Approved")).toBeDefined();
  expect(within(decided).getByText("$250.00")).toBeDefined();
  const waiting = screen.getByRole("row", { name: /CLM-1001/ });
  expect(within(waiting).getAllByText("-")).toHaveLength(2);
});

it("shows no approved amount for a declined claim", async () => {
  stubApi({
    "/api/claims": [
      { ...summaries[1], decision_kind: "decline", approved_amount: null },
    ],
  });
  render(<Queue />);
  const row = await screen.findByRole("row", { name: /CLM-1002/ });
  expect(within(row).getByText("Declined")).toBeDefined();
  expect(within(row).getByText("-")).toBeDefined();
});

it("filters by status with counts", async () => {
  stubApi({ "/api/claims": summaries });
  render(<Queue />);
  await screen.findByText("CLM-1001");
  const decided = screen.getByRole("button", { name: "Decided 1" });
  expect(screen.getByRole("button", { name: "All 2" })).toBeDefined();
  expect(
    screen.getByRole("button", { name: "Waiting for sign-off 0" }),
  ).toBeDefined();

  fireEvent.click(decided);
  expect(decided.getAttribute("aria-pressed")).toBe("true");
  expect(screen.queryByText("CLM-1001")).toBeNull();
  expect(screen.getByText("CLM-1002")).toBeDefined();

  fireEvent.click(screen.getByRole("button", { name: "All 2" }));
  expect(screen.getByText("CLM-1001")).toBeDefined();
});

it("says when the queue cannot be loaded", async () => {
  stubApi({});
  render(<Queue />);
  expect(await screen.findByRole("alert")).toBeDefined();
});

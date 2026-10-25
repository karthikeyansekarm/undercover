import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";
import { claim, policy, stubApi, summaries } from "./fixtures";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.location.hash = "";
});

it("shows that the backend is up", async () => {
  stubApi({ "/api/health": { status: "ok" }, "/api/claims": summaries });
  render(<App />);
  expect(await screen.findByText("Backend: up")).toBeDefined();
});

it("shows that the backend is down", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  render(<App />);
  expect(await screen.findByText("Backend: down")).toBeDefined();
});

it("shows the queue by default", async () => {
  stubApi({ "/api/claims": summaries });
  render(<App />);
  expect(await screen.findByText("Claims queue")).toBeDefined();
});

it("routes to a claim and to the instructions", async () => {
  stubApi({
    "/api/claims/CLM-1001": claim,
    "/api/policies/POL-2001": policy,
    "/api/instructions": { text: "Decide claims." },
  });
  window.location.hash = "#/claims/CLM-1001";
  render(<App />);
  expect(await screen.findByText(claim.story)).toBeDefined();

  window.location.hash = "#/instructions";
  window.dispatchEvent(new HashChangeEvent("hashchange"));
  expect(await screen.findByText("Decide claims.")).toBeDefined();
});

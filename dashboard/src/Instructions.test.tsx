import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { stubApi } from "./fixtures";
import { Instructions } from "./Instructions";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the instructions read only", async () => {
  stubApi({ "/api/instructions": { text: "# UnderCover Agent" } });
  render(<Instructions />);
  expect(await screen.findByText("# UnderCover Agent")).toBeDefined();
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});

it("says when the instructions cannot be loaded", async () => {
  stubApi({});
  render(<Instructions />);
  expect(await screen.findByRole("alert")).toBeDefined();
});

import { expect, test, type APIRequestContext } from "@playwright/test";

// These tests play the agent's part through the API, so no model is called.

async function start(request: APIRequestContext, claimId: string) {
  const response = await request.post(`/api/claims/${claimId}/start`, {
    data: { thread_id: "e2e" },
  });
  expect(response.ok()).toBe(true);
}

async function decide(
  request: APIRequestContext,
  claimId: string,
  decision: string,
  payout: number,
) {
  const response = await request.post(`/api/claims/${claimId}/decision`, {
    data: {
      decision,
      payout,
      reasons: "The documents support the claim.",
      policy_section: "5. Baggage and Personal Effects",
    },
  });
  expect(response.ok()).toBe(true);
}

test("the agent's steps appear as it works", async ({ page, request }) => {
  await start(request, "CLM-1003");
  await page.goto("/#/claims/CLM-1003");
  await expect(page.getByText("In progress", { exact: true })).toBeVisible();

  await request.post("/api/claims/CLM-1003/steps", {
    data: {
      thread_id: "e2e",
      kind: "tool_call",
      content: 'get_claim({"claim_id": "CLM-1003"})',
    },
  });
  await expect(
    page.getByText('get_claim({"claim_id": "CLM-1003"})'),
  ).toBeVisible({
    timeout: 2000,
  });
});

test("a payout over $1,000 waits for a handler's sign-off", async ({
  page,
  request,
}) => {
  await start(request, "CLM-1002");
  await decide(request, "CLM-1002", "approve", 1250);

  await page.goto("/");
  const row = page.getByRole("row", { name: /CLM-1002/ });
  await expect(row.getByText("Waiting for sign-off")).toBeVisible();

  await row.getByRole("link", { name: "CLM-1002" }).click();
  await expect(
    page.getByText("Payment waiting for a handler's sign-off"),
  ).toBeVisible();
  await page.getByRole("combobox").selectOption({ label: "Dana Whitfield" });
  await page.getByRole("button", { name: "Sign off and pay" }).click();

  await expect(page.getByText("Decided", { exact: true })).toBeVisible();
  await expect(page.getByText(/Paid \$1,250\.00 on/)).toBeVisible();
  await expect(page.getByText("HND-01")).toBeVisible();
});

test("a declined claim shows its reasons and no payment", async ({
  page,
  request,
}) => {
  await start(request, "CLM-1004");
  await decide(request, "CLM-1004", "decline", 0);

  await page.goto("/#/claims/CLM-1004");
  await expect(page.getByText("Declined")).toBeVisible();
  await expect(
    page.getByText("The documents support the claim."),
  ).toBeVisible();
  await expect(
    page.getByText("Policy section: 5. Baggage and Personal Effects"),
  ).toBeVisible();
  await expect(page.getByText(/Paid|Not paid/)).toHaveCount(0);
});

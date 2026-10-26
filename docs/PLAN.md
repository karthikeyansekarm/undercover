# Plan: the claims pilot

This plan builds the pilot in `docs/SPEC.md` on the stack in `docs/TECH_STACK.md`, starting from the hello-world skeleton in `docs/STATUS.md`. It has six phases. Each one leaves every check green and is committed before the next starts.

## The shape of the build

```
dashboard (React)  --->  backend (FastAPI + SQLite)  <---  agent (create_agent on OpenRouter)
   reads the queue,         owns the data and the           reads the claim and its
   claims, steps and        rules, including the            instructions, records steps,
   instructions; starts     $1,000 sign-off rule            its decision and the payment,
   a run; signs off                                         all through the API
```

The backend is the single source of truth and the only place the business rules live. The agent and the dashboard are both clients of its API. This is why the sign-off rule holds "even if the agent tries to pay": the agent has no way to pay except the `pay_claim` operation, and that operation refuses.

## Decisions worth reviewing

- **Database.** SQLite in one file, `backend/undercover.db` (git-ignored), path overridable with `UNDERCOVER_DB`. On startup the backend creates the tables and, if the database is empty, seeds it from `data/`. Tests use a fresh file in a temporary folder.
- **Seeding loads only the queue's own records.** The seed reads `claims.json`, `policies.json`, `customers.json`, `plans.json`, `company.json`, `handlers.json` and `policy_wording.md`. It never touches `data/evals/`, `data/security/`, `claims_manual.md` (not for now, per the spec) or `knowledge.json`. A test asserts the seed's file list, so the answer key can't creep in.
- **Claim states.** `waiting`, `in_progress`, `awaiting_signoff`, `decided`, matching the four the spec names. Claims in `claims.json` arrive as `open` and are seeded as `waiting`. A referred claim ends as `decided` with the decision `refer`: the agent is done with it, and the dashboard shows it needs a handler.
- **The agent's instructions live in the backend**, in `backend/instructions.md`, served by `get_instructions`. The agent fetches them at the start of each run and the dashboard shows the same text, so what handlers read is exactly what the agent gets.
- **Steps.** The agent's `run` streams the graph with `agent.stream(..., stream_mode="updates")` and posts each update to the backend as a step: a tool call (name and arguments), a tool result (shortened), or the model's text. The dashboard polls the claim every second while it is `in_progress`. Polling is simpler than server-sent events and fast enough for a person watching.
- **Starting a run.** Two ways: `uv run -m agent CLM-1001` from the terminal, and a "Run agent" button on a waiting claim in the dashboard, which calls `POST /api/claims/{id}/run`. That operation sets a new thread id and runs the agent as a FastAPI background task; the agent then calls back into the API over HTTP like any other client. `BACKEND_URL` (default `http://localhost:8000`) tells the agent where the API is.
- **Paying.** After recording an approval, the agent calls `pay_claim` with the amount. The backend pays only if the claim is approved, the amount equals the approved payout, it hasn't been paid, and, for payouts over the limit in `company.json` ($1,000), a handler has signed off. Otherwise it returns 409 with the reason, which the agent sees. When a handler signs off, the backend makes the payment itself at the approved payout. Payments are records only; nothing real moves.
- **Sign-off.** No sign-in for the pilot, so the dashboard offers a handler picker. The backend checks that handler's `can_approve_over_limit`.
- **Payout arithmetic** is done by the model, guided by the instructions and section 10 of the wording ("How we work out your payment"), and shown in its reasons. No calculator tool for now; the spec doesn't ask for one, and the evaluation work later will tell us if one is needed.
- **Checking against the handlers' decisions** is not built in the pilot. The spec says the agent must never see `data/evals/`; the process says not to open it unless asked. The pilot guarantees the isolation; scoring comes with the evaluations build.
- **Dashboard routing** uses the URL hash (`#/`, `#/claims/CLM-1001`, `#/instructions`) with a few lines of code instead of a router library. Three pages don't justify a dependency.

## The API

Every operation has an `operation_id`, a one-line docstring and no optional inputs.

| Method and path | operation_id | Used by |
|---|---|---|
| `GET /api/health` | `health` | dashboard |
| `GET /api/claims` | `list_claims` | dashboard (with each claim's decision and approved amount, added in Phase 7); `--all` runs |
| `GET /api/claims/{claim_id}` | `get_claim` | both: the claim, its decision, payment and steps |
| `GET /api/policies/{policy_id}` | `get_policy` | agent: the policy with its plan's limits and add-on details |
| `GET /api/customers/{customer_id}/history` | `get_claim_history` | agent: earlier claims only, no contact details |
| `GET /api/policy-wording` | `get_policy_wording` | agent |
| `GET /api/instructions` | `get_instructions` | both |
| `GET /api/handlers` | `list_handlers` | dashboard |
| `POST /api/claims/{claim_id}/run` | `run_agent` | dashboard |
| `POST /api/claims/{claim_id}/start` | `start_claim` | agent run: `waiting` to `in_progress` |
| `POST /api/claims/{claim_id}/steps` | `record_step` | agent run |
| `POST /api/claims/{claim_id}/decision` | `record_decision` | agent: decision, payout, reasons, policy section |
| `POST /api/claims/{claim_id}/pay` | `pay_claim` | agent: takes the amount |
| `POST /api/claims/{claim_id}/sign-off` | `sign_off` | dashboard: takes the handler id |

A decision is `approve`, `decline` or `refer`, with a payout (0 unless approved), reasons in two or three sentences, and the policy section (such as "3. Trip Delay"). An approval over $1,000 moves the claim to `awaiting_signoff`; any other decision moves it to `decided`.

The agent's tools are thin wrappers over `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`. It has no other way to reach data.

---

## Phase 1: Backend data and read API

Builds the SQLite schema, the seed from `data/`, and the read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions`, `list_handlers`. Adds a first draft of `backend/instructions.md`. Why first: everything else reads this data.

- [x] `uv run pytest -q backend` passes, with tests for each read operation and for a 404 on an unknown claim, policy and customer
- [x] A test asserts the seed reads exactly the seven files listed above and nothing under `data/evals/` or `data/security/`
- [x] With `npm run dev:backend` running, `GET /api/claims` returns 25 claims, each with `claim_id`, `summary`, `claim_type`, `amount_claimed` and `status: "waiting"`
- [x] `GET /api/claims/CLM-1001` returns the story, three items, the documents, and `decision: null`, `payment: null`, `steps: []`
- [x] `GET /api/policies/POL-2001` includes the Premium plan's limits and deductible
- [x] `GET /api/customers/CUS-3001/history` returns CLM-0412 and no email, phone, address or date of birth
- [x] `GET /api/policy-wording` returns the wording with all 12 sections
- [x] `/openapi.json` shows an `operationId` and a summary for every operation, and no optional parameters
- [x] `npm run check:python` passes, coverage at or above 80%

## Phase 2: Backend workflow and the sign-off rule

Builds `start_claim`, `record_step`, `record_decision`, `pay_claim` and `sign_off`, with the state changes and payment rules above. Why now: the rules must exist, and be tested, before an agent can exercise them.

- [x] Tests cover each state change: `waiting` to `in_progress` to `decided` (decline, refer, approve at or under $1,000) and to `awaiting_signoff` (approve over $1,000) and then `decided` on sign-off
- [x] Test: an approval of $1,000.00 exactly can be paid at once; $1,000.01 cannot
- [x] Test: `pay_claim` on a claim awaiting sign-off returns 409 and records no payment
- [x] Test: `pay_claim` returns 409 for a declined or referred claim, a claim with no decision, a wrong amount, or a second payment
- [x] Test: `sign_off` pays the approved payout, records the handler, and returns 409 on a claim not awaiting sign-off
- [x] Test: `record_decision` rejects a payout above 0 on a decline or refer (422), and a second decision (409)
- [x] Test: steps come back from `get_claim` in the order they were recorded
- [x] By hand with `curl` against the dev server: approve CLM-1001 at $1,250, `pay_claim` returns 409 "Payout over $1,000.00 needs a handler's sign-off"; `sign_off` with HND-01 returns the claim as `decided` with a payment of $1,250.00
- [x] `npm run check:python` passes, coverage at or above 80%

## Phase 3: The UnderCover Agent

Replaces the hello-world agent. `run(claim_id, thread_id)` fetches the instructions, starts the claim, streams the agent and records each step. Tools wrap the six operations listed above. Adds `run_agent` to the backend and `uv run -m agent <claim_id>`. Writes the real instructions: read the claim, policy, history and wording; check dates, waiting periods, limits, deductibles and exclusions; decide; work out the payout; give two or three sentences of reasons and the section; pay when the payout is $1,000 or less.

- [x] Agent tests with a stub model (no model calls): a scripted run reads the claim, records an approval and pays; the claim ends `decided` with a payment, and the steps show each tool call and result
- [x] Stub-model test: an over-limit approval followed by a `pay_claim` call leaves the claim `awaiting_signoff` with no payment, and the agent receives the 409 message as the tool result
- [x] Test: each tool calls only the backend API (via the injected client) and the agent module imports nothing that reads `data/`
- [x] Test: `run_agent` returns a thread id and starts the run in the background (runner stubbed)
- [x] Test: `model()` uses `openai/gpt-6-luna` with low reasoning by default, and `MODEL_NAME` when set
- [x] One live run, with the dev backend up: `uv run -m agent CLM-1001` records a decision with a payout, reasons and a section, and `get_claim` shows the steps (this one call uses the student's OpenRouter key; a few cents, or free with `MODEL_NAME=openrouter/free`)
- [x] `npm run check:python` passes, coverage at or above 80%

## Phase 4: Dashboard pages

Builds the three pages in the brand: the queue, a claim in full and the instructions. Adds the Google Fonts, the color tokens for light and dark mode, and a typed API client. Why separate from Phase 5: these pages are read-only and easy to verify; the live parts come next.

- [x] The queue lists every claim with its id, customer story summary, type, amount claimed in the form $1,250.00, and a status chip: waiting, in progress, waiting for sign-off, decided (Sea Green, Marigold, Coral, Cerulean)
- [x] The queue can be filtered by status, with a count for each
- [x] The claim page shows the story, items, documents, policy and plan, and, once decided, the decision, payout, reasons and policy section; an approval shows whether it is paid or waiting for sign-off
- [x] The instructions page shows the agent's instructions as read-only text, with no edit controls
- [x] Vitest tests for each page with `fetch` stubbed; `npm run check:ts` passes with coverage at or above 80%, strict TypeScript and no `any`
- [x] In the browser with Playwright (a script, as the Playwright MCP server didn't connect this session), at `npm run dev`: the queue shows 25 waiting claims; clicking CLM-1001 opens its page; the instructions page shows the same text as `GET /api/instructions`; the pages render correctly in light and dark mode

## Phase 5: Live runs and sign-off in the dashboard

Adds the "Run agent" button on waiting claims, the step-by-step activity panel (polling every second while in progress, stopping when the run ends), and the sign-off panel with a handler picker on claims waiting for sign-off. Adds Playwright tests. For the end-to-end tests, Playwright starts the backend on its own port with a fresh database (a new temp file per run, set in `playwright.config.ts`) and plays the agent's part by calling the API directly, so no test calls a model.

- [x] Vitest: the steps panel renders tool calls, results and model text in order, and polling stops once the claim leaves `in_progress`
- [x] Vitest: the sign-off panel appears only for claims awaiting sign-off and posts the chosen handler
- [x] Playwright: steps posted to a claim through the API appear on its page within two seconds
- [x] Playwright: a claim approved at $1,250 through the API shows "Waiting for sign-off" in the queue; signing off as Dana Whitfield moves it to decided and shows the payment of $1,250.00
- [x] Playwright: a claim declined through the API shows the decision, reasons and section, and no payment
- [x] `npm run e2e` passes, and the existing health test still passes
- [x] In the browser with Playwright (a script, as the MCP server didn't connect): click "Run agent" on a waiting claim (live model), watch the steps appear, and see the decision when it finishes

## Phase 6: Working the queue and handover

Runs the agent over the queue to check it holds up, fixes what that turns up in the instructions or the code, and finishes the documentation. Scoring against the handlers' decisions is not part of this phase.

- [x] Live runs on at least five claims of different types each end with a recorded decision, two or three sentences of reasons and a policy section, and none crashes; any over $1,000 waits for sign-off with no payment
- [x] `docs/STATUS.md` describes what's built, how to run it (`npm run dev`, `uv run -m agent <claim_id>`, resetting the database) and what's not built
- [x] A short README in `backend/`, `agent/` and `dashboard/` only if needed beyond `docs/STATUS.md` (not needed)
- [x] `npm run check` passes in full: ruff, pyright, pytest at 80%+, Prettier, ESLint, tsc, vitest at 80%+, and Playwright

## Phase 7: After the pilot: running the whole queue, and decisions in the queue

Two changes the student asked for after the pilot was handed over.

**Running every waiting claim from the command line.** Clicking Run agent on many claims at once ran them in parallel, and a new OpenRouter account hit its rate limit. `uv run -m agent --all` (also `npm run agent:all`) runs every waiting claim one after another instead. It reuses `run()` for each claim, so steps, decisions and payments are recorded exactly as from the dashboard. A failed claim is printed and recorded, and the run carries on with the next one.

**The decision and approved amount in the queue.** Handlers wanted to see each claim's outcome without opening it. `list_claims` now returns `decision_kind` (approve, decline, refer, or none yet) and `approved_amount` (the payout for an approval, none otherwise), read from the decisions table. The queue shows them as two new columns, Decision and Approved, next to the amount claimed.

- [x] `uv run -m agent --all` (also `-all` or `all`) runs every waiting claim one at a time, skips claims that aren't waiting, prints each claim's result and a final count, and carries on after a claim's run fails; any other option starting with `-` prints a usage message
- [x] Pytest with a stub model covers `--all`, including a failed claim; no test calls a model
- [x] Live: `npm run agent:all` decided all 25 claims with no errors (15 approved and paid, 3 approved and waiting for sign-off, 6 declined, 3 referred)
- [x] `GET /api/claims` returns `decision_kind` and `approved_amount`: none for an undecided claim, the payout for an approval, and no amount for a decline or referral (pytest)
- [x] The queue has Decision and Approved columns: the decision in its color (Approved, Declined, Referred to a handler) and the approved amount as $1,250.00, or "-" when there is none (vitest)
- [x] Playwright: the claim approved at $1,250 shows Approved and $1,250.00 in its queue row
- [x] In the browser with a Playwright script: the queue shows the new columns in light and dark mode, with no sideways scroll at phone width
- [x] `npm run check` passes in full

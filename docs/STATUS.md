# Status

The claims pilot from `docs/SPEC.md` is built, following `docs/PLAN.md`.

## Built

- `backend/`: FastAPI and SQLite. On startup it creates `backend/undercover.db` (or the file in `UNDERCOVER_DB`) and seeds it from `data/` if it's empty. It reads only the queue's records, never `data/evals/`, `data/security/` or the claims manual.
  - Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history` (earlier claims, no contact details), `get_policy_wording`, `get_instructions`, `list_handlers`.
  - Workflow operations: `run_agent`, `start_claim`, `record_step`, `record_decision`, `pay_claim`, `sign_off`.
  - A claim moves from `waiting` to `in_progress` to `decided`, or to `awaiting_signoff` when an approval is over the $1,000 limit in `data/company.json`. `pay_claim` pays only an approval, only its exact payout, only once, and never over the limit without a sign-off. `sign_off` checks the handler and releases the payment.
  - The agent's instructions are in `backend/instructions.md`, served to the agent and the dashboard alike.
- `agent/`: the UnderCover Agent, `run(claim_id, thread_id)` in `agent/main.py`. It fetches its instructions from the backend, reads the claim, policy, claim history and policy wording through the API, records a decision and pays approvals of $1,000 or less. Each tool call, result and message is recorded as a step on the claim. Tests use a stub model.
- `dashboard/`: React pages for the queue (with status filters and counts), each claim in full with its policy, decision, payment and the agent's steps, and the agent's instructions, read only. A waiting claim has a Run agent button; while the agent works the page refreshes every second. A claim waiting for sign-off has a sign-off panel with a handler picker. Hash routes: `#/`, `#/claims/<id>`, `#/instructions`. Brand colors and fonts in `dashboard/src/styles.css`, with light and dark mode.
- `e2e/`: Playwright tests of the dashboard. They play the agent's part through the API, so they never call a model.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on http://localhost:5173.
- Run the agent from a claim's page, or with `uv run -m agent CLM-1001` while the backend is running. It uses `openai/gpt-6-luna` with low reasoning, or the model in `MODEL_NAME`, through `OPENROUTER_API_KEY` in `.env`.
- `npm run check` runs every check. `npm run e2e` runs the Playwright tests on ports 8001 and 5174 with a new database each run, so they don't touch the dev data.
- To start over with a fresh queue, stop the backend and delete `backend/undercover.db`.

## Known gaps

- If a run fails part way (for example, OpenRouter's rate limit on a new account when several claims run at once), the claim can stay `in_progress`, or stay approved and unpaid, with no way in the dashboard to retry. Delete the database to start over. Run claims one at a time on a new OpenRouter account.
- The agent's decisions have not been scored against the handlers' decisions in `data/evals/`. That comes with the evaluations build.
- Live runs on 9 claims of 7 types gave sensible decisions, payouts and reasons after two changes to the instructions: take ids from the claim, and trip cancellation covers events before the trip.

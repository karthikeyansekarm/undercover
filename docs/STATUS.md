# Status

The claims pilot is being built from `docs/PLAN.md`.

## Built

- `backend/`: FastAPI and SQLite. On startup it creates `backend/undercover.db` (or the file in `UNDERCOVER_DB`) and seeds it from `data/` if it's empty. Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions`, `list_handlers`. Workflow operations: `start_claim`, `record_step`, `record_decision`, `pay_claim` and `sign_off`. A claim moves from `waiting` to `in_progress` to `decided`, or to `awaiting_signoff` when an approval is over the $1,000 limit in `data/company.json`. `pay_claim` refuses an unsigned payment over the limit; `sign_off` releases it. The agent's instructions are in `backend/instructions.md`.
- `agent/`: the UnderCover Agent, `run(claim_id, thread_id)` in `agent/main.py`. It fetches its instructions from the backend, reads the claim, policy, claim history and policy wording through the API, records a decision and pays approvals of $1,000 or less. Each tool call, result and message is recorded as a step on the claim. The backend's `run_agent` operation starts it in the background.
- `dashboard/`: React pages for the queue (with status filters and counts), each claim in full with its policy and decision, and the agent's instructions, read only. Hash routes: `#/`, `#/claims/<id>`, `#/instructions`. A waiting claim has a Run agent button; while the agent works, the claim page refreshes every second and shows each step. A claim waiting for sign-off has a sign-off panel with a handler picker. Brand colors and fonts in `dashboard/src/styles.css`, with light and dark mode.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `uv run -m agent CLM-1001` runs the agent on one claim with the backend running. It uses `openai/gpt-6-luna`, or the model in `MODEL_NAME`, through `OPENROUTER_API_KEY`.
- `npm run e2e` runs the Playwright tests on ports 8001 and 5174 with a new database each run, so they don't touch the dev data.
- To start over with a fresh queue, stop the backend and delete `backend/undercover.db`.

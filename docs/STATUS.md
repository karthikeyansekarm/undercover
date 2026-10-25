# Status

The claims pilot is being built from `docs/PLAN.md`.

## Built

- `backend/`: FastAPI and SQLite. On startup it creates `backend/undercover.db` (or the file in `UNDERCOVER_DB`) and seeds it from `data/` if it's empty. Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions`, `list_handlers`. Workflow operations: `start_claim`, `record_step`, `record_decision`, `pay_claim` and `sign_off`. A claim moves from `waiting` to `in_progress` to `decided`, or to `awaiting_signoff` when an approval is over the $1,000 limit in `data/company.json`. `pay_claim` refuses an unsigned payment over the limit; `sign_off` releases it. The agent's instructions are in `backend/instructions.md`.
- `agent/`: still the hello-world agent.
- `dashboard/`: still the hello-world page.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- To start over with a fresh queue, stop the backend and delete `backend/undercover.db`.

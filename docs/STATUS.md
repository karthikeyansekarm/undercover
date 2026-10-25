# Status

The claims pilot is being built from `docs/PLAN.md`.

## Built

- `backend/`: FastAPI and SQLite. On startup it creates `backend/undercover.db` (or the file in `UNDERCOVER_DB`) and seeds it from `data/` if it's empty. Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions`, `list_handlers`. The agent's instructions are in `backend/instructions.md`.
- `agent/`: still the hello-world agent.
- `dashboard/`: still the hello-world page.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- To start over with a fresh queue, stop the backend and delete `backend/undercover.db`.

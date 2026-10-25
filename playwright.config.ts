import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import { join } from "node:path";

// The tests get their own ports and a new database on every run.
const BACKEND_PORT = "8001";
const DASHBOARD_PORT = "5174";
const database = join(tmpdir(), `undercover-e2e-${String(Date.now())}.db`);

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  use: { baseURL: `http://localhost:${DASHBOARD_PORT}` },
  webServer: [
    {
      command: `uv run -m uvicorn backend.main:app --port ${BACKEND_PORT}`,
      url: `http://127.0.0.1:${BACKEND_PORT}/api/health`,
      env: { UNDERCOVER_DB: database },
      reuseExistingServer: false,
    },
    {
      command: `npx vite dashboard --port ${DASHBOARD_PORT} --strictPort`,
      url: `http://localhost:${DASHBOARD_PORT}`,
      env: { BACKEND_PORT },
      reuseExistingServer: false,
    },
  ],
});

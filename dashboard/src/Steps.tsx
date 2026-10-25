import type { Step } from "./api";

const KIND_LABELS: Record<Step["kind"], string> = {
  tool_call: "Tool call",
  tool_result: "Result",
  message: "Agent",
};

export function Steps({
  steps,
  working,
}: Readonly<{ steps: Step[]; working: boolean }>) {
  return (
    <section className="panel" aria-live="polite">
      <h3>What the agent did</h3>
      {steps.length === 0 && (
        <p className="muted">
          {working ? "The agent is starting..." : "The agent has not run yet."}
        </p>
      )}
      <ol className="steps">
        {steps.map((step) => (
          <li key={step.id} className={`step-${step.kind}`}>
            <span className="step-kind">{KIND_LABELS[step.kind]}</span>{" "}
            <span className="step-text">{step.content}</span>
          </li>
        ))}
      </ol>
      {working && steps.length > 0 && <p className="muted">Working...</p>}
    </section>
  );
}

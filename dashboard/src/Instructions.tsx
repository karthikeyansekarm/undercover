import type { Text } from "./api";
import { useApi } from "./useApi";

export function Instructions() {
  const { data, error } = useApi<Text>("/api/instructions");

  if (error) return <p role="alert">Could not load the instructions.</p>;
  if (!data) return <p>Loading the instructions...</p>;

  return (
    <section className="panel">
      <h2>The agent's instructions</h2>
      <p className="muted">
        Read only. These are the instructions the agent works from.
      </p>
      <pre className="instructions">{data.text}</pre>
    </section>
  );
}

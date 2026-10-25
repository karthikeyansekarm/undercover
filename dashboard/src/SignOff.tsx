import { useState } from "react";
import { post, type Claim, type Handler } from "./api";
import { money } from "./format";
import { useApi } from "./useApi";

export function SignOff({
  claim,
  onDone,
}: Readonly<{ claim: Claim; onDone: () => void }>) {
  const { data: handlers } = useApi<Handler[]>("/api/handlers");
  const [handlerId, setHandlerId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!handlers || !claim.decision) return null;
  const allowed = handlers.filter((h) => h.can_approve_over_limit);

  const signOff = () => {
    setBusy(true);
    post<Claim>(`/api/claims/${claim.claim_id}/sign-off`, {
      handler_id: handlerId,
    })
      .then(onDone)
      .catch(() => {
        setError("The sign-off did not go through.");
        setBusy(false);
      });
  };

  return (
    <section className="panel">
      <h3>Sign-off</h3>
      <p>
        This payout is over the approval limit. A handler must sign off before{" "}
        <span className="mono">{money(claim.decision.payout)}</span> is paid.
      </p>
      <label>
        Handler{" "}
        <select
          value={handlerId}
          onChange={(e) => {
            setHandlerId(e.target.value);
          }}
        >
          <option value="">Choose a handler</option>
          {allowed.map((h) => (
            <option key={h.handler_id} value={h.handler_id}>
              {h.name}
            </option>
          ))}
        </select>
      </label>{" "}
      <button
        type="button"
        className="primary"
        disabled={!handlerId || busy}
        onClick={signOff}
      >
        Sign off and pay
      </button>
      {error && <p role="alert">{error}</p>}
    </section>
  );
}

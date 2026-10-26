import { useCallback, useState } from "react";
import { post, type Claim, type Policy, type RunStarted } from "./api";
import { DECISION_LABELS, label, money } from "./format";
import { StatusChip } from "./Queue";
import { SignOff } from "./SignOff";
import { Steps } from "./Steps";
import { useApi } from "./useApi";

function PolicyPanel({ policyId }: Readonly<{ policyId: string }>) {
  const { data: policy } = useApi<Policy>(`/api/policies/${policyId}`);
  if (!policy) return null;
  return (
    <section className="panel">
      <h3>Policy</h3>
      <dl>
        <dt>Policy</dt>
        <dd className="mono">{policy.policy_id}</dd>
        <dt>Plan</dt>
        <dd>{policy.plan.name}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_ons.map((a) => a.name).join(", ") || "None"}</dd>
        <dt>Bought on</dt>
        <dd className="mono">{policy.purchased_on}</dd>
        <dt>Trip</dt>
        <dd>
          {policy.trip.destination},{" "}
          <span className="mono">
            {policy.trip.departs_on} to {policy.trip.returns_on}
          </span>
        </dd>
        <dt>Trip cost</dt>
        <dd className="mono">{money(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
        <dt>Deductible</dt>
        <dd className="mono">{money(policy.plan.deductible)}</dd>
      </dl>
    </section>
  );
}

function paymentText(claim: Claim): string {
  if (claim.payment)
    return `Paid ${money(claim.payment.amount)} on ${claim.payment.paid_at.slice(0, 10)}`;
  if (claim.status === "awaiting_signoff")
    return "Payment waiting for a handler's sign-off";
  return "Not paid yet";
}

export function DecisionPanel({ claim }: Readonly<{ claim: Claim }>) {
  const { decision } = claim;
  if (!decision) return null;
  return (
    <section className="panel">
      <h3>Decision</h3>
      <p className={`decision decision-${decision.decision}`}>
        {DECISION_LABELS[decision.decision]}
        {decision.decision === "approve" && (
          <span className="mono"> {money(decision.payout)}</span>
        )}
      </p>
      <p>{decision.reasons}</p>
      <p className="muted">Policy section: {decision.policy_section}</p>
      {decision.decision === "approve" && <p>{paymentText(claim)}</p>}
      {decision.signed_off_by && (
        <p className="muted">
          Signed off by <span className="mono">{decision.signed_off_by}</span>
        </p>
      )}
    </section>
  );
}

export function ClaimDetails({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <section className="panel">
      <h3>The claim</h3>
      <p className="muted">
        {label(claim.claim_type)} · {claim.incident_location} · incident on{" "}
        <span className="mono">{claim.incident_date}</span> · submitted on{" "}
        <span className="mono">{claim.submitted_on}</span>
      </p>
      <blockquote className="story">{claim.story}</blockquote>
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Category</th>
            <th className="num">Amount</th>
          </tr>
        </thead>
        <tbody>
          {claim.items.map((item) => (
            <tr key={item.description}>
              <td>{item.description}</td>
              <td>{label(item.category)}</td>
              <td className="num mono">{money(item.amount)}</td>
            </tr>
          ))}
          <tr>
            <th scope="row" colSpan={2}>
              Total claimed
            </th>
            <td className="num mono">{money(claim.amount_claimed)}</td>
          </tr>
        </tbody>
      </table>
      <h3>Documents</h3>
      {claim.documents.map((doc) => (
        <details key={doc.name}>
          <summary>
            {doc.name} <span className="muted">({label(doc.type)})</span>
          </summary>
          <p>{doc.content}</p>
        </details>
      ))}
    </section>
  );
}

// An approval within the limit is decided before the agent pays it.
function awaitingPayment(c: Claim): boolean {
  return (
    c.status === "decided" &&
    c.decision?.decision === "approve" &&
    c.decision.signed_off_by === null &&
    c.payment === null
  );
}

function RunButton({
  claimId,
  onStarted,
}: Readonly<{ claimId: string; onStarted: () => void }>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = () => {
    setBusy(true);
    post<RunStarted>(`/api/claims/${claimId}/run`, {})
      .then(onStarted)
      .catch(() => {
        setError("The agent could not start.");
        setBusy(false);
      });
  };
  return (
    <>
      <button type="button" className="primary" disabled={busy} onClick={run}>
        Run agent
      </button>
      {error && <p role="alert">{error}</p>}
    </>
  );
}

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const [started, setStarted] = useState(false);
  const pollWhile = useCallback(
    (c: Claim) =>
      c.status === "in_progress" ||
      (started && c.status === "waiting") ||
      awaitingPayment(c),
    [started],
  );
  const {
    data: claim,
    error,
    reload,
  } = useApi<Claim>(`/api/claims/${claimId}`, pollWhile);
  const start = useCallback(() => {
    setStarted(true);
  }, []);

  if (error) return <p role="alert">Could not load claim {claimId}.</p>;
  if (!claim) return <p>Loading the claim...</p>;
  const working = pollWhile(claim);

  return (
    <>
      <p>
        <a href="#/">Back to the queue</a>
      </p>
      <header className="claim-header">
        <h2>
          <span className="mono">{claim.claim_id}</span> {claim.summary}
        </h2>
        <StatusChip status={claim.status} />
        {claim.status === "waiting" && !started && (
          <RunButton claimId={claim.claim_id} onStarted={start} />
        )}
      </header>
      <p>{claim.customer_name}</p>
      <div className="columns">
        <div>
          {claim.status === "awaiting_signoff" && (
            <SignOff claim={claim} onDone={reload} />
          )}
          <DecisionPanel claim={claim} />
          <ClaimDetails claim={claim} />
        </div>
        <div>
          <Steps steps={claim.steps} working={working} />
          <PolicyPanel policyId={claim.policy_id} />
        </div>
      </div>
    </>
  );
}

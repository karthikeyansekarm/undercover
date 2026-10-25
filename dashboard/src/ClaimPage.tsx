import type { Claim, Decision, Policy } from "./api";
import { label, money } from "./format";
import { StatusChip } from "./Queue";
import { useApi } from "./useApi";

const DECISION_LABELS: Record<Decision["decision"], string> = {
  approve: "Approved",
  decline: "Declined",
  refer: "Referred to a handler",
};

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

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const { data: claim, error } = useApi<Claim>(`/api/claims/${claimId}`);

  if (error) return <p role="alert">Could not load claim {claimId}.</p>;
  if (!claim) return <p>Loading the claim...</p>;

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
      </header>
      <p>{claim.customer_name}</p>
      <div className="columns">
        <div>
          <DecisionPanel claim={claim} />
          <ClaimDetails claim={claim} />
        </div>
        <div>
          <PolicyPanel policyId={claim.policy_id} />
        </div>
      </div>
    </>
  );
}

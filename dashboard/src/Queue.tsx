import { useState } from "react";
import type { ClaimSummary, Status } from "./api";
import { STATUSES, STATUS_LABELS, label, money } from "./format";
import { useApi } from "./useApi";

const always = () => true;

export function StatusChip({ status }: Readonly<{ status: Status }>) {
  return <span className={`chip chip-${status}`}>{STATUS_LABELS[status]}</span>;
}

export function Queue() {
  const { data: claims, error } = useApi<ClaimSummary[]>(
    "/api/claims",
    always,
    3000,
  );
  const [filter, setFilter] = useState<Status | "all">("all");

  if (error) return <p role="alert">Could not load the queue.</p>;
  if (!claims) return <p>Loading the queue...</p>;

  const count = (status: Status) =>
    claims.filter((c) => c.status === status).length;
  const shown =
    filter === "all" ? claims : claims.filter((c) => c.status === filter);

  return (
    <section className="panel">
      <h2>Claims queue</h2>
      <div className="filters" role="group" aria-label="Filter by status">
        <button
          type="button"
          aria-pressed={filter === "all"}
          onClick={() => {
            setFilter("all");
          }}
        >
          All <span className="count">{claims.length}</span>
        </button>
        {STATUSES.map((status) => (
          <button
            key={status}
            type="button"
            aria-pressed={filter === status}
            onClick={() => {
              setFilter(status);
            }}
          >
            {STATUS_LABELS[status]}{" "}
            <span className="count">{count(status)}</span>
          </button>
        ))}
      </div>
      <table>
        <thead>
          <tr>
            <th>Claim</th>
            <th>Customer</th>
            <th>Type</th>
            <th>Summary</th>
            <th className="num">Claimed</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((claim) => (
            <tr key={claim.claim_id}>
              <td className="mono">
                <a href={`#/claims/${claim.claim_id}`}>{claim.claim_id}</a>
              </td>
              <td>{claim.customer_name}</td>
              <td>{label(claim.claim_type)}</td>
              <td>{claim.summary}</td>
              <td className="num mono">{money(claim.amount_claimed)}</td>
              <td>
                <StatusChip status={claim.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

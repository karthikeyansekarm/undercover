import type { DecisionKind, Status } from "./api";

export const DECISION_LABELS: Record<DecisionKind, string> = {
  approve: "Approved",
  decline: "Declined",
  refer: "Referred to a handler",
};

export const STATUSES: Status[] = [
  "waiting",
  "in_progress",
  "awaiting_signoff",
  "decided",
];

export const STATUS_LABELS: Record<Status, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  awaiting_signoff: "Waiting for sign-off",
  decided: "Decided",
};

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export function money(amount: number): string {
  return dollars.format(amount);
}

export function label(value: string): string {
  const words = value.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

import type { OpportunityStage, RelationshipCertainty } from "@/src/types/opportunities";
import {
  OPPORTUNITY_STAGE_LABELS,
  RELATIONSHIP_CERTAINTY_LABELS,
} from "@/src/features/opportunity-workspace/display-contract";

const DATE_FORMATTER = new Intl.DateTimeFormat("es-CL", {
  dateStyle: "medium",
});

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "No disponible";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "No disponible";
  }
  return DATE_FORMATTER.format(parsed);
}

export function formatMoney(
  amount: number | null | undefined,
  currencyCode: string | null | undefined,
): string {
  if (amount === null || amount === undefined) {
    return "No disponible";
  }
  const currency = currencyCode && currencyCode.length === 3 ? currencyCode : "CLP";
  return new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "No disponible";
  }
  return new Intl.NumberFormat("es-CL").format(value);
}

export function formatStage(stage: OpportunityStage): string {
  return OPPORTUNITY_STAGE_LABELS[stage];
}

export function formatRelationshipCertainty(certainty: RelationshipCertainty): string {
  return RELATIONSHIP_CERTAINTY_LABELS[certainty];
}

export function formatUnavailable(value: string | null | undefined): string {
  return value && value.trim() ? value : "No disponible";
}

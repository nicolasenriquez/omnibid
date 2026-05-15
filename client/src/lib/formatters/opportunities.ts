import type {
  OpportunityAvailability,
  OpportunityStage,
  RelationshipCertainty,
} from "@/src/types/opportunities";
import {
  AVAILABILITY_CAUSE_LABELS,
  OPPORTUNITY_STAGE_LABELS,
  RELATIONSHIP_CERTAINTY_LABELS,
} from "@/src/features/opportunity-workspace/display-contract";

const DATE_FORMATTER = new Intl.DateTimeFormat("es-CL", {
  dateStyle: "medium",
});
const COUNT_FORMATTER = new Intl.NumberFormat("es-CL");
const CURRENCY_FORMATTERS = new Map<string, Intl.NumberFormat>();

function getCurrencyFormatter(currencyCode: string): Intl.NumberFormat {
  const normalizedCurrencyCode = currencyCode.toUpperCase();
  const cached = CURRENCY_FORMATTERS.get(normalizedCurrencyCode);
  if (cached) {
    return cached;
  }

  const formatter = new Intl.NumberFormat("es-CL", {
    style: "currency",
    currency: normalizedCurrencyCode,
    maximumFractionDigits: 0,
  });
  CURRENCY_FORMATTERS.set(normalizedCurrencyCode, formatter);
  return formatter;
}

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
  return getCurrencyFormatter(currency).format(amount);
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "No disponible";
  }
  return COUNT_FORMATTER.format(value);
}

export function formatStage(stage: OpportunityStage): string {
  return OPPORTUNITY_STAGE_LABELS[stage];
}

export function formatRelationshipCertainty(
  certainty: RelationshipCertainty | string | null | undefined,
): string {
  if (!certainty) {
    return RELATIONSHIP_CERTAINTY_LABELS.unconfirmed;
  }
  return (
    RELATIONSHIP_CERTAINTY_LABELS[certainty as RelationshipCertainty] ??
    RELATIONSHIP_CERTAINTY_LABELS.unconfirmed
  );
}

export function formatUnavailable(value: string | null | undefined): string {
  return value && value.trim() ? value : "No disponible";
}

export function formatAvailability(value: OpportunityAvailability | null | undefined): string {
  if (!value) {
    return "No informado por la fuente";
  }
  return AVAILABILITY_CAUSE_LABELS[value] ?? "No informado por la fuente";
}

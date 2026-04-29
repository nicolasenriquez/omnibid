import type { OpportunityStage, RelationshipCertainty } from "@/src/types/opportunities";

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
  switch (stage) {
    case "open":
      return "Abierta";
    case "closing_soon":
      return "Cierra pronto";
    case "closed":
      return "Cerrada";
    case "awarded":
      return "Adjudicada";
    case "revoked_or_suspended":
      return "Revocada o suspendida";
    default:
      return "Sin clasificar";
  }
}

export function formatRelationshipCertainty(certainty: RelationshipCertainty): string {
  switch (certainty) {
    case "high":
      return "Alta";
    case "medium":
      return "Media";
    case "low":
      return "Baja";
    case "none":
      return "Sin evidencia";
    default:
      return "No confirmada";
  }
}

export function formatUnavailable(value: string | null | undefined): string {
  return value && value.trim() ? value : "No disponible";
}

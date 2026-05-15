import type {
  OpportunityAvailability,
  OpportunityStage,
  RelationshipCertainty,
  WorkspaceDataMode,
  WorkspaceTab,
} from "@/src/types/opportunities";

export const WORKSPACE_TAB_LABELS: Record<WorkspaceTab, string> = {
  explorer: "Lista",
  radar: "Radar",
};

export const WORKSPACE_MODE_LABELS: Record<WorkspaceDataMode, string> = {
  abiertas: "Abiertas",
  historicas: "Históricas",
};

export const OPPORTUNITY_STAGE_LABELS: Record<OpportunityStage, string> = {
  open: "Abierta",
  closing_soon: "Cierra pronto",
  closed: "Cerrada",
  awarded: "Adjudicada",
  revoked_or_suspended: "Revocada o suspendida",
  unknown: "Sin clasificar",
};

export const RELATIONSHIP_CERTAINTY_LABELS: Record<RelationshipCertainty, string> = {
  high: "Alta",
  medium: "Media",
  low: "Baja",
  none: "Sin evidencia",
  unconfirmed: "No confirmada",
};

export const PROCUREMENT_TYPE_LABELS = {
  public: "Pública",
  private: "Privada",
  service: "Servicios",
} as const;

export const AVAILABILITY_CAUSE_LABELS: Record<OpportunityAvailability, string> = {
  available: "Disponible",
  not_yet_public: "Aún no publicado",
  not_applicable: "No aplica",
  pending_detail: "Pendiente de detalle",
  not_reported_by_source: "No informado por la fuente",
  pipeline_missing: "Histórico no cargado",
};

export const NOTICE_LEVEL_FIELDS = [
  "externalNoticeCode",
  "title",
  "officialStatus",
  "mpEstadoCodigo",
  "mpEstadoNombre",
  "mpEstadoCanonical",
  "dataSourceKind",
  "availabilityContext",
  "codigoTipo",
  "tipo",
  "tipoConvocatoria",
  "informada",
  "visibilidadMonto",
  "fuenteFinanciamiento",
  "complaintCount",
  "estimatedAmount",
  "currencyCode",
  "publicationDate",
  "closeDate",
  "awardDate",
  "estimatedAwardDate",
  "noticeDescriptionRaw",
  "buyerName",
  "buyerRegion",
  "buyerCommune",
  "contractingUnitName",
  "contractingUnitCode",
] as const;

export const CYCLE_LEVEL_FIELDS = [
  "participantsAvailability",
  "offersAvailability",
  "awardAvailability",
  "purchaseOrderAvailability",
  "descriptionAvailability",
  "lines",
  "offers",
  "purchaseOrders",
  "relationshipSummary",
] as const;

export type OpportunityFieldScope = "notice" | "cycle";

export function getOpportunityFieldScope(fieldName: string): OpportunityFieldScope | null {
  if ((NOTICE_LEVEL_FIELDS as readonly string[]).includes(fieldName)) {
    return "notice";
  }
  if ((CYCLE_LEVEL_FIELDS as readonly string[]).includes(fieldName)) {
    return "cycle";
  }
  return null;
}

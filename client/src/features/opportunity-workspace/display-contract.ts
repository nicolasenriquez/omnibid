import type { OpportunityStage, RelationshipCertainty, WorkspaceTab } from "@/src/types/opportunities";

export const WORKSPACE_TAB_LABELS: Record<WorkspaceTab, string> = {
  explorer: "Explorador",
  radar: "Radar",
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
  public: "Publica",
  private: "Privada",
  service: "Servicios",
} as const;

export const READ_ONLY_ACTION_LABELS = {
  copyCode: "Copiar codigo",
  openNotice: "Abrir licitacion",
  viewDetail: "Abrir detalle",
} as const;

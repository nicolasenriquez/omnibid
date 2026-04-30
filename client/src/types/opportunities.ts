export const OPPORTUNITY_STAGES = [
  "open",
  "closing_soon",
  "closed",
  "awarded",
  "revoked_or_suspended",
  "unknown",
] as const;

export type OpportunityStage = (typeof OPPORTUNITY_STAGES)[number];

export const RELATIONSHIP_CERTAINTIES = [
  "high",
  "medium",
  "low",
  "none",
  "unconfirmed",
] as const;

export type RelationshipCertainty = (typeof RELATIONSHIP_CERTAINTIES)[number];

export type WorkspaceTab = "radar" | "explorer";

export type OpportunitySortField =
  | "close_date"
  | "publication_date"
  | "estimated_amount"
  | "days_remaining";

export type OpportunitySortDirection = "asc" | "desc";
export type ProcurementTypeFilter = "public" | "private" | "service";

export type OpportunitySummaryMetric = {
  key: string;
  label: string;
  value: number | null;
  helper?: string | null;
};

export type OpportunityFilters = {
  q?: string;
  officialStatus?: string;
  stage?: OpportunityStage;
  buyerRegion?: string;
  primaryCategory?: string;
  publicationFrom?: string;
  publicationTo?: string;
  closeFrom?: string;
  closeTo?: string;
  minAmount?: number;
  maxAmount?: number;
  procurementType?: ProcurementTypeFilter;
  lessThan100Utm?: boolean;
  page: number;
  pageSize: number;
  sortBy: OpportunitySortField;
  sortOrder: OpportunitySortDirection;
};

export type OpportunityListItem = {
  noticeId: string;
  externalNoticeCode: string | null;
  title: string;
  officialStatus: string | null;
  derivedStage: OpportunityStage;
  buyerName: string | null;
  buyerRegion: string | null;
  primaryCategory: string | null;
  estimatedAmount: number | null;
  currencyCode: string | null;
  publicationDate: string | null;
  closeDate: string | null;
  daysRemaining: number | null;
  lineCount: number;
  bidCount: number;
  supplierCount: number;
  purchaseOrderCount: number;
};

export type OpportunityKanbanColumn = {
  stage: OpportunityStage;
  label: string;
  total: number;
  opportunities: OpportunityListItem[];
};

export type OpportunityTimelineEvent = {
  key: string;
  label: string;
  date: string | null;
  source: "official" | "derived";
};

export type OpportunityLineEvidence = {
  itemCode: string;
  correlative: string | null;
  productCodeOnu: string | null;
  lineName: string | null;
  lineDescription: string | null;
  category: string | null;
  quantity: number | null;
  unit: string | null;
  offerCount: number | null;
  selectedOfferCount: number | null;
  relatedPurchaseOrderItemCount: number | null;
  relationshipCertainty: RelationshipCertainty;
};

export type OpportunityOfferEvidence = {
  supplierCode: string | null;
  supplierName: string | null;
  offerName: string | null;
  itemCode: string | null;
  offerStatus: string | null;
  offeredAmount: number | null;
  unitPrice: number | null;
  offeredQuantity: number | null;
  currencyCode: string | null;
  isSelected: boolean | null;
  submittedAt: string | null;
};

export type OpportunityPurchaseOrderEvidence = {
  purchaseOrderCode: string;
  purchaseOrderStatus: string | null;
  purchaseOrderCreatedAt: string | null;
  purchaseOrderAmount: number | null;
  currencyCode: string | null;
  purchaseOrderItemId: string | null;
  purchaseOrderItemProductCodeOnu: string | null;
  purchaseOrderItemNetTotal: number | null;
  relationshipCertainty: RelationshipCertainty;
};

export type OpportunityBuyerSnapshot = {
  buyerName: string | null;
  buyerRegion: string | null;
  contractingUnitName: string | null;
  contractingUnitCode: string | null;
};

export type OpportunityDetail = {
  noticeId: string;
  externalNoticeCode: string | null;
  title: string;
  officialStatus: string | null;
  derivedStage: OpportunityStage;
  estimatedAmount: number | null;
  currencyCode: string | null;
  buyer: OpportunityBuyerSnapshot;
  relationshipSummary: RelationshipCertainty;
  timeline: OpportunityTimelineEvent[];
  lines: OpportunityLineEvidence[];
  offers: OpportunityOfferEvidence[];
  purchaseOrders: OpportunityPurchaseOrderEvidence[];
};

export type OpportunityListResponse = {
  items: OpportunityListItem[];
  total: number;
  page: number;
  pageSize: number;
  columns?: OpportunityKanbanColumn[];
};

export type OpportunitySummaryResponse = {
  metrics: OpportunitySummaryMetric[];
};

export type OpportunityWorkspaceQueryState = {
  tab: WorkspaceTab;
  selectedNoticeId: string | null;
  q: string;
  officialStatus: string;
  stage: OpportunityStage | "";
  buyerRegion: string;
  primaryCategory: string;
  publicationFrom: string;
  publicationTo: string;
  closeFrom: string;
  closeTo: string;
  minAmount: string;
  maxAmount: string;
  procurementType: ProcurementTypeFilter | "";
  lessThan100Utm: boolean;
  page: number;
  pageSize: number;
  sortBy: OpportunitySortField;
  sortOrder: OpportunitySortDirection;
};

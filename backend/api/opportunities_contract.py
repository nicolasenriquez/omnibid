from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

OpportunityStage = Literal[
    "open",
    "closing_soon",
    "closed",
    "awarded",
    "revoked_or_suspended",
    "unknown",
]

RelationshipCertainty = Literal["high", "medium", "low", "none", "unconfirmed"]
OpportunityAvailability = Literal[
    "available",
    "not_yet_public",
    "not_applicable",
    "not_reported_by_source",
    "pipeline_missing",
]


class OpportunitySummaryMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    value: int | float | None
    helper: str | None = None


class OpportunitySummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metrics: list[OpportunitySummaryMetric]


class OpportunityListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    noticeId: str
    externalNoticeCode: str | None
    title: str | None
    officialStatus: str | None
    mpEstadoCodigo: int | None
    mpEstadoNombre: str | None
    mpEstadoCanonical: str | None
    dataSourceKind: str | None
    availabilityContext: str | None
    codigoTipo: str | None
    tipo: str | None
    tipoConvocatoria: str | None
    informada: str | None
    visibilidadMonto: str | None
    fuenteFinanciamiento: str | None
    derivedStage: OpportunityStage
    estimatedAmount: float | None
    currencyCode: str | None
    publicationDate: str | None
    closeDate: str | None
    lineCount: int | None
    bidCount: int | None
    supplierCount: int | None
    purchaseOrderCount: int | None
    buyerName: str | None
    buyerRegion: str | None
    buyerCommune: str | None
    primaryCategory: str | None
    procurementType: str | None
    isLessThan100Utm: bool | None
    daysRemaining: int | None


class OpportunityListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[OpportunityListItem]
    total: int
    page: int
    pageSize: int


class OpportunityTimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    date: str | None
    source: Literal["official", "derived"]


class OpportunityLineEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itemCode: str
    correlative: int | None
    productCodeOnu: str | None
    lineName: str | None
    lineDescription: str | None
    category: str | None
    quantity: float | None
    unit: str | None
    offerCount: int | None
    selectedOfferCount: int | None
    supplierCount: int | None
    relatedPurchaseOrderItemCount: int | None
    relationshipCertainty: RelationshipCertainty


class OpportunityOfferEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplierCode: str | None
    supplierName: str | None
    offerName: str | None
    itemCode: str | None
    offerStatus: str | None
    offeredAmount: float | None
    unitPrice: float | None
    offeredQuantity: float | None
    currencyCode: str | None
    isSelected: bool | None
    submittedAt: str | None


class OpportunityPurchaseOrderEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purchaseOrderCode: str
    purchaseOrderStatus: str | None
    purchaseOrderCreatedAt: str | None
    purchaseOrderAmount: float | None
    currencyCode: str | None
    purchaseOrderItemId: str | None
    purchaseOrderItemProductCodeOnu: str | None
    purchaseOrderItemNetTotal: float | None
    relationshipCertainty: RelationshipCertainty


class OpportunityBuyerSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buyerName: str | None
    buyerRegion: str | None
    buyerCommune: str | None
    contractingUnitName: str | None
    contractingUnitCode: str | None


class OpportunityDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    noticeId: str
    externalNoticeCode: str | None
    title: str | None
    officialStatus: str | None
    mpEstadoCodigo: int | None
    mpEstadoNombre: str | None
    mpEstadoCanonical: str | None
    dataSourceKind: str | None
    availabilityContext: str | None
    codigoTipo: str | None
    tipo: str | None
    tipoConvocatoria: str | None
    informada: str | None
    visibilidadMonto: str | None
    fuenteFinanciamiento: str | None
    derivedStage: OpportunityStage
    estimatedAmount: float | None
    currencyCode: str | None
    participantsAvailability: OpportunityAvailability
    offersAvailability: OpportunityAvailability
    awardAvailability: OpportunityAvailability
    purchaseOrderAvailability: OpportunityAvailability
    descriptionAvailability: OpportunityAvailability
    buyer: OpportunityBuyerSnapshot
    relationshipSummary: RelationshipCertainty
    timeline: list[OpportunityTimelineEvent]
    lines: list[OpportunityLineEvidence]
    offers: list[OpportunityOfferEvidence]
    purchaseOrders: list[OpportunityPurchaseOrderEvidence]

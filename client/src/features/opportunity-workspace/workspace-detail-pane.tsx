"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Copy, ExternalLink, X } from "lucide-react";

import {
  formatCount,
  formatDate,
  formatMoney,
  formatRelationshipCertainty,
  formatStage,
  formatUnavailable,
} from "@/src/lib/formatters/opportunities";
import type { OpportunityDetail, WorkspaceTab } from "@/src/types/opportunities";
import {
  Button,
  DetailSection,
  IconButton,
  Select,
  Skeleton,
} from "@/src/components/ui";

type RemoteDetailState =
  | { status: "idle" | "loading" }
  | { status: "success"; data: OpportunityDetail }
  | { status: "error"; message: string; statusCode: number | null };

type OfferControls = {
  noticeId: string | null;
  viewMode: "summary" | "all";
  itemFilter: string;
};

type CopyFeedback = {
  noticeId: string;
  message: string;
};

const CHILECOMPRA_NOTICE_URL =
  "https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx";

function buildChileCompraNoticeUrl(externalNoticeCode: string | null): string | null {
  if (!externalNoticeCode) {
    return null;
  }
  const code = externalNoticeCode.trim();
  if (!code) {
    return null;
  }
  return `${CHILECOMPRA_NOTICE_URL}?idlicitacion=${encodeURIComponent(code)}`;
}

function NoDataState({
  title,
  description,
  isError = false,
  statusCode,
  action,
}: {
  title: string;
  description: string;
  isError?: boolean;
  statusCode?: number | null;
  action?: React.ReactNode;
}) {
  return (
    <div
      className={isError ? "state-block state-block--error" : "state-block"}
      role={isError ? "alert" : "status"}
    >
      <div className="state-block__header">
        {isError ? <AlertTriangle size={18} aria-hidden="true" /> : null}
        <strong>{title}</strong>
        {statusCode ? <span className="state-block__code">{`HTTP ${statusCode}`}</span> : null}
      </div>
      <p className="state-block__description">{description}</p>
      {action ? <div className="state-actions">{action}</div> : null}
    </div>
  );
}

export function WorkspaceDetailPane({
  selectedNoticeId,
  tab,
  detailState,
  onClose,
  onRetry,
  onCopyNoticeCode,
}: {
  selectedNoticeId: string | null;
  tab: WorkspaceTab;
  detailState: RemoteDetailState;
  onClose: () => void;
  onRetry: () => void;
  onCopyNoticeCode: (externalNoticeCode: string | null) => Promise<boolean> | boolean;
}) {
  const [offerControls, setOfferControls] = useState<OfferControls>({
    noticeId: null,
    viewMode: "summary",
    itemFilter: "all",
  });
  const [copyFeedback, setCopyFeedback] = useState<CopyFeedback | null>(null);

  const orderedOffers = useMemo(() => {
    if (detailState.status !== "success") {
      return [];
    }

    return [...detailState.data.offers].sort((left, right) => {
      const leftSelected = left.isSelected ? 1 : 0;
      const rightSelected = right.isSelected ? 1 : 0;
      if (leftSelected !== rightSelected) {
        return rightSelected - leftSelected;
      }

      const leftAmount = left.offeredAmount ?? Number.POSITIVE_INFINITY;
      const rightAmount = right.offeredAmount ?? Number.POSITIVE_INFINITY;
      if (leftAmount !== rightAmount) {
        return leftAmount - rightAmount;
      }

      return formatUnavailable(left.supplierName).localeCompare(
        formatUnavailable(right.supplierName),
      );
    });
  }, [detailState]);

  const offerLineOptions = useMemo(() => {
    const byItemCode = new Map<string, number>();
    for (const offer of orderedOffers) {
      const itemCode =
        offer.itemCode && offer.itemCode.trim() ? offer.itemCode.trim() : "Sin item";
      byItemCode.set(itemCode, (byItemCode.get(itemCode) ?? 0) + 1);
    }
    return Array.from(byItemCode.entries())
      .map(([itemCode, count]) => ({ itemCode, count }))
      .sort((left, right) => left.itemCode.localeCompare(right.itemCode));
  }, [orderedOffers]);

  const activeOfferControls =
    offerControls.noticeId === selectedNoticeId
      ? offerControls
      : {
          noticeId: selectedNoticeId,
          viewMode: "summary" as const,
          itemFilter: "all",
        };

  const filteredOffers = useMemo(() => {
    if (activeOfferControls.itemFilter === "all") {
      return orderedOffers;
    }
    return orderedOffers.filter((offer) => {
      const itemCode =
        offer.itemCode && offer.itemCode.trim() ? offer.itemCode.trim() : "Sin item";
      return itemCode === activeOfferControls.itemFilter;
    });
  }, [activeOfferControls.itemFilter, orderedOffers]);

  const visibleOffers = useMemo(
    () =>
      activeOfferControls.viewMode === "all"
        ? filteredOffers
        : filteredOffers.slice(0, 5),
    [activeOfferControls.viewMode, filteredOffers],
  );

  const selectedOffersCount = useMemo(
    () => filteredOffers.filter((offer) => Boolean(offer.isSelected)).length,
    [filteredOffers],
  );

  useEffect(() => {
    if (!copyFeedback) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setCopyFeedback(null);
    }, 2400);

    return () => window.clearTimeout(timeoutId);
  }, [copyFeedback]);

  if (!selectedNoticeId) {
    return null;
  }

  return (
    <aside className="workspace-detail" aria-label="Detalle de licitación">
      <header className="workspace-detail__header">
        <div>
          <strong>Detalle de licitación</strong>
          <span>{tab === "radar" ? "Origen: Radar" : "Origen: Lista"}</span>
        </div>
        <IconButton
          icon={<X size={15} aria-hidden="true" />}
          label="Cerrar detalle"
          onClick={onClose}
          disabled={!selectedNoticeId}
        />
      </header>

      {detailState.status === "loading" ? (
        <div className="workspace-detail__loading">
          <Skeleton height="1rem" />
          <Skeleton height="1rem" />
          <Skeleton height="8rem" />
          <Skeleton height="8rem" />
        </div>
      ) : null}

      {detailState.status === "error" ? (
        <div className="workspace-detail__body">
          <NoDataState
            title={detailState.statusCode === 404 ? "Detalle no disponible" : "Error de detalle"}
            description={detailState.message}
            isError
            action={
              <Button
                leadingIcon={<AlertTriangle size={15} aria-hidden="true" />}
                onClick={onRetry}
              >
                Reintentar
              </Button>
            }
          />
        </div>
      ) : null}

      {detailState.status === "success" ? (
        <>
          <div className="workspace-detail__actions" aria-label="Acciones de solo lectura">
            <Button
              leadingIcon={<Copy size={15} aria-hidden="true" />}
              onClick={async () => {
                try {
                  const copied = await onCopyNoticeCode(detailState.data.externalNoticeCode);
                  setCopyFeedback({
                    noticeId: selectedNoticeId ?? "",
                    message: copied
                      ? "Código copiado al portapapeles."
                      : "No se pudo copiar el código.",
                  });
                } catch {
                  setCopyFeedback({
                    noticeId: selectedNoticeId ?? "",
                    message: "No se pudo copiar el código.",
                  });
                }
              }}
              disabled={!detailState.data.externalNoticeCode}
            >
              Copiar código
            </Button>
            {buildChileCompraNoticeUrl(detailState.data.externalNoticeCode) ? (
              <Button
                leadingIcon={<ExternalLink size={15} aria-hidden="true" />}
                onClick={() => {
                  const url = buildChileCompraNoticeUrl(detailState.data.externalNoticeCode);
                  if (url) {
                    window.open(url, "_blank", "noopener,noreferrer");
                  }
                }}
              >
                Abrir licitación
              </Button>
            ) : null}
            {copyFeedback && copyFeedback.noticeId === selectedNoticeId ? (
              <span className="workspace-detail__copy-feedback" role="status" aria-live="polite">
                {copyFeedback.message}
              </span>
            ) : null}
          </div>

          <DetailSection title="Resumen">
            <strong>{formatUnavailable(detailState.data.externalNoticeCode)}</strong>
            <span>{detailState.data.title}</span>
            <span>{`Estado oficial: ${formatUnavailable(detailState.data.officialStatus)}`}</span>
            <span>{`Etapa: ${formatStage(detailState.data.derivedStage)}`}</span>
            <span>
              {`Monto estimado: ${formatMoney(
                detailState.data.estimatedAmount,
                detailState.data.currencyCode,
              )}`}
            </span>
            <span>{`Comprador: ${formatUnavailable(detailState.data.buyer.buyerName)}`}</span>
          </DetailSection>

          <DetailSection title="Línea de tiempo">
            {detailState.data.timeline.length === 0 ? (
              <span>No disponible</span>
            ) : (
              detailState.data.timeline.map((event) => (
                <span key={event.key}>{`${event.label}: ${formatDate(event.date)}`}</span>
              ))
            )}
          </DetailSection>

          <DetailSection title="Productos o servicios">
            {detailState.data.lines.length === 0 ? (
              <span>Sin información disponible.</span>
            ) : (
              detailState.data.lines.slice(0, 5).map((line) => (
                <article key={line.itemCode} className="detail-line-card">
                  <strong>{`Ítem ${line.itemCode}`}</strong>
                  <div>{formatUnavailable(line.lineName)}</div>
                  <div>{`Categoría: ${formatUnavailable(line.category)}`}</div>
                  <div>{`Ofertas: ${formatCount(line.offerCount)}`}</div>
                  <div>{`Certeza: ${formatRelationshipCertainty(line.relationshipCertainty)}`}</div>
                </article>
              ))
            )}
          </DetailSection>

          <DetailSection title="Comprador">
            <span>{`Nombre: ${formatUnavailable(detailState.data.buyer.buyerName)}`}</span>
            <span>{`Región: ${formatUnavailable(detailState.data.buyer.buyerRegion)}`}</span>
            <span>{`Unidad: ${formatUnavailable(detailState.data.buyer.contractingUnitName)}`}</span>
          </DetailSection>

          <DetailSection title="Económico y evidencia">
            <span>{`Ofertas: ${formatCount(detailState.data.offers.length)}`}</span>
            <span>{`Órdenes de compra: ${formatCount(detailState.data.purchaseOrders.length)}`}</span>
            <span>
              {`Certeza de relación: ${formatRelationshipCertainty(
                detailState.data.relationshipSummary,
              )}`}
            </span>
          </DetailSection>

          <DetailSection title="Ofertas">
            {orderedOffers.length === 0 ? (
              <span>Sin ofertas disponibles en la API.</span>
            ) : (
              <>
                <div className="detail-offers-summary">
                  <span>{`${formatCount(filteredOffers.length)} ofertas visibles`}</span>
                  <span>{`${formatCount(selectedOffersCount)} ganadora(s)`}</span>
                </div>
                <div className="detail-offers-toolbar">
                  <Select
                    value={activeOfferControls.itemFilter}
                    onChange={(event) =>
                      setOfferControls({
                        noticeId: selectedNoticeId,
                        viewMode: activeOfferControls.viewMode,
                        itemFilter: event.target.value,
                      })
                    }
                  >
                    <option value="all">Todas las líneas</option>
                    {offerLineOptions.map((option) => (
                      <option key={option.itemCode} value={option.itemCode}>
                        {`Ítem ${option.itemCode} (${formatCount(option.count)})`}
                      </option>
                    ))}
                  </Select>
                  <Button
                    variant="ghost"
                    onClick={() =>
                      setOfferControls({
                        noticeId: selectedNoticeId,
                        itemFilter: activeOfferControls.itemFilter,
                        viewMode:
                          activeOfferControls.viewMode === "all" ? "summary" : "all",
                      })
                    }
                  >
                    {activeOfferControls.viewMode === "all" ? "Ver resumen" : "Ver todas"}
                  </Button>
                </div>
                {visibleOffers.map((offer, index) => (
                  <article
                    key={`${offer.supplierCode ?? "proveedor"}-${index}`}
                    className={
                      offer.isSelected
                        ? "detail-offer-card detail-offer-card--selected"
                        : "detail-offer-card"
                    }
                  >
                    <header>
                      <strong>{formatUnavailable(offer.supplierName)}</strong>
                      <span
                        className={
                          offer.isSelected
                            ? "detail-offer-chip detail-offer-chip--winner"
                            : "detail-offer-chip"
                        }
                      >
                        {offer.isSelected ? "Ganadora" : "Oferta"}
                      </span>
                    </header>
                    <div>{formatUnavailable(offer.offerName)}</div>
                    <dl>
                      <div>
                        <dt>Monto</dt>
                        <dd>{formatMoney(offer.offeredAmount, offer.currencyCode)}</dd>
                      </div>
                      <div>
                        <dt>Unitario</dt>
                        <dd>{formatMoney(offer.unitPrice, offer.currencyCode)}</dd>
                      </div>
                      <div>
                        <dt>Cantidad</dt>
                        <dd>{formatCount(offer.offeredQuantity)}</dd>
                      </div>
                      <div>
                        <dt>Estado</dt>
                        <dd>{formatUnavailable(offer.offerStatus)}</dd>
                      </div>
                      <div>
                        <dt>Ítem</dt>
                        <dd>{formatUnavailable(offer.itemCode)}</dd>
                      </div>
                      <div>
                        <dt>Envío</dt>
                        <dd>{formatDate(offer.submittedAt)}</dd>
                      </div>
                    </dl>
                  </article>
                ))}
                {activeOfferControls.viewMode === "summary" &&
                filteredOffers.length > visibleOffers.length ? (
                  <span className="detail-offers-footnote">
                    {`Mostrando 5 de ${formatCount(filteredOffers.length)} ofertas.`}
                  </span>
                ) : null}
              </>
            )}
          </DetailSection>

          <DetailSection title="Órdenes de compra">
            {detailState.data.purchaseOrders.length === 0 ? (
              <span>Sin órdenes de compra disponibles en la API.</span>
            ) : (
              detailState.data.purchaseOrders.slice(0, 5).map((order) => (
                <article key={order.purchaseOrderCode} className="detail-line-card">
                  <strong>{order.purchaseOrderCode}</strong>
                  <div>{`Estado: ${formatUnavailable(order.purchaseOrderStatus)}`}</div>
                  <div>
                    {`Monto: ${formatMoney(order.purchaseOrderAmount, order.currencyCode)}`}
                  </div>
                  <div>{`Certeza: ${formatRelationshipCertainty(order.relationshipCertainty)}`}</div>
                </article>
              ))
            )}
          </DetailSection>

          <DetailSection title="Metadatos">
            <span>{`Identificador interno: ${detailState.data.noticeId}`}</span>
            <span>{`Código externo: ${formatUnavailable(detailState.data.externalNoticeCode)}`}</span>
            <span>Fuente: API de oportunidades en modo lectura.</span>
          </DetailSection>
        </>
      ) : null}
    </aside>
  );
}

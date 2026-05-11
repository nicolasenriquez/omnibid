"use client";

import { Fragment, useEffect, useMemo, useRef, type RefObject } from "react";
import {
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Star,
} from "lucide-react";

import {
  formatCount,
  formatDate,
  formatMoney,
  formatRelationshipCertainty,
  formatStage,
  formatUnavailable,
} from "@/src/lib/formatters/opportunities";
import type {
  OpportunityListItem,
  OpportunitySortDirection,
  OpportunitySortField,
  OpportunityStage,
} from "@/src/types/opportunities";
import {
  Button,
  Chip,
  IconButton,
  Table,
  TableWrap,
} from "@/src/components/ui";

function stageClassName(stage: OpportunityStage): string {
  switch (stage) {
    case "open":
      return "status-chip status-chip--open";
    case "closing_soon":
      return "status-chip status-chip--closing-soon";
    case "closed":
      return "status-chip status-chip--closed";
    case "awarded":
      return "status-chip status-chip--awarded";
    case "revoked_or_suspended":
      return "status-chip status-chip--revoked-or-suspended";
    default:
      return "status-chip status-chip--unknown";
  }
}

function opportunityCardClassName(
  item: OpportunityListItem,
  selectedNoticeId: string | null,
): string {
  const classes = ["opportunity-card", `opportunity-card--${item.derivedStage}`];
  if (item.noticeId === selectedNoticeId) {
    classes.push("opportunity-card--selected");
  }
  return classes.join(" ");
}

function SortHeader({
  label,
  active = false,
  sortOrder,
}: {
  label: string;
  active?: boolean;
  sortOrder?: "asc" | "desc";
}) {
  return (
    <span className={active ? "table-sort table-sort--active" : "table-sort"}>
      <span>{label}</span>
      {active ? (
        <ChevronDown
          className={sortOrder === "asc" ? "table-sort__icon table-sort__icon--ascending" : "table-sort__icon"}
          size={13}
          aria-hidden="true"
        />
      ) : null}
    </span>
  );
}

function NoDataState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="state-block" role="status">
      <div className="state-block__header">
        <strong>{title}</strong>
      </div>
      <p className="state-block__description">{description}</p>
    </div>
  );
}

export function WorkspaceRadarBoard({
  radarColumns,
  selectedNoticeId,
  onOpenDetail,
}: {
  radarColumns: Array<{
    stage: OpportunityStage;
    label: string;
    items: OpportunityListItem[];
  }>;
  selectedNoticeId: string | null;
  onOpenDetail: (noticeId: string) => void;
}) {
  return (
    <section className="radar-board" aria-label="Radar de oportunidades">
      {radarColumns.map((column) => (
        <article key={column.stage} className="radar-column">
          <header className="radar-column__header">
            <div>
              <strong>{column.label}</strong>
              <span>Etapa derivada</span>
            </div>
            <Chip>{formatCount(column.items.length)}</Chip>
          </header>
          <div className="radar-column__list">
            {column.items.length === 0 ? (
              <NoDataState title="Sin tarjetas" description="No hay oportunidades para esta etapa." />
            ) : null}
            {column.items.map((item) => (
              <button
                key={item.noticeId}
                type="button"
                className={opportunityCardClassName(item, selectedNoticeId)}
                onClick={() => onOpenDetail(item.noticeId)}
              >
                <h3 className="opportunity-card__title">
                  <span>{formatUnavailable(item.externalNoticeCode)}</span>
                  {item.title}
                </h3>
                <div className="opportunity-card__meta">
                  <span className={stageClassName(item.derivedStage)}>
                    {formatStage(item.derivedStage)}
                  </span>
                  <span>{formatUnavailable(item.buyerName)}</span>
                  <span>{formatDate(item.closeDate)}</span>
                  <span>{formatMoney(item.estimatedAmount, item.currencyCode)}</span>
                </div>
                <div className="opportunity-card__evidence">
                  <span>{`${formatCount(item.lineCount)} líneas`}</span>
                  <span>{`${formatCount(item.bidCount)} ofertas`}</span>
                  <span>{`${formatCount(item.purchaseOrderCount)} OC`}</span>
                </div>
              </button>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}

export function WorkspaceExplorerTable({
  listItems,
  selectedNoticeId,
  expandedNoticeId,
  watchlistNoticeIds,
  selectedNoticeIds,
  sortBy,
  sortOrder,
  onSort,
  onOpenDetail,
  onToggleExpanded,
  onToggleWatchlistNotice,
  onToggleSelectedNotice,
  onToggleAllSelectedNotices,
  onClearSelectedNoticeIds,
  onAddSelectedToWatchlist,
  onRemoveSelectedFromWatchlist,
  explorerLoadMoreRef,
  isLoadingMoreExplorer,
  loadMoreErrorMessage,
  onRetryLoadMore,
  canAutoLoadMore,
}: {
  listItems: OpportunityListItem[];
  selectedNoticeId: string | null;
  expandedNoticeId: string | null;
  watchlistNoticeIds: string[];
  selectedNoticeIds: string[];
  sortBy: OpportunitySortField;
  sortOrder: OpportunitySortDirection;
  onSort: (field: OpportunitySortField) => void;
  onOpenDetail: (noticeId: string) => void;
  onToggleExpanded: (noticeId: string) => void;
  onToggleWatchlistNotice: (noticeId: string) => void;
  onToggleSelectedNotice: (noticeId: string) => void;
  onToggleAllSelectedNotices: (checked: boolean) => void;
  onClearSelectedNoticeIds: () => void;
  onAddSelectedToWatchlist: () => void;
  onRemoveSelectedFromWatchlist: () => void;
  explorerLoadMoreRef: RefObject<HTMLDivElement | null>;
  isLoadingMoreExplorer: boolean;
  loadMoreErrorMessage: string | null;
  onRetryLoadMore: () => void;
  canAutoLoadMore: boolean;
}) {
  const selectedNoticeIdSet = useMemo(() => new Set(selectedNoticeIds), [selectedNoticeIds]);
  const watchlistNoticeIdSet = useMemo(() => new Set(watchlistNoticeIds), [watchlistNoticeIds]);
  const selectAllRef = useRef<HTMLInputElement | null>(null);
  const allVisibleSelected = listItems.length > 0 && selectedNoticeIds.length === listItems.length;
  const selectedInRadarCount = selectedNoticeIds.filter((noticeId) =>
    watchlistNoticeIdSet.has(noticeId),
  ).length;
  const selectedOutsideRadarCount = selectedNoticeIds.length - selectedInRadarCount;

  useEffect(() => {
    if (!selectAllRef.current) {
      return;
    }
    selectAllRef.current.indeterminate =
      selectedNoticeIds.length > 0 && selectedNoticeIds.length < listItems.length;
  }, [listItems.length, selectedNoticeIds.length]);

  return (
    <>
      {selectedNoticeIds.length > 0 ? (
        <div className="workspace-bulk-actions" aria-label="Acciones masivas de la tabla">
          <Chip className="workspace-bulk-actions__count">
            {selectedNoticeIds.length === 1
              ? "1 licitación seleccionada"
              : `${selectedNoticeIds.length} licitaciones seleccionadas`}
          </Chip>
          <Button
            variant="primary"
            disabled={selectedOutsideRadarCount === 0}
            onClick={onAddSelectedToWatchlist}
          >
            Agregar al radar
          </Button>
          <Button
            variant="ghost"
            disabled={selectedInRadarCount === 0}
            onClick={onRemoveSelectedFromWatchlist}
          >
            Quitar del radar
          </Button>
          <Button variant="ghost" onClick={onClearSelectedNoticeIds}>
            Limpiar selección
          </Button>
        </div>
      ) : null}
      <TableWrap>
        <Table aria-label="Tabla de licitaciones">
          <thead>
            <tr>
              <th scope="col" className="ui-table-cell-select">
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  className="table-select-all__checkbox"
                  aria-label="Seleccionar todas las licitaciones cargadas"
                  checked={allVisibleSelected}
                  onChange={(event) => onToggleAllSelectedNotices(event.target.checked)}
                />
              </th>
              <th scope="col"><span className="sr-only">Expandir</span></th>
              <th scope="col"><SortHeader label="Código" /></th>
              <th scope="col"><SortHeader label="Licitación" /></th>
              <th scope="col"><SortHeader label="Comprador" /></th>
              <th scope="col"><SortHeader label="Región" /></th>
              <th scope="col"><SortHeader label="Estado" /></th>
              <th scope="col"><span className="table-label">Etapa</span></th>
              <th
                scope="col"
                aria-sort={sortBy === "estimated_amount" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}
                onClick={() => onSort("estimated_amount")}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSort("estimated_amount");
                  }
                }}
                tabIndex={0}
                className="table-sort-header table-sort-header--interactive"
              >
                <SortHeader
                  label="Monto"
                  active={sortBy === "estimated_amount"}
                  sortOrder={sortOrder}
                />
              </th>
              <th
                scope="col"
                aria-sort={sortBy === "close_date" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}
                onClick={() => onSort("close_date")}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onSort("close_date");
                  }
                }}
                tabIndex={0}
                className="table-sort-header table-sort-header--interactive"
              >
                <SortHeader
                  label="Cierre"
                  active={sortBy === "close_date"}
                  sortOrder={sortOrder}
                />
              </th>
              <th scope="col"><SortHeader label="Líneas" /></th>
              <th scope="col"><SortHeader label="Ofertas" /></th>
              <th scope="col"><SortHeader label="OC" /></th>
              <th scope="col"><span className="table-label">Radar</span></th>
            </tr>
          </thead>
          <tbody>
            {listItems.map((item) => {
              const isExpanded = expandedNoticeId === item.noticeId;
              const isWatchlisted = watchlistNoticeIdSet.has(item.noticeId);
              const isSelected = selectedNoticeIdSet.has(item.noticeId);
              return (
                <Fragment key={item.noticeId}>
                  <tr
                    key={item.noticeId}
                    className={
                      isSelected
                        ? item.noticeId === selectedNoticeId
                          ? "ui-table-row-active ui-table-row-selected"
                          : "ui-table-row-selected"
                        : item.noticeId === selectedNoticeId
                          ? "ui-table-row-active"
                          : undefined
                    }
                  >
                    <td className="ui-table-cell-select">
                      <input
                        type="checkbox"
                        className="table-row-select__checkbox"
                        aria-label={`Seleccionar ${item.title}`}
                        checked={isSelected}
                        onChange={() => onToggleSelectedNotice(item.noticeId)}
                      />
                    </td>
                    <td className="ui-table-cell-control">
                      <IconButton
                        icon={
                          isExpanded ? (
                            <ChevronDown size={14} aria-hidden="true" />
                          ) : (
                            <ChevronRight size={14} aria-hidden="true" />
                          )
                        }
                        label={isExpanded ? "Contraer licitación" : "Expandir licitación"}
                        aria-expanded={isExpanded}
                        onClick={() => onToggleExpanded(item.noticeId)}
                      />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="ui-table-row-button"
                        onClick={() => onOpenDetail(item.noticeId)}
                      >
                        {formatUnavailable(item.externalNoticeCode)}
                      </button>
                    </td>
                    <td className="ui-table-title-cell">
                      <button
                        type="button"
                        className="ui-table-row-button"
                        title={item.title}
                        onClick={() => onOpenDetail(item.noticeId)}
                      >
                        {item.title}
                      </button>
                    </td>
                    <td>{formatUnavailable(item.buyerName)}</td>
                    <td>{formatUnavailable(item.buyerRegion)}</td>
                    <td>{formatUnavailable(item.officialStatus)}</td>
                    <td>
                      <span className={stageClassName(item.derivedStage)}>
                        {formatStage(item.derivedStage)}
                      </span>
                    </td>
                    <td className="ui-table-number">
                      {formatMoney(item.estimatedAmount, item.currencyCode)}
                    </td>
                    <td>{formatDate(item.closeDate)}</td>
                    <td className="ui-table-number">{formatCount(item.lineCount)}</td>
                    <td className="ui-table-number">{formatCount(item.bidCount)}</td>
                    <td className="ui-table-number">{formatCount(item.purchaseOrderCount)}</td>
                    <td className="ui-table-cell-watchlist">
                      <IconButton
                        icon={
                          <Star
                            size={14}
                            aria-hidden="true"
                            fill={isWatchlisted ? "currentColor" : "none"}
                          />
                        }
                        className={
                          isWatchlisted
                            ? "table-watchlist-button table-watchlist-button--active"
                            : "table-watchlist-button"
                        }
                        label={
                          isWatchlisted
                            ? "Quitar licitación del radar"
                            : "Agregar licitación al radar"
                        }
                        onClick={() => onToggleWatchlistNotice(item.noticeId)}
                      />
                    </td>
                  </tr>
                  {isExpanded ? (
                    <tr key={`${item.noticeId}-expanded`} className="ui-table-expanded-row">
                      <td colSpan={14}>
                        <div className="table-evidence-panel">
                          <div className="table-evidence-panel__hero">
                            <div className="table-evidence-panel__hero-copy">
                              <span className="evidence-label">Ficha resumida</span>
                              <strong>{item.title}</strong>
                              <p>
                                {formatUnavailable(item.buyerName)} ·{" "}
                                {formatUnavailable(item.externalNoticeCode)}
                              </p>
                            </div>
                            <div className="table-evidence-panel__hero-badges">
                              <span className={stageClassName(item.derivedStage)}>
                                {formatStage(item.derivedStage)}
                              </span>
                              <span className="ui-chip">
                                {item.daysRemaining === null
                                  ? "Cerrada o sin fecha"
                                  : `${formatCount(item.daysRemaining)} días`}
                              </span>
                            </div>
                          </div>
                          <div className="table-evidence-panel__summary">
                            <div className="table-evidence-panel__fact">
                              <span className="evidence-label">Categoría</span>
                              <strong>{formatUnavailable(item.primaryCategory)}</strong>
                            </div>
                            <div className="table-evidence-panel__fact">
                              <span className="evidence-label">Publicación</span>
                              <strong>{formatDate(item.publicationDate)}</strong>
                            </div>
                            <div className="table-evidence-panel__fact">
                              <span className="evidence-label">Cierre</span>
                              <strong>{formatDate(item.closeDate)}</strong>
                            </div>
                            <div className="table-evidence-panel__fact">
                              <span className="evidence-label">Días restantes</span>
                              <strong>
                                {item.daysRemaining === null
                                  ? "Cerrada o sin fecha"
                                  : formatCount(item.daysRemaining)}
                              </strong>
                            </div>
                            <div className="table-evidence-panel__fact">
                              <span className="evidence-label">Certeza de relación</span>
                              <strong>{formatRelationshipCertainty("unconfirmed")}</strong>
                            </div>
                            <div className="table-evidence-panel__fact">
                              <span className="evidence-label">Monto estimado</span>
                              <strong>{formatMoney(item.estimatedAmount, item.currencyCode)}</strong>
                            </div>
                          </div>
                          <div className="evidence-groups" aria-label="Evidencia hija disponible">
                            <article className="evidence-group">
                              <span className="evidence-label">Líneas o ítems</span>
                              <strong>{formatCount(item.lineCount)}</strong>
                              <small>Detalle disponible si la API entrega líneas.</small>
                            </article>
                            <article className="evidence-group">
                              <span className="evidence-label">Ofertas</span>
                              <strong>{formatCount(item.bidCount)}</strong>
                              <small>{`${formatCount(item.supplierCount)} proveedores asociados.`}</small>
                            </article>
                            <article className="evidence-group">
                              <span className="evidence-label">Órdenes de compra</span>
                              <strong>{formatCount(item.purchaseOrderCount)}</strong>
                              <small>Relaciones tratadas como evidencia, no como hecho confirmado.</small>
                            </article>
                          </div>
                          <div className="table-evidence-panel__actions">
                            <Button variant="primary" onClick={() => onOpenDetail(item.noticeId)}>
                              Abrir detalle
                            </Button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </Table>
      </TableWrap>
      <div ref={explorerLoadMoreRef} className="workspace-infinite-sentinel" aria-hidden="true" />
      {isLoadingMoreExplorer ? (
        <div className="workspace-infinite-loader" role="status" aria-live="polite">
          <RefreshCw size={14} aria-hidden="true" className="upload-progress__spinner" />
          <span>Cargando más licitaciones...</span>
        </div>
      ) : null}
      {loadMoreErrorMessage ? (
        <div className="workspace-infinite-error" role="status">
          <span>{loadMoreErrorMessage}</span>
          <Button variant="ghost" onClick={onRetryLoadMore}>
            Reintentar carga
          </Button>
        </div>
      ) : null}
      {!canAutoLoadMore && listItems.length > 0 ? (
        <div className="workspace-infinite-end" role="status">
          <span>Fin de resultados cargados para esta consulta.</span>
        </div>
      ) : null}
    </>
  );
}

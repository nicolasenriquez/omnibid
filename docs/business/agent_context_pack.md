# Paquete de Contexto de Omnibid

_Snapshot vivo capturado el 2026-05-15 con el stack Docker levantado y la base consultada en producción local._

## Qué Es Este Documento

Este archivo es un contexto compacto pero amplio para otro agente de IA. Reúne:
- objetivo de negocio
- flujo del usuario
- arquitectura técnica
- pipeline de datos
- inventario de tablas
- contenido vivo de la base
- texto visible de la aplicación
- contratos principales del API

No es un dump completo de todas las filas. Para tablas grandes, el reporte incluye conteos, muestras representativas y el contrato de esquema. Si se necesita un exporte total, conviene generar CSV o SQL aparte.

## Resumen Ejecutivo

1. `omnibid` es una plataforma determinística de inteligencia de compras públicas para Chile.
2. El negocio es supplier-side: ayuda a una empresa proveedora a encontrar, entender y priorizar licitaciones.
3. La fuente operativa histórica es `Datos Abiertos` y la fuente viva es la API de `Mercado Público`.
4. La app visible al usuario es un workspace read-only en `/licitaciones`.
5. La arquitectura separa `Raw`, `Normalized`, `Silver` y deja `Gold` para capas posteriores.
6. El runtime canónico es Docker Compose con `just` como superficie operativa.
7. La base tiene alto volumen: millones de filas en `raw_*` y `normalized_*`, y cientos de miles en `silver_*`.
8. La lane viva de Mercado Público mezcla `rolling-window`, `detail-by-codigo` y `active-discovery`.
9. El workspace sincroniza filtros, tabs y selección por URL; la watchlist vive en `localStorage`.
10. El producto actual es de lectura y evidencia, no de scoring ni recomendación automática.

## Objetivo De Negocio

Omnibid existe para reducir el tiempo que una empresa proveedora invierte en:
- descubrir oportunidades
- leer bases
- verificar fechas y elegibilidad
- comparar líneas, ofertas y órdenes de compra
- decidir si vale la pena seguir una licitación

El producto no reemplaza la revisión humana. La decisión legal, comercial y de cumplimiento sigue siendo humana.

### Qué Sí Automatiza
- detección y refresco de oportunidades
- normalización y deduplicación
- extracción determinística de fechas, montos y estados
- evidencia lineal de productos, ofertas y órdenes de compra
- packaging de contexto para análisis

### Qué No Automatiza
- lectura legal de bases
- compliance final
- bid / no-bid como verdad automática
- scoring o recomendación persistida en Silver
- narrativa generada por agente como verdad canónica

## Flujo Del Usuario

1. Entra a `/licitaciones`.
2. Ve el encabezado con métricas, estado de API y modo activo.
3. Filtra por estado, etapa, región, categoría, fechas, montos o tipo de compra.
4. Cambia entre `Lista` y `Radar`.
5. Abre una licitación desde una fila o una tarjeta.
6. Revisa el panel lateral con resumen, línea de tiempo, líneas, ofertas y OC.
7. Copia el código externo o abre la licitación en ChileCompra.
8. Marca ítems para la watchlist local (`Radar`).
9. Exporta CSV o imprime la vista actual si hace falta.
10. Si el usuario lo necesita, abre el `Centro de Ingesta` para cargar CSV manuales.

La vista conserva contexto: el panel lateral y la selección no deberían hacer perder el estado de lista/radar.

## Arquitectura Técnica

### Stack
- Backend: FastAPI + SQLAlchemy + Alembic
- Base de datos: PostgreSQL 16
- Frontend: Next.js App Router + React 19 + TypeScript
- Estilos: Tailwind + CSS modular de workspace
- Runtime local: Docker Compose
- CLI operativa: `just`
- Package manager frontend: `pnpm`
- Package manager backend: `uv`

### Componentes Principales
- `backend/core`: configuración y wiring
- `backend/db`: sesión, base, engine
- `backend/api`: health, operations, uploads, opportunities
- `backend/pipeline/extract`: clientes y contratos de entrada
- `backend/pipeline/transform`: builders de canonicalización, upsert y quality gates
- `backend/pipeline/load`: persistencia, colas y checkpoints
- `backend/pipeline/orchestration`: sync diario y worker
- `backend/models`: modelos ORM de operational, raw, normalized y silver
- `client/`: workspace read-only y clientes de API

### Boundary Operativo
- La ruta frontend principal es `/licitaciones`.
- El API read-only principal es `/opportunities`.
- La lane de API de Mercado Público está separada de los CSV históricos.
- `Silver` guarda hechos determinísticos y anotaciones semánticas versionadas.
- `Gold` queda para agregados, features y decisiones posteriores.

## Workflow Funcional

### Pipeline CSV
1. Registrar archivo fuente.
2. Perfilar y validar columnas.
3. Ingerir raw con hash y linaje.
4. Construir `Normalized`.
5. Construir `Silver`.

### Pipeline API Mercado Público
1. `active-discovery` detecta activas.
2. `rolling-window` refresca el universo reciente.
3. `detail-by-codigo` enriquece oportunidades candidatas.
4. Se persisten request, payload y snapshots.
5. Se canoniza a `Normalized` + `Silver`.
6. Se postprocesan enlaces y métricas derivadas.

### Cadena Diaria
La corrida diaria efectiva compone:
- rolling sync
- detail enrichment
- canonicalización de payloads
- postprocesamiento Silver

## Contrato Del API Visible

### Endpoints
- `GET /health`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /files`
- `GET /files/{source_file_id}`
- `GET /datasets/summary`
- `POST /uploads/procurement-csv/preflight`
- `POST /uploads/procurement-csv/{file_token}/process`
- `GET /uploads/procurement-csv/jobs/{job_id}`
- `GET /opportunities`
- `GET /opportunities/summary`
- `GET /opportunities/{notice_id}`

### Lista De Oportunidades
Campos principales:
- `noticeId`
- `externalNoticeCode`
- `title`
- `officialStatus`
- `mpEstadoCodigo`
- `mpEstadoNombre`
- `mpEstadoCanonical`
- `dataSourceKind`
- `availabilityContext`
- `codigoTipo`
- `tipo`
- `tipoConvocatoria`
- `informada`
- `visibilidadMonto`
- `fuenteFinanciamiento`
- `complaintCount`
- `derivedStage`
- `estimatedAmount`
- `currencyCode`
- `publicationDate`
- `closeDate`
- `lineCount`
- `bidCount`
- `supplierCount`
- `purchaseOrderCount`
- `buyerName`
- `buyerRegion`
- `buyerCommune`
- `primaryCategory`
- `procurementType`
- `isLessThan100Utm`
- `daysRemaining`

### Detalle De Oportunidad
Campos principales:
- todo lo anterior
- `noticeDescriptionRaw`
- `participantsAvailability`
- `offersAvailability`
- `awardAvailability`
- `purchaseOrderAvailability`
- `descriptionAvailability`
- `buyer`
- `relationshipSummary`
- `timeline`
- `lines`
- `offers`
- `purchaseOrders`

### Reglas Semánticas
- `derivedStage` puede ser `open`, `closing_soon`, `closed`, `awarded`, `revoked_or_suspended` o `unknown`.
- `RelationshipCertainty` puede ser `high`, `medium`, `low`, `none` o `unconfirmed`.
- `OpportunityAvailability` puede ser `available`, `not_yet_public`, `not_applicable`, `pending_detail`, `not_reported_by_source` o `pipeline_missing`.
- Los textos visibles siempre están en español.

## Texto Visible Y Labels Canónicos

### Tabs Y Modo
- `Lista`
- `Radar`
- `Abiertas`
- `Históricas`
- `Lista y Radar en solo lectura`
- `Radar activo`
- `Lista activa`
- `Mismo universo de oportunidades, distinta vista.`

### Etapas
- `Abierta`
- `Cierra pronto`
- `Cerrada`
- `Adjudicada`
- `Revocada o suspendida`
- `Sin clasificar`

### Tipos De Compra
- `Pública`
- `Privada`
- `Servicios`

### Certeza De Relación
- `Alta`
- `Media`
- `Baja`
- `Sin evidencia`
- `No confirmada`

### Disponibilidad
- `Disponible`
- `Aún no aplica`
- `Pendiente de detalle`
- `No informado por la fuente`
- `Histórico no cargado`

### Encabezado Y Estado
- `Oportunidades`
- `API conectada`
- `Consultando API`
- `Resultados pendientes`
- `Refrescar`
- `Limpiar filtros`
- `Anterior`
- `Siguiente`
- `Exportar CSV`
- `Imprimir`

### Filtros
- `Estado oficial`
- `Etapa`
- `Región comprador`
- `Categoría`
- `Fecha cierre`
- `Fecha publicación`
- `Monto mínimo`
- `Monto máximo`
- `Tipo licitación`
- `Menor a 100 UTM`

### Acciones De Selección
- `Agregar al radar`
- `Quitar del radar`
- `Limpiar selección`
- `Radar`

### Detalle
- `Detalle de licitación`
- `Origen: Radar`
- `Origen: Lista`
- `Copiar código`
- `Abrir licitación`
- `Analizar oportunidad`
- `Línea de tiempo`
- `Productos o servicios`
- `Comprador`
- `Económico y evidencia`
- `Órdenes de compra`
- `Metadatos`
- `Fuente: API de oportunidades en modo lectura.`

### Estados Y Errores
- `No disponible`
- `No informado por la fuente`
- `No se encontraron oportunidades. Intenta con otros filtros o más tarde.`
- `Hubo un problema al cargar las oportunidades. Intenta de nuevo en unos momentos.`
- `No se pudo conectar con el servidor. Verifica tu conexión.`
- `Sin tarjetas`
- `No hay oportunidades para esta etapa.`
- `Detalle no disponible`
- `Error de detalle`
- `No se pudo copiar el código.`

### Ingesta Manual
- `Centro de Ingesta`
- `Cargar CSV al flujo`
- `Selecciona Licitaciones u Órdenes de compra, adjunta CSV y valida antes de cargar.`
- `Preparar`
- `Validar`
- `Cargar`
- `Validar archivo`
- `Cargar archivo`
- `Arrastra CSV o haz clic para elegir`
- `CSV delimitado por ;. El backend revisa columnas requeridas, hash y límite de carga.`
- `Procesando archivo…`
- `Esto puede tardar varios minutos en CSV grandes.`
- `Puedes cerrar esta ventana. El proceso continua en el servidor.`

### Atajo
- `Ctrl/Cmd + Shift + E` exporta CSV.

## Inventario De Base De Datos

### Capas Y Modelo
- `Operational`: `source_files`, `source_checkpoints`, `pipeline_runs`, `pipeline_run_steps`, `ingestion_batches`, `data_quality_issues`, `dataset_summary_snapshots`
- `API source`: `api_source_request`, `api_source_payload`, `mercado_publico_notice_snapshot`, `mercado_publico_notice_item_snapshot`
- `Raw`: `raw_licitaciones`, `raw_ordenes_compra`
- `Normalized`: `normalized_licitaciones`, `normalized_licitacion_items`, `normalized_buyers`, `normalized_suppliers`, `normalized_categories`, `normalized_ofertas`, `normalized_ordenes_compra`, `normalized_ordenes_compra_items`
- `Silver`: `silver_notice`, `silver_notice_line`, `silver_bid_submission`, `silver_award_outcome`, `silver_purchase_order`, `silver_purchase_order_line`, `silver_buying_org`, `silver_contracting_unit`, `silver_supplier`, `silver_category_ref`, `silver_notice_purchase_order_link`, `silver_supplier_participation`, `silver_notice_text_ann`, `silver_notice_line_text_ann`, `silver_purchase_order_line_text_ann`

### Granos Importantes
- `source_files`: un archivo o artefacto lógico registrado
- `pipeline_runs`: una corrida
- `raw_licitaciones`: una fila cruda de licitación
- `raw_ordenes_compra`: una fila cruda de OC
- `normalized_licitaciones`: una licitación canónica
- `normalized_licitacion_items`: una línea de licitación
- `normalized_ofertas`: una oferta
- `normalized_ordenes_compra`: una orden de compra
- `normalized_ordenes_compra_items`: una línea de OC
- `silver_notice`: una oportunidad canónica
- `silver_notice_line`: una línea de oportunidad
- `silver_bid_submission`: una oferta canónica
- `silver_award_outcome`: un resultado de adjudicación
- `silver_purchase_order`: una OC canónica
- `silver_purchase_order_line`: una línea de OC canónica
- `silver_notice_text_ann` / `silver_notice_line_text_ann` / `silver_purchase_order_line_text_ann`: anotaciones NLP versionadas

### Claves Canónicas
- Buyer key: `buyer_key` = `CodigoUnidadCompra`
- Supplier key: `supplier_key` = `codigo:<CodigoProveedor>` y fallback `rut:<RutProveedor>`
- Category key: `category_key` = `codigoCategoria`
- Silver usa `notice_id` y `notice_id + item_code` como grano principal

## Snapshot Vivo De La Base

_Conteos consultados directamente en PostgreSQL el 2026-05-15._

### Operacional Y API Source

| Tabla | Filas | Lectura rápida |
|---|---:|---|
| `source_files` | 61 | Archivos y artefactos lógicos registrados |
| `source_checkpoints` | 0 | Reservado; no usado en esta base |
| `pipeline_runs` | 126 | Corridas de pipeline |
| `pipeline_run_steps` | 168 | Pasos por corrida |
| `ingestion_batches` | 70 | Lotes de carga raw |
| `data_quality_issues` | 2 | Avisos de calidad registrados |
| `dataset_summary_snapshots` | 1 | Snapshot resumido del dataset |
| `api_source_request` | 2,764 | Requests persistidos de la lane API |
| `api_source_payload` | 3,258 | Payloads persistidos |
| `mercado_publico_notice_snapshot` | 58,980 | Snapshots de licitaciones API |
| `mercado_publico_notice_item_snapshot` | 7,022 | Snapshots de items API |

### Raw

| Tabla | Filas | Lectura rápida |
|---|---:|---|
| `raw_licitaciones` | 2,269,483 | Histórico crudo de licitaciones |
| `raw_ordenes_compra` | 6,999,377 | Histórico crudo de órdenes de compra |

### Normalized

| Tabla | Filas | Lectura rápida |
|---|---:|---|
| `normalized_licitaciones` | 124,577 | Licitaciones canónicas |
| `normalized_licitacion_items` | 570,575 | Líneas de licitación |
| `normalized_buyers` | 5,895 | Maestros de compradores |
| `normalized_suppliers` | 94,720 | Maestros de proveedores |
| `normalized_categories` | 1,992 | Catálogo de categorías/ONU |
| `normalized_ofertas` | 2,119,924 | Ofertas |
| `normalized_ordenes_compra` | 2,394,889 | Órdenes de compra |
| `normalized_ordenes_compra_items` | 6,668,038 | Ítems de OC |

### Silver

| Tabla | Filas | Lectura rápida |
|---|---:|---|
| `silver_notice` | 128,119 | Oportunidades canónicas |
| `silver_notice_line` | 565,146 | Líneas de oportunidad |
| `silver_bid_submission` | 2,111,924 | Ofertas canónicas |
| `silver_award_outcome` | 2,111,464 | Adjudicaciones canónicas |
| `silver_purchase_order` | 2,394,889 | Órdenes de compra canónicas |
| `silver_purchase_order_line` | 6,668,038 | Líneas de OC canónicas |
| `silver_buying_org` | 1,190 | Organismos compradores |
| `silver_contracting_unit` | 5,933 | Unidades de compra |
| `silver_supplier` | 94,720 | Proveedores |
| `silver_category_ref` | 12,435 | Referencias de categoría |
| `silver_notice_purchase_order_link` | 361,200 | Puentes licitación-OC |
| `silver_supplier_participation` | 540,306 | Participación de proveedores |
| `silver_notice_text_ann` | 122,400 | NLP sobre descripciones de licitación |
| `silver_notice_line_text_ann` | 565,146 | NLP sobre líneas de licitación |
| `silver_purchase_order_line_text_ann` | 6,668,038 | NLP sobre líneas de OC |

### Distribución De `source_files`

| dataset_type | status | count |
|---|---|---:|
| `licitacion` | `completed` | 5 |
| `licitacion` | `failed` | 2 |
| `licitacion` | `loaded` | 22 |
| `mercado_publico_api_notice` | `loaded` | 15 |
| `orden_compra` | `completed` | 1 |
| `orden_compra` | `loaded` | 16 |

### Distribución De Snapshots API

| `source_mode` | count | lectura |
|---|---:|---|
| `rolling-window` | 37,652 | predominante en la lane viva |
| `(null)` | 9,486 | snapshots heredados o sin clasificar |
| `active-discovery` | 8,644 | descubrimiento de activas |
| `detail-by-codigo` | 3,198 | enriquecimiento puntual por código |

### Completeness API

| `api_completeness_level` | count |
|---|---:|
| `(null)` | 37,151 |
| `summary` | 20,014 |
| `detail` | 1,815 |

### Snapshot Resumido Más Reciente

`dataset_summary_snapshots` más reciente:
- `generated_at`: 2026-05-14 03:44:01.051532+00
- `refresh_mode`: `bootstrap`
- `status`: `success`
- `source_files_count`: 61
- `raw_licitaciones_count`: 2,269,483
- `raw_ordenes_compra_count`: 6,999,377
- `normalized_licitaciones_count`: 124,577
- `normalized_licitacion_items_count`: 570,575
- `normalized_ofertas_count`: 2,119,924
- `normalized_ordenes_compra_count`: 2,394,889
- `normalized_ordenes_compra_items_count`: 6,668,038

## Estado De Calidad

Hay 2 avisos históricos en `data_quality_issues`, ambos asociados a `normalized_categories` para `orden_compra`:

| fecha | dataset | tabla | issue | severity | resumen |
|---|---|---|---|---|---|
| 2026-04-25 20:22:13.481521+00 | `orden_compra` | `normalized_categories` | `normalized_missing_domain_identity` | warning | `codigo_categoria` faltante, 5,000 filas procesadas, 646 rechazadas, error rate 12.92% |
| 2026-04-25 18:12:16.185472+00 | `orden_compra` | `normalized_categories` | `normalized_missing_domain_identity` | warning | `codigo_categoria` faltante, 3,121,628 filas procesadas, 500,536 rechazadas, error rate 16.03% |

## Muestras Reales De La Base

### Linaje API

- `api_source_request` más reciente: `5251-26-CO26`, GET a `licitaciones.json?codigo=...`, HTTP 200, `ticket` redacted, `success=true`.
- `api_source_payload` más reciente: `payload_count=1`, `schema_observed_keys=["Cantidad", "FechaCreacion", "Listado", "Version"]`.
- `mercado_publico_notice_snapshot` más reciente: `5251-26-CO26`, `source_mode=detail-by-codigo`, `api_completeness_level=detail`, comprador `UNIVERSIDAD TECNOLOGICA METROPOLITANA`, unidad `DEPARTAMENTO DE ABASTECIMIENTO`, monto `47000.00`.

### Oportunidad Canónica

- Un ejemplo vivo de `silver_notice` es `1099402-12-R126`, `officialStatus=Cerrada`, `derivedStage=awarded`, `estimatedAmount=19400000.0`, `complaintCount=15`.
- En ese detalle, la disponibilidad calculada fue:
  - `participantsAvailability=available`
  - `offersAvailability=available`
  - `awardAvailability=available`
  - `purchaseOrderAvailability=pipeline_missing`
  - `descriptionAvailability=available`
- El `relationshipSummary` de ese ejemplo fue `none`.

### Líneas, Ofertas Y Órdenes

- `silver_notice_line` muestra líneas con `line_bid_count`, `line_supplier_count` y rangos de oferta. Ejemplo: línea `43440514` de `1099402-12-R126` tuvo 10 ofertas, 10 proveedores, mínimo `10000.00` y máximo `10656000.00`.
- `normalized_ofertas` contiene ofertas aceptadas y rechazadas con `oferta_seleccionada`, montos unitarios y totales, y fecha de envío.
- `normalized_ordenes_compra` muestra que `CodigoLicitacion` puede venir vacío, así que el vínculo OC-licitación es opcional.
- `silver_purchase_order` conserva el enlace opcional y los flags `is_linked_to_notice_flag`, `is_direct_award_flag`, `is_agile_purchase_flag`.
- `silver_purchase_order_line` conserva `linked_notice_id`, código ONU, categorías, specs de comprador y proveedor, y totales por línea.

### Puentes Y Relaciones

- `silver_notice_purchase_order_link` usa `link_type=explicit_code_match` con `link_confidence=1.000000` en muchos ejemplos.
- `silver_supplier_participation` materializa el vínculo entre proveedor, aviso, oferta, adjudicación y OC.

### NLP Y Texto

- `silver_notice_text_ann` usa `nlp_version=silver_nlp_v1`, `corpus_scope=notice_description`, `language_detected=es` y `tfidf_artifact_ref` tipo `tfidf://...`.
- En muestras vivas aparecen etiquetas semánticas como `health` y `maintenance`.
- `silver_purchase_order_line_text_ann` usa `corpus_scope=purchase_order_line_specs`, `language_detected=es` y referencias `tfidf://silver_purchase_order_line/...`.
- La política de Silver es guardar referencias y metadatos, no vectores serializados ni scores de negocio.

## Surface Del Usuario En La App

### Encabezado
- muestra métricas de oportunidad
- muestra frescura de datos
- muestra estado de API
- permite refrescar la consulta
- expone el acceso al `Centro de Ingesta`

### Filtros
- búsqueda por texto
- estado oficial
- etapa derivada
- región del comprador
- categoría primaria
- rango de fechas de publicación y cierre
- rango de monto
- tipo de adquisición
- bandera `Menor a 100 UTM`
- chips de filtro activos con remoción individual

### Lista
- tabla de oportunidades
- selección masiva
- expandir/contraer fila
- toggle de watchlist
- ordenamiento por monto, cierre, publicación y días restantes
- carga incremental al hacer scroll en `Lista`

### Radar
- tablero por etapa
- tarjetas por oportunidad
- evidencia resumida de líneas, ofertas y OC
- selección visual del ítem activo

### Detalle
- panel lateral sticky
- encabezado con código y estado
- copiar código
- abrir en ChileCompra
- resumen
- timeline
- líneas
- comprador
- evidencia económica
- ofertas con vista `resumen` o `todas`
- órdenes de compra
- metadatos

### Watchlist
- se guarda en `localStorage`
- el key actual es `opportunity-workspace.watchlist.v1`
- el filtro `Radar` es local, no un write backend

### Ingesta Manual
- flujo de 3 pasos: `Preparar` → `Validar` → `Cargar`
- dataset switch: `Licitaciones` / `Órdenes de compra`
- subida de CSV delimitado por `;`
- validación previa de columnas, hash y tamaño
- consola viva con progreso del backend

## Herramientas Y Comandos Canónicos

### Docker / just
- `rtk just compose-up`
- `rtk just docker-pipeline-full`
- `rtk just docker-smoke`
- `rtk just dev`
- `rtk just mp-api-daily-refresh`
- `rtk just mp-api-sync-active`
- `rtk just mp-api-sync-rolling`
- `rtk just mp-api-sync-detail`
- `rtk just test-unit`
- `rtk just quality`

### Reglas De Runtime
- el host DB interno usa `db` y `db_test`, nunca `localhost`
- el dataset se monta read-only en `/datasets/mercado-publico`
- el backend corre non-root y con `no-new-privileges`
- el frontend usa `pnpm`, nunca `npm` en `client/`

## Riesgos Y Cautelas

- No asumir que toda OC tiene licitación enlazada.
- No asumir que toda licitación termina en OC.
- No tratar `ONU` como evidencia concluyente por sí sola.
- No inventar scores, forecast o recomendaciones.
- No mover hechos de negocio a Silver si son heurísticos o predictivos.
- No confundir `source_files`, `raw_*`, `normalized_*` y `silver_*` porque representan grano distinto.
- `source_checkpoints` está vacío hoy; no es un error, pero sí una señal de que esa parte del sistema no está activa en este snapshot.

## Archivos Clave Para Profundizar

- `README.md`
- `PRODUCT.md`
- `docs/business/market_public_domain_overview.md`
- `docs/business/procurement_lifecycle.md`
- `docs/business/data_sources_downloads_vs_api.md`
- `docs/business/domain_glossary.md`
- `docs/architecture/data_model.md`
- `docs/architecture/data_architecture.md`
- `docs/architecture/external_api_ingestion.md`
- `docs/pipeline/structure.md`
- `backend/models/operational.py`
- `backend/models/api_source.py`
- `backend/models/raw.py`
- `backend/models/normalized.py`
- `backend/api/routers/opportunities.py`
- `backend/api/opportunities_contract.py`
- `backend/api/opportunities_query.py`
- `client/src/features/opportunity-workspace/workspace.tsx`
- `client/src/features/opportunity-workspace/workspace-detail-pane.tsx`
- `client/src/features/opportunity-workspace/workspace-list-views.tsx`
- `client/src/features/opportunity-workspace/display-contract.ts`
- `client/src/features/opportunity-workspace/upload-workflow-state.ts`

## Cierre

Si otro agente va a rehacer la UI, este es el modelo mental correcto:
- el producto es un workspace de investigación de oportunidades
- la unidad principal es la licitación/aviso, no la oferta ni la OC
- el detalle debe mostrar evidencia, no inventar certeza
- la base ya contiene una cantidad grande de datos normalizados y Silver
- el diseño nuevo debe respetar el flujo read-only, el idioma español y el linaje explícito

## Anexo Técnico: Esquema, Relaciones Y Granos

### 1) Esquema Por Capas

#### Operational
- `source_files`
- `source_checkpoints`
- `pipeline_runs`
- `pipeline_run_steps`
- `ingestion_batches`
- `data_quality_issues`
- `dataset_summary_snapshots`

#### API Source
- `api_source_request`
- `api_source_payload`
- `mercado_publico_notice_snapshot`
- `mercado_publico_notice_item_snapshot`

#### Raw
- `raw_licitaciones`
- `raw_ordenes_compra`

#### Normalized
- `normalized_licitaciones`
- `normalized_licitacion_items`
- `normalized_buyers`
- `normalized_suppliers`
- `normalized_categories`
- `normalized_ofertas`
- `normalized_ordenes_compra`
- `normalized_ordenes_compra_items`

#### Silver
- `silver_notice`
- `silver_notice_line`
- `silver_bid_submission`
- `silver_award_outcome`
- `silver_purchase_order`
- `silver_purchase_order_line`
- `silver_buying_org`
- `silver_contracting_unit`
- `silver_supplier`
- `silver_category_ref`
- `silver_notice_purchase_order_link`
- `silver_supplier_participation`
- `silver_notice_text_ann`
- `silver_notice_line_text_ann`
- `silver_purchase_order_line_text_ann`

### 2) Relaciones Principales

#### Operational / lineage
- `pipeline_runs.source_file_id -> source_files.id`
- `pipeline_run_steps.run_id -> pipeline_runs.id`
- `ingestion_batches.source_file_id -> source_files.id`
- `data_quality_issues.run_id -> pipeline_runs.id`
- `data_quality_issues.source_file_id -> source_files.id`
- `api_source_request.pipeline_run_id -> pipeline_runs.id`
- `api_source_payload.pipeline_run_id -> pipeline_runs.id`
- `mercado_publico_notice_snapshot.pipeline_run_id -> pipeline_runs.id`
- `mercado_publico_notice_snapshot.request_id -> api_source_request.id`
- `mercado_publico_notice_snapshot.payload_id -> api_source_payload.id`
- `mercado_publico_notice_item_snapshot.pipeline_run_id -> pipeline_runs.id`
- `mercado_publico_notice_item_snapshot.request_id -> api_source_request.id`
- `mercado_publico_notice_item_snapshot.payload_id -> api_source_payload.id`

#### Raw / normalized
- `raw_licitaciones.source_file_id -> source_files.id`
- `raw_licitaciones.batch_id -> ingestion_batches.id`
- `raw_ordenes_compra.source_file_id -> source_files.id`
- `raw_ordenes_compra.batch_id -> ingestion_batches.id`
- `normalized_licitaciones.source_file_id -> source_files.id`
- `normalized_licitacion_items.codigo_externo -> normalized_licitaciones.codigo_externo`
- `normalized_licitacion_items.source_file_id -> source_files.id`
- `normalized_ofertas.codigo_externo -> normalized_licitaciones.codigo_externo`
- `normalized_ofertas.supplier_key -> normalized_suppliers.supplier_key`
- `normalized_ordenes_compra.buyer_key -> normalized_buyers.buyer_key`
- `normalized_ordenes_compra.supplier_key -> normalized_suppliers.supplier_key`
- `normalized_ordenes_compra_items.codigo_oc -> normalized_ordenes_compra.codigo_oc`
- `normalized_ordenes_compra_items.category_key -> normalized_categories.category_key`

#### Silver canonical
- `silver_notice_line.notice_id -> silver_notice.notice_id`
- `silver_bid_submission.notice_id -> silver_notice.notice_id`
- `silver_bid_submission.notice_line_id -> silver_notice_line.notice_line_id`
- `silver_award_outcome.notice_id -> silver_notice.notice_id`
- `silver_award_outcome.notice_line_id -> silver_notice_line.notice_line_id`
- `silver_award_outcome.bid_submission_id -> silver_bid_submission.bid_submission_id`
- `silver_purchase_order_line.purchase_order_id -> silver_purchase_order.purchase_order_id`
- `silver_buying_org` and `silver_contracting_unit` are buyer masters
- `silver_supplier_participation.supplier_id -> silver_supplier.supplier_id`
- `silver_supplier_participation.notice_id -> silver_notice.notice_id`
- `silver_supplier_participation.notice_line_id -> silver_notice_line.notice_line_id`
- `silver_supplier_participation.bid_submission_id -> silver_bid_submission.bid_submission_id`
- `silver_supplier_participation.award_outcome_id -> silver_award_outcome.award_outcome_id`
- `silver_supplier_participation.purchase_order_line_id -> silver_purchase_order_line.purchase_order_line_id`
- `silver_notice_text_ann.notice_id -> silver_notice.notice_id`
- `silver_notice_line_text_ann.notice_id, item_code -> silver_notice_line.notice_id, item_code`
- `silver_purchase_order_line_text_ann.purchase_order_id, line_item_id -> silver_purchase_order_line.purchase_order_id, line_item_id`
- `silver_notice_purchase_order_link.notice_id -> silver_notice.notice_id`
- `silver_notice_purchase_order_link.purchase_order_id -> silver_purchase_order.purchase_order_id`

### 3) Granos Y Cardinalidades

#### Parent grains
- `source_files`: 1 file = 1 row
- `pipeline_runs`: 1 run = 1 row
- `normalized_licitaciones`: 1 licitación = 1 row by `codigo_externo`
- `normalized_ordenes_compra`: 1 OC = 1 row by `codigo_oc`
- `silver_notice`: 1 oportunidad = 1 row by `notice_id`
- `silver_purchase_order`: 1 OC canónica = 1 row by `purchase_order_id`

#### Child grains
- `normalized_licitacion_items`: 1 line item = 1 row by (`codigo_externo`, `codigo_item`)
- `normalized_ofertas`: 1 offer = 1 row by `oferta_key_sha256`
- `normalized_ordenes_compra_items`: 1 OC line = 1 row by (`codigo_oc`, `id_item`)
- `silver_notice_line`: 1 notice line = 1 row by (`notice_id`, `item_code`)
- `silver_bid_submission`: 1 bid = 1 row by `bid_submission_id`
- `silver_award_outcome`: 1 award = 1 row by `award_outcome_id`
- `silver_purchase_order_line`: 1 OC line = 1 row by (`purchase_order_id`, `line_item_id`)

#### Bridge / fact grains
- `silver_notice_purchase_order_link`: 1 relationship row per notice + OC + link type
- `silver_supplier_participation`: 1 supplier participation row per supplier + notice

#### Annotation grains
- `silver_notice_text_ann`: 1 notice + 1 NLP version
- `silver_notice_line_text_ann`: 1 notice line + 1 NLP version
- `silver_purchase_order_line_text_ann`: 1 OC line + 1 NLP version

### 4) Join Rules Que El Agente Debe Respetar

- No unir líneas hijas directamente a la grilla principal sin deduplicar por `notice_id`.
- No asumir que `purchase_order` implica automáticamente `notice`.
- No asumir que `ONU` o `category` son evidencia concluyente.
- Usar `silver_notice` como grano padre del workspace.
- Usar `silver_notice_line`, `silver_bid_submission`, `silver_award_outcome`, `silver_purchase_order` y `silver_purchase_order_line` solo como evidencia hija.
- Mantener `relationshipCertainty` visible cuando el vínculo no es directo.

### 5) Contrato De Persistencia

- `Raw` conserva traza y fila original.
- `Normalized` conserva la entidad canónica lista para consulta.
- `Silver` conserva hechos determinísticos, métricas y anotaciones.
- `Gold` no debe mezclarse con hechos canónicos actuales.

### 6) Llaves Relevantes Para Diseño De UI

- `noticeId` = unidad de selección y detalle.
- `externalNoticeCode` = código visible y copiable.
- `itemCode` = unidad de evidencia de línea.
- `purchaseOrderCode` = unidad de evidencia OC.
- `supplierCode` / `supplierName` = unidad de comparación de oferta.
- `derivedStage` = estado visual del radar y la lista.
- `relationshipSummary` = confianza agregada del caso.

### 7) Observaciones De Modelado

- `source_checkpoints` aparece vacío en este snapshot.
- `dataSourceKind` y `availabilityContext` forman parte del contrato de detalle para explicar cobertura y vacíos.
- Algunos campos del detalle se rellenan desde `Silver`; otros son fallback desde `Normalized`.
- El workspace de lista/radar no debe depender de nombres de columna SQL; debe depender del contrato DTO.

## Anexo Técnico

### 1) Inventario De Esquema Por Capa

#### Operacional
- `source_files`: catálogo de archivos o fuentes ingeridas.
- `source_checkpoints`: control de avance e idempotencia por fuente.
- `pipeline_runs`: ejecución completa de un pipeline.
- `pipeline_run_steps`: detalle de cada paso de un run.
- `ingestion_batches`: lote físico o lógico de carga.
- `data_quality_issues`: hallazgos de validación o calidad.
- `dataset_summary_snapshots`: instantáneas resumidas del estado del dataset.
- `api_source_request`: request observada contra la API.
- `api_source_payload`: payload crudo recibido desde la API.
- `mercado_publico_notice_snapshot`: snapshot de oportunidad/notice antes de normalizar.
- `mercado_publico_notice_item_snapshot`: snapshot de ítems asociados a la notice.

#### Raw
- `raw_licitaciones`: fila cruda de licitación.
- `raw_licitacion_items`: ítems crudos de la licitación.
- `raw_ofertas`: ofertas crudas capturadas desde origen.
- `raw_ordenes_compra`: ordenes de compra crudas.
- `raw_ordenes_compra_items`: líneas crudas de OC.

#### Normalized
- `normalized_licitaciones`: cabecera canónica de licitación.
- `normalized_licitacion_items`: líneas canónicas de licitación.
- `normalized_ofertas`: ofertas canónicas y deduplicadas.
- `normalized_buyers`: compradores / organismos.
- `normalized_suppliers`: proveedores.
- `normalized_categories`: categorías / clasificaciones.
- `normalized_ordenes_compra`: cabecera canónica de OC.
- `normalized_ordenes_compra_items`: líneas canónicas de OC.

#### Silver
- `silver_notice`: entidad de trabajo para la UI y el análisis.
- `silver_notice_line`: líneas de la notice.
- `silver_bid_submission`: envíos de oferta.
- `silver_award_outcome`: resultado de adjudicación.
- `silver_purchase_order`: OC canónica de negocio.
- `silver_purchase_order_line`: líneas de OC.
- `silver_buying_org`: organismo comprador.
- `silver_contracting_unit`: unidad compradora / contratante.
- `silver_supplier`: proveedor.
- `silver_category_ref`: referencia de categoría.
- `silver_notice_purchase_order_link`: relación notice-OC.
- `silver_supplier_participation`: participación de proveedor en una notice.
- `silver_notice_text_ann`: anotación NLP a nivel notice.
- `silver_notice_line_text_ann`: anotación NLP a nivel línea de notice.
- `silver_purchase_order_line_text_ann`: anotación NLP a nivel línea de OC.

### 2) Relaciones Clave Entre Tablas

#### Cadena de trazabilidad
- `source_files` -> `ingestion_batches` -> `pipeline_runs` -> `pipeline_run_steps` -> tablas destino.
- `source_files` y `api_source_request` explican de dónde salió cada lote.
- `api_source_payload` conserva el contenido observado antes de la transformación.

#### Licitaciones
- `normalized_licitaciones` es la cabecera.
- `normalized_licitacion_items` depende de `normalized_licitaciones` por `codigo_externo`.
- `normalized_ofertas` depende de la licitación y de la línea / item que recibió la oferta.
- `silver_notice` se construye desde la licitación normalizada y concentra el contrato de UI.
- `silver_notice_line` depende de `silver_notice` y desciende al grano de línea.
- `silver_bid_submission` y `silver_award_outcome` cuelgan de la notice y/o de su línea relacionada.

#### Órdenes de compra
- `normalized_ordenes_compra` es la cabecera.
- `normalized_ordenes_compra_items` depende de `normalized_ordenes_compra`.
- `silver_purchase_order` es la representación canónica de negocio.
- `silver_purchase_order_line` depende de `silver_purchase_order`.
- `silver_purchase_order_line_text_ann` agrega anotación semántica a la línea de OC.

#### Relaciones puente
- `silver_notice_purchase_order_link` conecta notice y OC cuando existe evidencia explícita o inferida.
- `silver_supplier_participation` conecta proveedor y notice.
- Estas tablas no deben tratarse como equivalentes a una FK dura; representan evidencia de relación.

#### Catálogos y soporte
- `normalized_buyers` alimenta `silver_buying_org`.
- `normalized_suppliers` alimenta `silver_supplier`.
- `normalized_categories` alimenta `silver_category_ref`.
- `silver_contracting_unit` agrega la unidad compradora observada en el negocio.

### 3) Llaves De Negocio Y Claves Técnicas

- `codigo_externo`: clave natural principal para licitación.
- `notice_id`: clave canónica de trabajo para el workspace.
- `purchase_order_id`: clave canónica de orden de compra.
- `codigo_oc`: clave externa para OC.
- `codigo_item` / `item_code`: clave de línea.
- `supplier_code`: clave natural del proveedor.
- `category_code`: clave natural de categoría.
- `ingestion_batch_id`: clave técnica del lote.
- `pipeline_run_id`: clave técnica de la ejecución.
- `source_file_id`: clave técnica del archivo fuente.

### 4) Cardinalidades Esperadas

- 1 `source_file` -> N `pipeline_runs` relacionados.
- 1 `pipeline_run` -> N `pipeline_run_steps`.
- 1 `normalized_licitacion` -> N `normalized_licitacion_items`.
- 1 `normalized_licitacion` -> N `normalized_ofertas`.
- 1 `normalized_orden_compra` -> N `normalized_ordenes_compra_items`.
- 1 `silver_notice` -> N `silver_notice_line`.
- 1 `silver_purchase_order` -> N `silver_purchase_order_line`.
- 1 `silver_notice` -> N `silver_notice_text_ann` por versión NLP.
- 1 `silver_notice_line` -> N `silver_notice_line_text_ann` por versión NLP.
- 1 `silver_purchase_order_line` -> N `silver_purchase_order_line_text_ann` por versión NLP.

### 5) Reglas Prácticas Para El Agente

- No asumir que una OC siempre deriva de una notice; la relación puede ser parcial o inferida.
- No colapsar oferta, línea y cabecera en una sola entidad visual.
- No usar `normalized_categories` o `silver_category_ref` como identidad completa si el código viene vacío.
- Mantener visibles los casos de evidencia parcial, porque son parte del valor analítico.
- Para rediseño de UI, tomar `silver_notice` como grano principal y usar las tablas hijas como paneles de contexto, no como lista principal.

# Omnibid — Reporte Completo de Proyecto para Agente de IA

> **Propósito:** Este documento proporciona el contexto completo del proyecto Omnibid para que un agente de IA pueda entender la aplicación, sus datos, flujos, arquitectura y objetivos de negocio, y así generar rediseños o nuevas funcionalidades asumiendo el rol de un **analista de licitaciones públicas**.

---

## 1. Resumen Ejecutivo

**Omnibid** es un espacio de trabajo determinístico de datos de procurement (licitaciones públicas). Permite buscar, filtrar y analizar licitaciones de ChileCompra/Mercado Público por etapa, fecha de cierre, monto, comprador y categoría. Los usuarios pivotan entre vistas de radar (kanban) y explorador (tabla), y pueden profundizar en el detalle de cada oportunidad con evidencia de líneas, ofertas, adjudicaciones y órdenes de compra.

### Stack tecnológico
- **Backend:** FastAPI + PostgreSQL + SQLAlchemy + Alembic
- **Frontend:** Next.js 15 (App Router) + React + TypeScript + Tailwind CSS
- **Runtime/Paquetería:** `uv` (backend Python), `pnpm` (frontend)
- **Infraestructura local:** Docker Compose (PostgreSQL 16 + API container)
- **Orquestación:** `just` (task runner)
- **NLP:** spaCy + FastText para anotaciones semánticas en español

### Objetivo de negocio
Proveer a **analistas de procurement** una herramienta de inteligencia de licitaciones que:
1. Centralice datos de oportunidades públicas chilenas (ChileCompra / Mercado Público)
2. Permita filtrar, ordenar y seguir licitaciones en tiempo real
3. Exponga evidencia estructurada para decidir si participar (licitar) o no
4. Mantenga trazabilidad completa desde la fuente original hasta el dato normalizado

---

## 2. Estructura del Proyecto

```
omnibid/
├── backend/                    # FastAPI application
│   ├── api/                    # API routers y servicios
│   │   ├── routers/            # health, opportunities, operations, manual_uploads
│   │   ├── services/           # dataset_summary_snapshots
│   │   ├── deps.py             # Inyección de dependencias (DB session)
│   │   ├── opportunities_contract.py  # Modelos Pydantic de respuesta
│   │   └── opportunities_query.py     # Filtros SQL dinámicos
│   ├── core/                   # Config, settings (pydantic-settings)
│   ├── db/                     # SQLAlchemy engine, session, base
│   ├── ingestion/              # Ingesta manual de CSVs
│   ├── integrations/           # Shims de integración Mercado Público
│   ├── models/                 # ORM models (operational, raw, normalized, api_source, ingestion_jobs)
│   ├── nlp/                    # NLP pipeline (spaCy, FastText, TF-IDF)
│   ├── normalized/             # Transformaciones raw → normalized
│   ├── observability/          # Logging estructurado, CLI UI
│   ├── pipeline/               # Pipeline de datos
│   │   ├── extract/            # API clients, esquemas, rate limiting
│   │   ├── transform/          # Normalización, canonicalización, upsert engine
│   │   ├── load/               # Persistencia, store, postprocess
│   │   ├── orchestration/      # daily_pipeline, sync, worker
│   │   └── shared/             # cleaning, validación
│   └── main.py                 # FastAPI app entrypoint
├── client/                     # Next.js frontend
│   ├── app/                    # App Router pages
│   │   ├── licitaciones/       # /licitaciones → OpportunityWorkspace
│   │   ├── page.tsx            # Redirect a /licitaciones
│   │   └── layout.tsx          # Root layout con tema
│   └── src/
│       ├── components/ui/      # Design system: Badge, Button, Card, Chip, Input, Panel, Select, Skeleton, Table, Tabs
│       ├── features/opportunity-workspace/  # Feature module completo
│       ├── lib/                # API clients, formatters, URL state, theme
│       ├── styles/             # Design tokens CSS, workspace CSS
│       └── types/              # TypeScript types para API contracts
├── scripts/                    # Entrypoints operacionales
│   ├── ingest_raw.py           # Ingesta de CSV → raw
│   ├── build_normalized.py     # Raw → Normalized + Silver build
│   ├── fetch_mp_api.py         # Fetch manual de API Mercado Público
│   ├── run_mp_api_daily_pipeline.py  # Pipeline diario completo
│   ├── profile_raw.py          # Profileo de archivos fuente
│   └── run_ingestion_jobs.py   # Worker de cola de ingesta
├── alembic/                    # Migraciones de base de datos (17 revisiones)
├── tests/                      # Unit + Integration tests (~45 archivos)
├── config/                     # pipeline.yaml, NLP configs JSON
├── docs/                       # Arquitectura, negocio, runbooks, estándares, referencias SDD
├── openspec/                   # Change proposals + specs (5 activos, 16 archivados)
├── docker-compose.yml          # Runtime Docker local
├── Dockerfile                  # Imagen de la API
├── justfile                    # Task runner recipes
├── pyproject.toml              # Dependencias Python
└── PRODUCT.md                  # Visión de producto
```

---

## 3. Modelo de Negocio y Dominio

### Dominio: Licitaciones Públicas Chilenas (Mercado Público / ChileCompra)

**ChileCompra** es la agencia pública que administra el sistema de compras públicas chilenas. **Mercado Público** es la plataforma transaccional donde ocurren las licitaciones.

#### Conceptos clave del dominio

| Término | Significado oficial | Implicancia en datos |
|---|---|---|
| **Licitación pública** | Procedimiento abierto donde cualquier proveedor calificado puede ofertar | Modelada como notice con líneas, ofertas, adjudicaciones y posibles OC |
| **Licitación privada** | Procedimiento por invitación limitado a proveedores seleccionados | Camino más restringido |
| **Oferta** | Respuesta de un proveedor a una licitación | Existe a nivel línea + proveedor |
| **Adjudicación** | Selección de la oferta más conveniente | Hito clave antes de contrato/OC |
| **Orden de Compra (OC)** | Documento electrónico emitido por el comprador | Puede o no vincularse a una licitación |
| **Compra Ágil** | Procedimiento rápido para montos menores | Canal separado con reglas distintas |
| **Convenio Marco** | Catálogo de compras recurrentes | Manejo separado |
| **Trato Directo** | Contratación directa excepcional | No es licitación abierta |

#### Jerarquía de datos del procurement

```
Notice (Licitación)
├── Line (Línea/Producto solicitado)
│   ├── Bid Submission (Oferta por proveedor)
│   │   └── Award Outcome (Adjudicación)
│   └── Purchase Order Line (Línea de OC vinculada)
└── Purchase Order (Orden de Compra)
    └── Purchase Order Line
```

### Modelo de negocio (intermediario)

Omnibid es una herramienta **supplier-side** (lado proveedor). Ayuda a equipos a:
1. **Encontrar** oportunidades relevantes
2. **Entender** requisitos, competencia y contexto
3. **Decidir** si participar (licitar) basado en evidencia

**No reemplaza** los flujos de compra del Estado. Mantiene a los humanos en el loop para decisiones legales, comerciales y de compliance.

---

## 4. Base de Datos — Esquema Completo

### 4.1 Capa Operacional (`operational.py`)

Tablas de infraestructura del pipeline:

#### `source_files` — Archivos fuente registrados
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `dataset_type` | Text | `licitacion` u `orden_compra` |
| `file_name` | Text | Nombre original |
| `file_path` | Text | Ruta/URI del archivo |
| `file_size_bytes` | BigInt | Tamaño en bytes |
| `file_hash_sha256` | String(64) | Hash SHA-256 (unique) |
| `source_modified_at` | DateTime | Fecha de modificación del origen |
| `registered_at` | DateTime | Cuándo se registró |
| `status` | Text | `registered`, `loaded`, etc. |
| `source_meta` | JSONB | Metadata del origen |

#### `source_checkpoints` — Puntos de control de ingesta incremental
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `source_kind` | Text | Tipo de fuente (`csv_upload`, `api_snapshot`) |
| `dataset_type` | Text | Tipo de dataset |
| `source_file_id` | UUID | FK → source_files |
| `storage_uri` | Text | URI del storage |
| `payload_hash_sha256` | String(64) | Hash del payload |
| `status` | Text | `staged`, `consumed`, `completed` |
| `consumed_job_id` | UUID | Job que lo consumió |
| `cleanup_eligible_at` | DateTime | Elegible para limpieza |

#### `pipeline_runs` — Ejecuciones del pipeline
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `run_key` | Text | Clave única de ejecución (unique) |
| `dataset_type` | Text | Tipo de dataset |
| `source_file_id` | UUID | FK → source_files |
| `status` | Text | `running`, `completed`, `failed` |
| `provider` | Text | Origen (ej. `mercado_publico`) |
| `run_mode` | Text | Modo de ejecución |
| `started_at` | DateTime | Inicio |
| `finished_at` | DateTime | Fin |
| `config` | JSONB | Configuración de la corrida |
| `run_parameters_json` | JSONB | Parámetros |
| `run_stats_json` | JSONB | Estadísticas finales |
| `error_summary` | Text | Resumen de error |

#### `pipeline_run_steps` — Pasos dentro de una ejecución
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `run_id` | UUID | FK → pipeline_runs |
| `step_name` | Text | Nombre del paso |
| `status` | Text | `running`, `completed`, `failed` |
| `rows_in` | BigInt | Filas de entrada |
| `rows_out` | BigInt | Filas de salida |
| `rows_rejected` | BigInt | Filas rechazadas |
| `error_details` | JSONB | Detalles de error |

#### `ingestion_batches` — Lotes de ingesta
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `source_file_id` | UUID | FK → source_files |
| `batch_key` | Text | Clave única del lote (unique) |
| `status` | Text | `started`, `completed`, `failed` |
| `total_rows` | BigInt | Total de filas |
| `loaded_rows` | BigInt | Filas cargadas |
| `rejected_rows` | BigInt | Filas rechazadas |

#### `data_quality_issues` — Issues de calidad de datos
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `run_id` | UUID | FK → pipeline_runs |
| `source_file_id` | UUID | FK → source_files |
| `dataset_type` | Text | Tipo de dataset |
| `table_name` | Text | Tabla afectada |
| `issue_type` | Text | Tipo de issue |
| `severity` | Text | `warning`, `error`, `critical` |
| `record_ref` | Text | Referencia al registro |
| `column_name` | Text | Columna afectada |
| `issue_value` | Text | Valor problemático |
| `details` | JSONB | Detalles |

#### `dataset_summary_snapshots` — Snapshots de resumen
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `generated_at` | DateTime | Cuándo se generó |
| `refresh_mode` | Text | Modo de refresco |
| `status` | Text | `success`, `failed` |
| `source_files_count` | BigInt | N° de archivos fuente |
| `raw_licitaciones_count` | BigInt | Total raw licitaciones |
| `raw_ordenes_compra_count` | BigInt | Total raw OCs |
| `normalized_licitaciones_count` | BigInt | Total normalized licitaciones |
| `normalized_licitacion_items_count` | BigInt | Total items |
| `normalized_ofertas_count` | BigInt | Total ofertas |
| `normalized_ordenes_compra_count` | BigInt | Total OCs normalizadas |
| `normalized_ordenes_compra_items_count` | BigInt | Total items OC |

### 4.2 Capa Raw (`raw.py`)

Datos en bruto (JSONB), preservación completa del origen:

#### `raw_licitaciones`
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | BigInt | PK autoincremental |
| `source_file_id` | UUID | FK → source_files |
| `batch_id` | UUID | FK → ingestion_batches |
| `raw_row_num` | BigInt | Número de fila en el archivo original |
| `codigo` | Text | Código interno |
| `codigo_externo` | Text | Código externo (ChileCompra) |
| `row_hash_sha256` | String(64) | Hash de la fila |
| `raw_json` | JSONB | **JSON completo de la fila original** |
| `ingested_at` | DateTime | Fecha de ingesta |

- Unique constraint: `(source_file_id, raw_row_num)`

#### `raw_ordenes_compra`
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | BigInt | PK autoincremental |
| `source_file_id` | UUID | FK → source_files |
| `batch_id` | UUID | FK → ingestion_batches |
| `raw_row_num` | BigInt | Número de fila |
| `codigo_oc` | Text | Código de OC |
| `codigo_licitacion` | Text | Código de licitación vinculada |
| `id_item` | Text | ID del ítem |
| `row_hash_sha256` | String(64) | Hash de la fila |
| `raw_json` | JSONB | **JSON completo de la fila original** |
| `ingested_at` | DateTime | Fecha de ingesta |

- Unique constraint: `(source_file_id, raw_row_num)`

### 4.3 Capa API Source (`api_source.py`)

Tablas operacionales para la ingesta desde API Mercado Público:

#### `api_source_payload` — Payloads crudos de API
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `pipeline_run_id` | UUID | FK → pipeline_runs |
| `source_system` | Text | `mercado_publico` |
| `endpoint_name` | Text | `licitaciones.json` |
| `resource_type` | Text | `licitacion` |
| `resource_key` | Text | Clave del recurso |
| `fetched_at` | DateTime | Cuándo se obtuvo |
| `payload_json` | JSONB | **Respuesta completa de la API** |
| `payload_sha256` | String(64) | Hash del payload (unique) |
| `api_version` | Text | Versión de API |
| `source_fecha_creacion` | Date | Fecha del lado fuente |
| `source_count` | Integer | Cantidad reportada |
| `schema_observed_keys` | JSONB | Keys observadas en el payload |

#### `api_source_request` — Requests a la API
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `pipeline_run_id` | UUID | FK → pipeline_runs |
| `source_system` | Text | `mercado_publico` |
| `endpoint_name` | Text | Endpoint llamado |
| `resource_type` | Text | Tipo de recurso |
| `resource_key` | Text | Clave del recurso |
| `request_method` | Text | `GET` |
| `request_url_safe` | Text | URL (sin secretos) |
| `request_params_json` | JSONB | Parámetros (sin ticket) |
| `request_hash` | String(64) | Hash del request |
| `requested_at` | DateTime | Cuándo se hizo |
| `completed_at` | DateTime | Cuándo completó |
| `http_status` | Integer | Código HTTP |
| `success` | Boolean | ¿Exitosa? |
| `error_type` | Text | Tipo de error |
| `error_message` | Text | Mensaje de error |
| `cost_units` | Integer | Unidades de costo (rate limit) |
| `response_hash` | String(64) | Hash de la respuesta |
| `response_payload_id` | UUID | FK → api_source_payload |
| `cache_hit` | Boolean | ¿Cache hit? |
| `rate_limit_day` | Date | Día para rate limiting |

#### `mercado_publico_notice_snapshot` — Snapshots de licitaciones
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `pipeline_run_id` | UUID | FK → pipeline_runs |
| `request_id` | UUID | FK → api_source_request |
| `payload_id` | UUID | FK → api_source_payload |
| `endpoint_name` | Text | Endpoint |
| `source_mode` | Text | `rolling-window`, `detail-by-codigo`, `active-discovery` |
| `resource_key` | Text | Clave del recurso |
| `notice_id` | Text | ID interno |
| `external_notice_code` | Text | **Código externo (ChileCompra)** |
| `notice_title` | Text | Título de la licitación |
| `official_status_code` | Integer | Código de estado oficial |
| `official_status_name` | Text | Nombre del estado |
| `publication_date` | Date | Fecha de publicación |
| `close_date` | Date | Fecha de cierre |
| `buyer_org_code` | Text | Código organismo comprador |
| `buyer_org_name` | Text | Nombre organismo |
| `buyer_unit_code` | Text | Código unidad de compra |
| `buyer_unit_name` | Text | Nombre unidad |
| `currency_code` | Text | Código moneda |
| `estimated_amount` | Numeric(20,2) | Monto estimado |
| `payload_sha256` | String(64) | Hash del payload |
| `snapshot_date` | Date | Fecha del snapshot |
| `observed_at` | DateTime | Cuándo se observó |
| `synced_at` | DateTime | Cuándo se sincronizó |
| `description` | Text | Descripción |
| `buyer_unit_address` | Text | Dirección |
| `buyer_unit_commune` | Text | Comuna |
| `buyer_unit_region` | Text | Región |
| `buyer_user_rut` | Text | RUT usuario comprador |
| `buyer_user_code` | Text | Código usuario |
| `buyer_user_name` | Text | Nombre usuario |
| `buyer_user_position` | Text | Cargo |
| `created_date` | Date | Fecha creación |
| `estimated_award_date` | Date | Fecha estimada adjudicación |
| `award_date` | Date | Fecha adjudicación real |
| `tipo` | Text | Tipo (Licitación Pública, etc.) |
| `codigo_tipo` | Text | Código de tipo |
| `tipo_convocatoria` | Text | Tipo convocatoria |
| `days_to_close` | Integer | Días para cierre |
| `claim_count` | Integer | Cantidad de reclamos |
| `funding_source` | Text | Fuente financiamiento |
| `visibility_amount` | Text | Visibilidad monto |
| `api_completeness_level` | Text | `summary` o `detail` |

- Unique: `(external_notice_code, payload_sha256)` y `(payload_id, external_notice_code)`

#### `mercado_publico_notice_item_snapshot` — Ítems de licitaciones
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `pipeline_run_id` | UUID | FK |
| `request_id` | UUID | FK |
| `payload_id` | UUID | FK |
| `external_notice_code` | Text | Código licitación |
| `item_correlative` | Integer | Correlativo del ítem |
| `codigo_producto` | Text | Código ONU |
| `codigo_categoria` | Text | Código categoría |
| `categoria` | Text | Nombre categoría |
| `nombre_producto` | Text | Nombre del producto |
| `descripcion` | Text | Descripción |
| `unidad_medida` | Text | Unidad de medida |
| `cantidad` | Text | Cantidad |

- Unique: `(payload_id, external_notice_code, item_correlative)`

### 4.4 Capa de Jobs de Ingesta (`ingestion_jobs.py`)

#### `pipeline_jobs` — Cola de trabajos del pipeline
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `job_type` | Text | Tipo de job |
| `source_kind` | Text | Tipo de fuente |
| `dataset_type` | Text | Tipo de dataset |
| `source_checkpoint_id` | UUID | FK → source_checkpoints |
| `status` | Text | `queued`, `running`, `completed`, `failed`, `dead` |
| `priority` | Integer | Prioridad (default 100) |
| `payload` | JSONB | Payload del job |
| `attempts` | Integer | Intentos realizados |
| `max_attempts` | Integer | Máximo de intentos (default 2) |
| `available_at` | DateTime | Disponible desde |
| `locked_at` | DateTime | Cuándo se lockeó |
| `locked_by` | Text | Quién lo lockeó |
| `started_at` | DateTime | Inicio |
| `finished_at` | DateTime | Fin |
| `failed_at` | DateTime | Fallo |
| `error_message` | Text | Mensaje de error |

#### `ingestion_units` — Unidades de ingesta
| Columna | Tipo | Descripción |
|---|---|---|
| `id` | UUID | PK |
| `job_id` | UUID | FK → pipeline_jobs |
| `source_checkpoint_id` | UUID | FK → source_checkpoints |
| `source_kind` | Text | Tipo de fuente |
| `dataset_type` | Text | Tipo de dataset |
| `source_file_id` | UUID | FK → source_files |
| `api_call_id` | UUID | ID de llamada API |
| `period_start` | Date | Inicio del período |
| `period_end` | Date | Fin del período |
| `raw_min_id` | BigInt | ID mínimo raw |
| `raw_max_id` | BigInt | ID máximo raw |
| `raw_inserted_rows` | BigInt | Filas insertadas |
| `raw_duplicate_rows` | BigInt | Filas duplicadas |
| `status` | Text | `started`, `completed`, `failed` |
| `metadata` | JSONB | Metadata |

### 4.5 Capa Normalized (`normalized.py`)

Entidades canónicas con modelos relacionales. **18 tablas** en total (8 normalized core + 10 silver).

#### Normalized Core (8 tablas)

##### `normalized_licitaciones`
- **PK:** `codigo_externo` (Text)
- Campos principales: `codigo`, `nombre`, `descripcion`, `tipo_adquisicion`, `tipo_adquisicion_norm`, `codigo_estado`, `estado`, `tipo`, `tipo_convocatoria`, `moneda_adquisicion`, `visibilidad_monto_raw`, `monto_estimado` (Numeric 20,6), `numero_oferentes`, `codigo_organismo`, `nombre_organismo`, `codigo_unidad`, `nombre_unidad`, `comuna_unidad`, `region_unidad`, `fecha_publicacion`, `fecha_cierre`, `fecha_adjudicacion`, `fecha_estimada_adjudicacion`, `fecha_inicio`, `fecha_final`, `cantidad_dias_licitacion`
- Flags: `flag_licitacion_publica`, `flag_licitacion_privada`, `flag_licitacion_servicios`, `flag_menos_100_utm`, `is_elegible_mvp`
- Auditoría: `source_file_id`, `row_hash_sha256`, `created_at`, `updated_at`

##### `normalized_licitacion_items`
- **PK:** `id` (BigInt autoincrement)
- **FK:** `codigo_externo` → normalized_licitaciones
- Campos: `codigo_item`, `correlativo`, `codigo_producto_onu`, `nombre_producto_generico`, `nombre_linea_adquisicion`, `descripcion_linea_adquisicion`, `unidad_medida`, `cantidad` (Numeric 20,6), `rubro1`, `rubro2`, `rubro3`
- Unique: `(codigo_externo, codigo_item)`

##### `normalized_buyers`
- **PK:** `buyer_key` (Text) — basado en `CodigoUnidadCompra`
- Campos: `codigo_unidad_compra`, `rut_unidad_compra`, `unidad_compra`, `codigo_organismo_publico`, `organismo_publico`, `sector`, `actividad_comprador`, `ciudad_unidad_compra`, `region_unidad_compra`, `pais_unidad_compra`

##### `normalized_suppliers`
- **PK:** `supplier_key` (Text) — precedencia: `codigo:<CodigoProveedor>` → `rut:<RutProveedor>`
- Campos: `codigo_proveedor`, `rut_proveedor`, `nombre_proveedor`, `razon_social_proveedor`, `actividad_proveedor`, `comuna_proveedor`, `region_proveedor`, `pais_proveedor`

##### `normalized_categories`
- **PK:** `category_key` (Text) — basado en `codigoCategoria`
- Campos: `codigo_categoria`, `categoria`, `rubro_n1`, `rubro_n2`, `rubro_n3`

##### `normalized_ofertas`
- **PK:** `oferta_key_sha256` (String 64)
- **FKs:** `codigo_externo` → normalized_licitaciones, `supplier_key` → normalized_suppliers
- Campos: `codigo_item`, `correlativo`, `codigo_proveedor`, `rut_proveedor`, `nombre_proveedor`, `razon_social_proveedor`, `estado_oferta`, `nombre_oferta`, `cantidad_ofertada`, `monto_unitario_oferta`, `valor_total_ofertado`, `oferta_seleccionada`, `fecha_envio_oferta`, `cantidad_adjudicada`, `monto_linea_adjudica`, `monto_estimado_adjudicado`

##### `normalized_ordenes_compra`
- **PK:** `codigo_oc` (Text)
- **FKs:** `buyer_key`, `supplier_key`
- Campos extensos: información completa de OC incluyendo montos (total, neto, impuestos, descuentos, cargos), fechas (creación, envío, aceptación, cancelación), comprador, proveedor, financiamiento, forma de pago, tipo despacho
- Flags: `es_trato_directo`, `es_compra_agil`, `has_codigo_licitacion`
- Campos de link: `codigo_licitacion`, `codigo_convenio_marco`

##### `normalized_ordenes_compra_items`
- **PK:** `id` (BigInt autoincrement)
- **FKs:** `codigo_oc` → normalized_ordenes_compra, `category_key` → normalized_categories
- Campos: `id_item`, `codigo_producto_onu`, `codigo_categoria`, `categoria`, `nombre_producto_generico`, `rubro_n1`, `rubro_n2`, `rubro_n3`, `especificacion_comprador`, `especificacion_proveedor`, `cantidad`, `unidad_medida`, `moneda_item`, `precio_neto`, `total_cargos`, `total_descuentos`, `total_impuestos`, `total_linea_neto`
- Unique: `(codigo_oc, id_item)`

#### Silver Layer (10 tablas + 3 anotaciones)

##### `silver_notice`
- **PK:** `notice_id` (Text)
- Visa canónica de la licitación con: `external_notice_code`, `notice_url`, `notice_title`, `notice_description_raw`, `notice_description_clean`, `procurement_method_name`, `procurement_method_code`, `notice_status_name`, `notice_status_code`, `mp_estado_codigo`, `mp_estado_nombre`, `mp_estado_canonical`, `data_source_kind`, `availability_context`
- Fechas: `publication_date`, `created_date`, `close_date`, `award_date`, `estimated_award_date`
- Montos: `estimated_amount` (Numeric 20,6), `currency_code`, `currency_name`
- Flags: `is_public_tender_flag`, `is_private_tender_flag`, `requires_toma_razon_flag`, `multiple_stages_flag`, `hidden_budget_flag`, `has_extension_flag`, `has_site_visit_flag`, `has_physical_document_delivery_flag`
- Conteos: `notice_line_count`, `notice_bid_count`, `notice_supplier_count`, `notice_selected_bid_count`, `notice_awarded_line_count`
- OC link: `notice_has_purchase_order_flag`, `notice_purchase_order_count`, `notice_awarded_to_order_conversion_flag`
- Días calculados: `days_publication_to_close`, `days_creation_to_close`, `days_close_to_award`
- Flag: `has_missing_date_chain_flag`

##### `silver_notice_line`
- **PK:** `notice_line_id` (BigInt autoincrement)
- **FK:** `notice_id` → silver_notice
- Campos: `line_number`, `item_code`, `onu_product_code`, `category_level_1/2/3`, `generic_product_name`, `line_name`, `line_description_raw`, `line_description_clean`, `unit_of_measure`, `quantity_requested` (Numeric 20,6)
- Estadísticas de ofertas: `line_bid_count`, `line_supplier_count`, `line_min_offer_amount`, `line_max_offer_amount`, `line_avg_offer_amount`, `line_median_offer_amount`, `line_price_dispersion_ratio`
- Unique: `(notice_id, item_code)`

##### `silver_bid_submission`
- **PK:** `bid_submission_id` (String 64)
- **FKs:** `notice_id` → silver_notice, `notice_line_id` → silver_notice_line
- Campos: `supplier_key`, `supplier_branch_id`, `item_code`, `offer_name`, `offer_status`, `offer_submission_date`, `offered_quantity`, `offer_currency_name`, `unit_price_offered`, `total_price_offered`, `selected_offer_flag`

##### `silver_award_outcome`
- **PK:** `award_outcome_id` (String 64)
- **FKs:** `bid_submission_id` → silver_bid_submission, `notice_id` → silver_notice, `notice_line_id` → silver_notice_line
- Campos: `supplier_key`, `selected_offer_flag`, `awarded_quantity`, `awarded_line_amount`, `award_date`, `award_status`, `item_code`

##### `silver_purchase_order`
- **PK:** `purchase_order_id` (Text)
- Campos: `purchase_order_code`, `purchase_order_url`, `purchase_order_name`, `purchase_order_description_raw/clean`, `purchase_order_type`, `purchase_order_type_code`, `purchase_order_status_code/name`, `supplier_status_code/name`
- Fechas: `order_created_at`, `order_sent_at`, `order_accepted_at`, `order_cancelled_at`, `order_last_modified_at`
- Días: `days_order_creation_to_acceptance`, `days_order_creation_to_cancellation`
- Montos: `total_amount`, `net_total_amount`, `tax_amount`, `discount_amount`, `charge_amount`, `currency_code/name`
- Links: `supplier_key`, `supplier_branch_id`, `linked_notice_id`
- Flags: `is_linked_to_notice_flag`, `is_direct_award_flag`, `is_agile_purchase_flag`, `has_items_flag`
- Conteos: `purchase_order_line_count`, `purchase_order_total_quantity`, `purchase_order_total_net_amount`, `purchase_order_unique_product_count`

##### `silver_purchase_order_line`
- **PK:** `purchase_order_line_id` (BigInt autoincrement)
- **FK:** `purchase_order_id` → silver_purchase_order
- Campos: `line_item_id`, `linked_notice_id`, `onu_product_code`, `category_code`, `category_name`, `category_level_1/2/3`, `generic_product_name`, `buyer_item_spec_raw/clean`, `supplier_item_spec_raw/clean`, `quantity_ordered`, `unit_of_measure`, `line_currency`, `unit_net_price`, `line_net_total`, `line_tax_total`, `line_discount_total`, `line_charge_total`
- Unique: `(purchase_order_id, line_item_id)`

##### `silver_buying_org`
- **PK:** `buying_org_id` (Text)
- Campos: `buying_org_name`, `sector_name`

##### `silver_contracting_unit`
- **PK:** `contracting_unit_id` (Text)
- **FK:** `buying_org_id` → silver_buying_org
- Campos: `unit_rut`, `unit_name`, `unit_address`, `unit_commune`, `unit_region`, `unit_city`, `unit_country`

##### `silver_supplier`
- **PK:** `supplier_id` (Text)
- Campos: `supplier_branch_id`, `supplier_rut`, `supplier_trade_name`, `supplier_legal_name`, `supplier_activity`, `supplier_commune`, `supplier_region`, `supplier_country`

##### `silver_category_ref`
- **PK:** `category_ref_id` (Text)
- Campos: `onu_product_code`, `category_code`, `category_name`, `category_level_1/2/3`, `generic_product_name_canonical`

##### `silver_notice_purchase_order_link`
- **PK:** `notice_purchase_order_link_id` (BigInt autoincrement)
- **FKs:** `notice_id` → silver_notice, `purchase_order_id` → silver_purchase_order
- Campos: `link_type`, `link_confidence` (Numeric 10,6), `source_system`
- Unique: `(notice_id, purchase_order_id, link_type)`

##### `silver_supplier_participation`
- **PK:** `supplier_participation_id` (BigInt autoincrement)
- **FKs:** `supplier_id` → silver_supplier, `notice_id` → silver_notice, `notice_line_id`, `bid_submission_id`, `award_outcome_id`, `purchase_order_line_id`
- Flags: `was_selected_flag`, `was_materialized_in_purchase_order_flag`
- Unique: `(supplier_id, notice_id)`

#### Silver Text Annotations (3 tablas NLP)

##### `silver_notice_text_ann`
- **PK:** `(notice_id, nlp_version)`
- Campos: `corpus_scope`, `language_detected`, `normalized_tokens_json` (JSON), `top_ngrams_json` (JSON), `keyword_flags_json` (JSON), `domain_tags_json` (JSON), `semantic_category_label`, `tfidf_artifact_ref`

##### `silver_notice_line_text_ann`
- **PK:** `(notice_id, item_code, nlp_version)`
- FKs compuestas a `silver_notice` y `silver_notice_line`
- Mismos campos NLP que notice_text_ann

##### `silver_purchase_order_line_text_ann`
- **PK:** `(purchase_order_id, line_item_id, nlp_version)`
- FK compuesta a `silver_purchase_order_line`
- Campos adicionales: `buyer_spec_tags_json` (JSON), `supplier_spec_tags_json` (JSON)

---

## 5. Pipeline de Datos — Flujo Completo

### 5.1 Arquitectura de capas

```
┌─────────────────────────────────────────────────────────┐
│                     FUENTES DE DATOS                      │
│  ┌──────────────────┐  ┌──────────────────────────────┐  │
│  │  CSV Manual      │  │  API Mercado Público          │  │
│  │  (upload usuario) │  │  (licitaciones.json)          │  │
│  └──────┬───────────┘  └──────────────┬───────────────┘  │
└─────────┼──────────────────────────────┼──────────────────┘
          │                              │
          ▼                              ▼
┌─────────────────────────────────────────────────────────┐
│                    BRONZE / RAW                           │
│  raw_licitaciones (JSONB)                                │
│  raw_ordenes_compra (JSONB)                              │
│  api_source_payload (JSONB)                              │
│  api_source_request                                      │
│  mercado_publico_notice_snapshot                         │
│  mercado_publico_notice_item_snapshot                    │
│  ◆ Append-only, trazable, source_file_id + batch_id      │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                 SILVER / NORMALIZED                       │
│  normalized_licitaciones    ←──┐                         │
│  normalized_licitacion_items  │  Clean, canonical,       │
│  normalized_buyers            │  business keys,           │
│  normalized_suppliers         │  relational               │
│  normalized_categories        │                           │
│  normalized_ofertas           │                           │
│  normalized_ordenes_compra  ←──┘                         │
│  normalized_ordenes_compra_items                          │
│                                                          │
│  silver_notice               ←──┐                        │
│  silver_notice_line             │  Procurement cycle      │
│  silver_bid_submission          │  canonical path         │
│  silver_award_outcome           │  + deterministic        │
│  silver_purchase_order          │  enrichments            │
│  silver_purchase_order_line     │  + NLP annotations      │
│  silver_buying_org              │                         │
│  silver_contracting_unit        │                         │
│  silver_supplier              ←──┘                        │
│  silver_category_ref                                      │
│  silver_notice_purchase_order_link                        │
│  silver_supplier_participation                            │
│  silver_notice_text_ann                                   │
│  silver_notice_line_text_ann                              │
│  silver_purchase_order_line_text_ann                      │
│  ◆ Deterministic, query-ready, upsert semantics           │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│               GOLD (Futuro — No implementado)             │
│  Business aggregates, predictive scoring,                │
│  opportunity ranking, forecasting                        │
│  ◆ Deferred until Silver maturity gates pass             │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Pipeline Diario de API Mercado Público

Archivo principal: `backend/pipeline/orchestration/daily_pipeline.py`
Script entrypoint: `scripts/run_mp_api_daily_pipeline.py`

#### Paso 1: Rolling Window Sync
- Modo: `rolling-window`
- Recorre `window_days` días hacia atrás desde `target_date`
- Para cada día, llama a `GET /licitaciones.json?fecha=DDMMYYYY&ticket=***`
- Persiste request, payload y snapshots
- Usa PostgreSQL advisory locks para evitar race conditions
- Respeta rate limiting diario (máximo 10,000 requests/día)

#### Paso 2: Detail Enrichment (selectivo)
- Modo: `detail-by-codigo`
- Identifica candidatos que necesitan detalle (notices sin `detail` previo o stale)
- Selecciona hasta `max_candidates` códigos
- Para cada código, llama a `GET /licitaciones.json?codigo=XXXXXX&ticket=***`
- Prioriza notices con `source_mode = 'detail-by-codigo'` sobre `rolling-window`

#### Paso 3: Canonicalization → Silver + Normalized
- Toma los snapshots persistidos
- Aplica `canonicalize_mp_api_payloads_to_read_model()`:
  - Mapea snapshots → `silver_notice`
  - Mapea items → `silver_notice_line`
  - Mapea ofertas → `silver_bid_submission`
  - Mapea adjudicaciones → `silver_award_outcome`
  - Mapea compradores → `silver_buying_org` + `silver_contracting_unit`
  - Mapea proveedores → `silver_supplier`
  - Mapea categorías → `silver_category_ref`
  - Construye `silver_supplier_participation` (join supplier-notice)
- Aplica `canonicalize_api_snapshots_to_normalized()`:
  - Mapea a `normalized_licitaciones` + `normalized_licitacion_items`
  - Mapea ofertas a `normalized_ofertas` + `normalized_suppliers`
- Usa upsert engine con **complete-only semantics**: valores no-nulos existentes se preservan contra nulos/blancos entrantes

#### Paso 4: Silver Postprocess
- `run_mp_api_silver_postprocess()`:
  - Construye links notice ↔ purchase order (`silver_notice_purchase_order_link`)
  - Actualiza conteos derivados (line_count, bid_count, etc.)
  - Actualiza flags de relación (`notice_has_purchase_order_flag`, etc.)

#### Paso 5: NLP Annotations (script separado)
- Script: `scripts/build_nlp_annotations.py`
- Aplica spaCy + FastText para:
  - Tokenización y normalización de texto en español
  - Extracción de n-gramas
  - Detección de keywords de dominio
  - Etiquetado semántico
  - TF-IDF vectorization (solo referencias, no vectores serializados)
- Escribe en `silver_notice_text_ann`, `silver_notice_line_text_ann`, `silver_purchase_order_line_text_ann`

### 5.3 Pipeline de CSV Manual

Archivo principal: `backend/api/routers/manual_uploads.py`

#### Flujo completo de upload:

1. **Preflight (validación previa)**
   - `POST /uploads/procurement-csv/preflight`
   - Recibe archivo CSV + `dataset_type` (`licitacion` o `orden_compra`)
   - Valida: delimitador, columnas requeridas, hash SHA-256, tamaño
   - Retorna `file_token` (UUID) para referenciar el archivo staged

2. **Process (ejecución)**
   - `POST /uploads/procurement-csv/process`
   - Recibe `file_token`
   - Ejecuta en background:
     a. **Raw Ingest**: CSV → `raw_licitaciones` o `raw_ordenes_compra` (chunks de 5000)
     b. **Normalized Build**: Raw → `normalized_*` (fetch 10000, chunks 500)
     c. **Silver Build**: Normalized → `silver_*` (mismo upsert engine)
   - Reporta progreso en tiempo real (fases: `preparing`, `raw_ingest`, `normalized`, `finalizing`, `completed`/`failed`)

3. **Job Status (polling)**
   - `GET /uploads/procurement-csv/jobs/{job_id}`
   - Retorna estado actual, progreso (%, fase, filas procesadas), telemetría final
   - El frontend hace polling cada 1.8s durante el procesamiento

### 5.4 Pipeline Batch (CSV desde datasets)

Scripts:
- `scripts/profile_raw.py` — Perfila archivos fuente
- `scripts/ingest_raw.py` — Ingesta CSV → raw (chunk_size: 5000)
- `scripts/build_normalized.py` — Raw → Normalized + Silver (fetch_size: 10000, chunk_size: 500)

### 5.5 Calidad de Datos

- `backend/pipeline/transform/quality_gate.py` — Gates de calidad configurables
- `backend/pipeline/shared/cleaning.py` — Limpieza y normalización de texto
- `backend/pipeline/shared/validation.py` — Validación de contratos
- Silver feature guardrails en `upsert_engine.py`: prohíbe columnas de scoring/predicción en capa Silver
- Silver annotation guardrails: prohíbe vectores serializados, solo referencias TF-IDF

---

## 6. API Endpoints

### 6.1 Health
- `GET /health` → `{"status": "ok"}`

### 6.2 Opportunities (Oportunidades/Licitaciones)

#### `GET /opportunities/summary`
Métricas agregadas del universo de licitaciones, con filtros:
- Parámetros: `page`, `page_size`, `sort_by`, `sort_order`, `q` (búsqueda), `official_status`, `buyer_region`, `primary_category`, `publication_from/to`, `close_from/to`, `min_amount`, `max_amount`, `procurement_type` (`public`|`private`|`service`), `less_than_100_utm`, `stage`, `source_view` (`publicadas`)

Response: `{ metrics: [{ key, label, value }] }`
Métricas incluidas:
- `total_opportunities`, `open`, `closing_soon`, `closed`, `awarded`, `revoked_or_suspended`, `mp_publicada`, `source_publicadas`, `availability_publicadas`, `unknown_stage`, `avg_estimated_amount`, `total_estimated_amount`

#### `GET /opportunities`
Lista paginada de licitaciones:
- Mismos filtros que summary
- Response: `{ items: OpportunityListItem[], total, page, pageSize }`
- Cada item incluye: `noticeId`, `externalNoticeCode`, `title`, `officialStatus`, `mpEstadoCodigo/Nombre/Canonical`, `dataSourceKind`, `availabilityContext`, `codigoTipo`, `tipo`, `tipoConvocatoria`, `informada`, `visibilidadMonto`, `fuenteFinanciamiento`, `complaintCount`, `estimatedAmount`, `currencyCode`, `publicationDate`, `closeDate`, `lineCount`, `bidCount`, `supplierCount`, `purchaseOrderCount`, `buyerName`, `buyerRegion`, `buyerCommune`, `primaryCategory`, `procurementType`, `isLessThan100Utm`, `daysRemaining`, `derivedStage`

- **Estrategia de fuente:** `silver_notice` como principal, con fallback a `normalized_licitaciones` vía LEFT JOIN para campos display ausentes en Silver
- **Derived Stage calculado:** `awarded`, `revoked_or_suspended`, `unknown`, `closed`, `closing_soon`, `open`

#### `GET /opportunities/{notice_id}`
Detalle completo de una licitación:
- Response incluye:
  - **Header:** `noticeId`, `externalNoticeCode`, `title`, `officialStatus`, `mpEstado*`, `dataSourceKind`, `availabilityContext`, `codigoTipo`, `tipo`, `tipoConvocatoria`, `informada`, `visibilidadMonto`, `fuenteFinanciamiento`, `complaintCount`, `noticeDescriptionRaw`, `derivedStage`, `estimatedAmount`, `currencyCode`
  - **Availability flags:** `participantsAvailability`, `offersAvailability`, `awardAvailability`, `purchaseOrderAvailability`, `descriptionAvailability` (valores: `available`, `not_reported_by_source`, `pending_detail`, `pipeline_missing`, `not_yet_public`, `not_applicable`)
  - **Buyer:** `{ buyerName, buyerRegion, buyerCommune, contractingUnitName, contractingUnitCode }`
  - **RelationshipSummary:** `"none"` | `"low"` | `"medium"` | `"unconfirmed"` (certeza del vínculo líneas↔OC)
  - **Timeline:** `[{ key, label, date, source }]` (publication, close, estimated_award, award)
  - **Lines:** `[{ itemCode, correlative, productCodeOnu, lineName, lineDescription, category, quantity, unit, offerCount, selectedOfferCount, supplierCount, relatedPurchaseOrderItemCount, relationshipCertainty }]`
  - **Offers:** `[{ supplierCode, supplierName, offerName, itemCode, offerStatus, offeredAmount, unitPrice, offeredQuantity, currencyCode, isSelected, submittedAt }]`
  - **PurchaseOrders:** `[{ purchaseOrderCode, purchaseOrderStatus, purchaseOrderCreatedAt, purchaseOrderAmount, currencyCode }]`

### 6.3 Operations (Operaciones)

#### `GET /operations/runs` — Lista pipeline runs (default 50, max 200)
#### `GET /operations/runs/{run_id}` — Detalle de un pipeline run
#### `GET /operations/files` — Lista source files (default 100, max 200)
#### `GET /operations/files/{source_file_id}` — Detalle de un source file (incluye source_meta)
#### `GET /operations/datasets/summary` — Resumen de datasets (cached o fresh, con max_age configurable)

### 6.4 Manual Uploads (Carga Manual de CSV)

#### `GET /uploads/procurement-csv/limits` — Límites de upload (max_size_bytes, max_size_label)
#### `POST /uploads/procurement-csv/preflight` — Validación previa de archivo CSV
#### `POST /uploads/procurement-csv/process` — Procesar archivo (background)
#### `GET /uploads/procurement-csv/jobs/{job_id}` — Estado del job

---

## 7. Frontend — Arquitectura

### 7.1 Estructura del Workspace

El frontend es un **Opportunity Workspace** en la ruta `/licitaciones`.

**Componentes principales:**
- `workspace.tsx` — Componente raíz del workspace (2264 líneas)
- `workspace-detail-pane.tsx` — Panel lateral de detalle de licitación
- `workspace-list-views.tsx` — Vistas de lista:
  - `WorkspaceRadarBoard` — Vista Kanban por etapas
  - `WorkspaceExplorerTable` — Tabla con scroll infinito
- `query-state.ts` — Manejo de estado de URL (filtros, paginación)
- `workspace-view-model.ts` — View models, formateo, constantes
- `upload-workflow-state.ts` — Máquina de estados del flujo de upload

### 7.2 Vistas y Modos

#### Modos de datos:
- **Abiertas** (`mode=abiertas`): Solo licitaciones activas (open, closing_soon)
- **Histórico** (`mode=historico`): Ciclo completo (todas las etapas)

#### Tabs de visualización:
- **Explorer** (`tab=explorer`): Tabla con scroll infinito, selección múltiple, expansión de filas
- **Radar** (`tab=radar`): Kanban board agrupado por `derivedStage`

### 7.3 Flujo de Usuario Principal

1. **Usuario llega a `/licitaciones`** (redirigido desde `/`)
2. **Ve el header** con:
   - Modo de datos (Abiertas/Histórico)
   - KPIs rápidos (Total, Abiertas, Cierran pronto, etc.)
   - Botón de carga manual
3. **Aplica filtros:**
   - Búsqueda por texto (código, nombre, comprador, categoría)
   - Tipo (Pública, Privada, Servicios)
   - Etapa
   - Región
   - Rango de fechas (publicación, cierre)
   - Rango de montos
   - Solo radar (watchlist)
   - Vista Publicadas (solo fuente API)
4. **Navega resultados:**
   - En Explorer: tabla con columnas ordenables, scroll infinito
   - En Radar: columnas Kanban por etapa
5. **Selecciona una licitación** → Se abre panel lateral de detalle:
   - Datos generales (estado, fechas, montos)
   - Disponibilidad de datos (qué información existe y por qué)
   - Timeline de hitos
   - Comprador (nombre, región, comuna, unidad)
   - Productos/Servicios (líneas de la licitación)
   - Ofertas recibidas (proveedor, monto, estado)
   - Órdenes de compra vinculadas
   - Certeza de relación líneas↔OC
6. **Watchlist (Radar):**
   - Agrega/quita licitaciones del radar local (localStorage)
   - Filtra por "Solo radar" para ver seguimiento
7. **Exportación:**
   - CSV: descarga los items visibles
   - Impresión: window.print()
8. **Carga manual de CSV:**
   - Abre panel de ingesta
   - Selecciona tipo (licitación/orden_compra) y archivo
   - Preflight → Process → Polling de progreso
   - Al completar, refresca datos automáticamente

### 7.4 Atajos de teclado

| Atajo | Acción |
|---|---|
| `Ctrl/Cmd + F` | Enfocar búsqueda |
| `Ctrl/Cmd + Shift + E` | Exportar CSV |
| `Ctrl/Cmd + Shift + P` | Imprimir |
| `Esc` | Cerrar detalle o panel de ingesta |

### 7.5 Design System

Componentes UI personalizados (sin dependencia de librerías externas):
- `Badge`, `Button`, `IconButton`, `Card`, `Chip`, `DetailSection`, `Input`, `Panel`, `Select`, `Skeleton`, `Table`, `TableWrap`, `Tabs`, `ThemeToggle`

Design tokens CSS via variables:
- Colores: `--background-app/surface/subtle/elevated/hover`, `--border-subtle/strong`, `--text-primary/secondary/muted/inverse`, `--accent/hover/soft/border`
- Estados: `--status-open/closing-soon/closed/awarded/risk` con fondos
- Tipografía: `--font-family-sans`, `--font-family-mono`
- Espaciado: `--space-1` a `--space-8`
- Radios: `--radius-sm/md/lg/xl/pill`
- Sombras: `--shadow-card/card-hover/table/surface-strong/panel/popover`
- Movimiento: `--motion-duration-fast/medium/slow`, `--motion-ease-standard/emphasized`

---

## 8. Configuración y Runtime

### 8.1 Configuración de Pipeline (`config/pipeline.yaml`)

```yaml
pipeline:
  raw_chunk_size: 5000
  normalized_fetch_size: 10000
  normalized_chunk_size: 500

mercado_publico_api:
  base_url: "https://api.mercadopublico.cl/servicios/v1/publico"
  endpoints:
    licitaciones: "/licitaciones.json"
  timeout_seconds: 30.0
  cache_ttl_seconds: 900
  rate_limit:
    daily_request_limit: 10000
  retry:
    max_attempts: 3
    base_backoff_seconds: 2
    cap_backoff_seconds: 120
  rolling_window:
    default_window_days: 4
  detail_enrichment:
    backfill_interval_days: 7
    max_candidates_default: null
```

### 8.2 Settings (`backend/core/config.py`)

Settings via pydantic-settings con `.env`:
- `APP_ENV`: `development` | `production`
- `DATABASE_URL`, `TEST_DATABASE_URL`
- `MERCADO_PUBLICO_API_ENABLED`, `MERCADO_PUBLICO_API_KEY`, `MERCADO_PUBLICO_BASE_URL`
- `MERCADO_PUBLICO_DAILY_REQUEST_LIMIT` (default 10000)
- `MERCADO_PUBLICO_TIMEOUT_SECONDS` (default 30)
- `MERCADO_PUBLICO_RETRY_BUDGET` (default 2)
- `MANUAL_UPLOAD_MAX_BYTES` (default 800MB)
- `INGESTION_QUEUE_MAX_ATTEMPTS` (default 2)
- `INGESTION_QUEUE_RETRY_DELAY_SECONDS` (default 120)
- `INGESTION_QUEUE_POLL_SECONDS` (default 5)

Validaciones en runtime:
- `DATABASE_URL` ≠ `TEST_DATABASE_URL`
- No mezclar host y Docker runtime families
- Producción rechaza credenciales default y hosts locales
- Rate limit ≥ 1, timeout > 0, retry budget ≥ 0

### 8.3 Docker Compose

Servicios:
- `db`: PostgreSQL 16 Alpine, puerto `5432` (localhost-bound), volumen `omnibid_pgdata`
- `api`: FastAPI en puerto `8000`, bind mount de datasets en `/datasets/mercado-publico` (read-only), non-root, no-new-privileges, read-only root fs
- `.env.docker`: variables de entorno canónicas para runtime local

### 8.4 Just Recipes (task runner)

- `just compose-up` — Levanta stack Docker
- `just docker-build` — Buildea imagen API
- `just docker-pipeline-full` — Pipeline completo (profile → ingest → normalized)
- `just docker-smoke` — Smoke test
- `just quality` — Quality gates
- `just ci-fast` / `just ci` — CI gates
- `just uv-sync` — Sincroniza dependencias Python

---

## 9. NLP Pipeline

**Ubicación:** `backend/nlp/`

### Componentes:
- `config.py` — Configuración de contratos NLP
- `runtime.py` — Validación de runtime y perfil de fuente
- `normalization.py` — Normalización de texto (limpieza, tokenización)
- `annotations.py` — Extracción de features (n-gramas, keywords, domain tags, semantic categories)
- `embeddings.py` — TF-IDF vectorization (solo referencias externas, no vectores serializados en Silver)
- `artifacts.py` — Manejo de artefactos NLP

### Configuración NLP (`config/nlp/`):
- `nlp_config_v1.json` — Configuración general
- `nlp_patterns_v1.json` — Patrones de dominio para keyword matching

### Contracto de anotaciones:
- Silver solo almacena referencias TF-IDF (`tfidf_artifact_ref`), no vectores serializados
- Campos prohibidos en Silver: `embedding_*`, `*_vector`, `tfidf_vector`, `tfidf_matrix`
- Las anotaciones son versionadas (`nlp_version`)

---

## 10. Principios de Diseño (Producto)

Del documento `PRODUCT.md`:

### Personalidad de marca
**Confidente, moderno, enfocado.** La interfaz debe sentirse precisa y opinada como una herramienta profesional (energía Linear/Stripe). Cada pixel sirve a la tarea. Sin decoración, sin vacilación.

### Principios de diseño
1. **Data-first clarity**: Tablas, métricas y filtros son el héroe — el chrome retrocede
2. **Earned familiarity**: Patrones estándar que los usuarios conocen (tabs, tablas, búsqueda, chips de filtro)
3. **Quiet confidence**: Superficies deliberadas y compuestas. Color de acento reservado para acción y selección
4. **Depth without noise**: Información densa legible mediante tipografía cuidadosa, espaciado y capas de superficie

### Anti-referencias
- Dashboards enterprise genéricos (Material Design defaults)
- Portales de gobierno legacy (tablas sin estilo, contraste pobre)
- Superficies de marketing llamativas (gradientes, glassmorphism, animaciones decorativas)

### Accesibilidad
- Objetivo WCAG 2.1 AA
- HTML semántico, ARIA labels en regiones interactivas
- Navegación por teclado completa
- Respeta `prefers-reduced-motion`

---

## 11. Roadmap y Estados del Proyecto

### Implementado (Fase 1):
- ✅ Bronze/Raw ingestion foundation
- ✅ Raw reliability y data-quality hardening
- ✅ Silver/Normalized core canonicalization
- ✅ Normalized domain modeling expansion (buyers, suppliers, categories)
- ✅ Silver procurement-cycle canonicalization
- ✅ Mercado Público API ingestion lane (rolling-window + detail enrichment)
- ✅ Silver NLP text annotations
- ✅ Manual CSV upload con progreso en tiempo real
- ✅ Opportunity Workspace MVP (read-only, radar + explorer)
- ✅ Ingestion queue foundation (pipeline_jobs, ingestion_units)
- ✅ Precomputed dataset summary snapshots

### Pendiente (Gold / Futuro):
- ⬜ Gold business aggregates
- ⬜ Predictive scoring (opportunity ranking, win probability)
- ⬜ Forecasting y anomaly detection
- ⬜ Agentes de IA y narrativa generada
- ⬜ Supabase cutover (readiness en progreso)
- ⬜ Procurement Investigation Workspace
- ⬜ Workflow de decisiones (no solo read-only)

---

## 12. Formato de Datos — Ejemplos de API Mercado Público

### Esquema de respuesta API (`LicitacionesResponse`):

```json
{
  "Codigo": 200,
  "Descripcion": "OK",
  "FechaCreacion": "15052026",
  "Cantidad": 150,
  "Listado": [
    {
      "CodigoExterno": "1234-56-LE25",
      "Nombre": "Adquisición de equipos computacionales",
      "CodigoEstado": 5,
      "Estado": "Publicada",
      "FechaPublicacion": "10052026",
      "FechaCierre": "25052026",
      "CodigoOrganismo": "ORG001",
      "NombreOrganismo": "Ministerio de Educación",
      "CodigoUnidad": "U001",
      "NombreUnidad": "Departamento de Adquisiciones",
      "Moneda": "CLP",
      "MontoEstimado": 50000000,
      "Descripcion": "Adquisición de 100 notebooks para establecimientos educacionales",
      "Tipo": "Licitación Pública",
      "CodigoTipo": "LP",
      "TipoConvocatoria": "Abierta",
      "Comprador": {
        "CodigoOrganismo": "ORG001",
        "NombreOrganismo": "Ministerio de Educación",
        "RutUnidad": "60.000.000-1",
        "CodigoUnidad": "U001",
        "NombreUnidad": "Departamento de Adquisiciones",
        "DireccionUnidad": "Alameda 1234",
        "ComunaUnidad": "Santiago",
        "RegionUnidad": "Metropolitana",
        "RutUsuario": "12.345.678-9",
        "CodigoUsuario": "USR001",
        "NombreUsuario": "Juan Pérez",
        "CargoUsuario": "Jefe de Adquisiciones"
      },
      "Fechas": {
        "FechaCreacion": "08052026",
        "FechaCierre": "25052026",
        "FechaPublicacion": "10052026",
        "FechaAdjudicacion": null,
        "FechaEstimadaAdjudicacion": "15062026"
      },
      "Items": {
        "Cantidad": 1,
        "Listado": [
          {
            "Correlativo": 1,
            "CodigoProducto": "43211500",
            "CodigoCategoria": "TEC001",
            "Categoria": "Tecnología",
            "NombreProducto": "Notebook",
            "Descripcion": "Notebook con procesador i7, 16GB RAM, 512GB SSD",
            "UnidadMedida": "Unidad",
            "Cantidad": "100"
          }
        ]
      },
      "Adjudicacion": {
        "Tipo": null,
        "Fecha": null,
        "Numero": null,
        "NumeroOferentes": 0
      },
      "Informada": "Si",
      "DiasCierreLicitacion": 15,
      "CantidadReclamos": 0,
      "FuenteFinanciamiento": "Fiscal",
      "VisibilidadMonto": "Visible"
    }
  ]
}
```

### Modos de consulta API:
1. **Active Discovery:** `?estado=activas&ticket=***`
2. **Rolling Window:** `?fecha=DDMMYYYY&ticket=***`
3. **Detail by Codigo:** `?codigo=XXXX-XX-XXXX&ticket=***`

---

## 13. Identidad y Contratos de Datos

### Business Keys:
- **Buyer key:** `buyer_key` = `CodigoUnidadCompra`
- **Supplier key:** `supplier_key` = precedencia `codigo:<CodigoProveedor>` → `rut:<RutProveedor>`
- **Category key:** `category_key` = `codigoCategoria`
- **Oferta key:** `oferta_key_sha256` = hash de codigo_externo + codigo_item + codigo_proveedor

### Merge Semantics:
- **Complete-only upsert:** Valores no-nulos existentes se preservan contra nulos/blancos entrantes
- Los payloads de `detail-by-codigo` tienen precedencia sobre `rolling-window` para la misma business key

### Silver Guardrails (enforced en upsert_engine.py):
- Columnas prohibidas en Silver: `opportunity_rank`, `opportunity_score`, `winnability_score`, `convenience_score`, `win_probability`, `award_probability`, `forecast_value`, `forecast_label`, `anomaly_verdict`, `recommendation_score`
- Sufijos prohibidos: `_score`, `_probability`, `_forecast`, `_prediction`, `_rank`
- Prefijos prohibidos: `future_`
- En anotaciones: solo referencias TF-IDF (`tfidf://...`), no vectores serializados

### Trazabilidad (Data Lineage):
Cada registro en raw, normalized y silver mantiene:
- `source_file_id` → el archivo o snapshot API que lo originó
- `row_hash_sha256` → hash del contenido de la fila
- `created_at` / `updated_at` → timestamps de auditoría
- Raw adicional: `batch_id`, `raw_row_num`, `raw_json` (JSON original completo)

---

## 14. Herramientas y Dependencias

### Backend (Python):
- **Framework:** FastAPI, Uvicorn
- **ORM:** SQLAlchemy 2.x con async support
- **Migraciones:** Alembic (17 revisiones)
- **Validación:** Pydantic v2, pydantic-settings
- **NLP:** spaCy (es_core_news_md), FastText, scikit-learn (TF-IDF)
- **Testing:** Pytest, pytest-asyncio
- **Linting/Types:** Ruff, MyPy, Pyright
- **Task Runner:** just
- **Package Manager:** uv

### Frontend (TypeScript):
- **Framework:** Next.js 15 (App Router)
- **UI:** React 19, Tailwind CSS 4
- **Iconos:** Lucide React
- **Testing:** Vitest
- **Package Manager:** pnpm (Corepack-pinned)

### Infraestructura:
- **Base de datos:** PostgreSQL 16 (Alpine Docker image)
- **Contenedores:** Docker Compose
- **CI/CD:** GitHub Actions

---

## 15. Notas para el Agente de Rediseño

### Perfil del usuario objetivo: **Analista de Licitaciones Públicas**

Un profesional que:
- Revisa diariamente decenas o cientos de licitaciones publicadas
- Necesita filtrar rápido por rubro, región, monto y etapa
- Compara oportunidades para decidir cuáles investigar a fondo
- Da seguimiento a licitaciones de interés (watchlist/radar)
- Analiza competencia: quién más está ofertando, a qué precios
- Verifica si una licitación ya tiene orden de compra (¿se adjudicó?)
- Exporta datos para análisis offline o reportes
- Puede cargar sus propios CSVs de datos históricos

### Puntos de dolor que la herramienta resuelve:
1. **Datos dispersos:** Unifica datos de API Mercado Público + CSVs en un solo lugar
2. **Falta de contexto:** Muestra líneas, ofertas, adjudicaciones y OCs vinculadas
3. **Seguimiento manual:** Watchlist local para dar seguimiento sin depender del portal
4. **Señales de certeza:** Indica qué tan confiable es el vínculo entre una licitación y sus OCs
5. **Estados claros:** Clasifica en etapas accionables (abierta, cierra pronto, cerrada, adjudicada)

### Lo que NO hace (por diseño):
- No asigna puntajes ni recomendaciones automáticas
- No reemplaza el portal ChileCompra (es herramienta de análisis)
- No permite editar datos canónicos
- No genera narrativa automática (sin AI scoring en esta fase)

### Idioma:
- **Toda la UI está en español**
- Backend DTOs usan camelCase para el frontend
- Base de datos usa snake_case (inglés técnico para nombres de columna)

---

*Documento generado el 2026-05-15 para proporcionar contexto completo a agentes de IA.*

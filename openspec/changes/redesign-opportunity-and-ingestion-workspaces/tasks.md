## Fase 0 — Discovery y auditoría

- [ ] 0.1 Releer la proposal OpenSpec actual, `PRODUCT.md`, `AGENTS.md`, docs de arquitectura y el README de screenshots como source set canónico.
  **Acceptance**: el agente confirma que entiende los límites del producto, la capa Silver/Gold y la regla de oro de clasificación de datos.
- [ ] 0.2 Completar `data-availability-audit.md` como fuente canónica de verdad para toda implementación.
  **Acceptance**: cada campo visible en los mockups tiene una fila con clasificación (`available_now`, `derivable_client_side`, `derivable_backend`, `requires_endpoint_extension`, `requires_new_table_or_view`, `requires_gold_layer`, `out_of_scope`).
- [ ] 0.3 Clasificar cada elemento de mockup según la regla de oro y congelar la matriz.
  **Acceptance**: ningún campo sin clasificación entra en fases posteriores.
- [ ] 0.4 Confirmar qué datos se pueden mostrar sin backend nuevo y qué mockups quedan reducidos por falta de datos.
  **Acceptance**: lista explícita de elementos `out_of_scope` o `requires_gold_layer` que no se implementan en esta proposal, incluyendo KPIs no directos o ambiguos (`Nuevas hoy`, `Cargas hoy`, `Cambios hoy`, `Alertas activas`, `Próximos vencimientos`, quick-analysis rail, `Errores activos`), y la política de faltantes queda clara: concepto no modelado = ocultar o marcar no disponible; campo opcional por registro = `Sin dato` o `-` según densidad.
- [ ] 0.5 Responder las 4 preguntas abiertas del `design.md` (ruta de Ingestion Center, alcance de Priorización, documentos, API diagnostics).
  **Acceptance**: cada pregunta tiene una decisión documentada en `design.md` o `risks.md`.
- [ ] 0.6 Clasificar los affordances de acción y navegación del mockup (refresh, export, print, drill-down, comparison, proveedores, alertas, programación y reproceso) para cubrir botones además de datos.
  **Acceptance**: cada CTA queda etiquetado y los controles mutables u orquestadores se marcan como fuera de alcance o como trabajo futuro explícito.
- [ ] 0.7 Congelar la lista de rutas y navegación v1.
  **Acceptance**: solo `Oportunidades` y `Centro de Ingesta` quedan activos; destinos amplios del mockup (`Contratos`, `Proveedores`, `Reportes`, `Alertas`, `Integraciones`, `Configuración`) quedan omitidos o deshabilitados como futuros.
- [ ] 0.8 Escribir pruebas baseline antes de tocar UI o backend.
  **Acceptance**: existen pruebas que capturan el comportamiento actual de `/licitaciones`, view-state, summary metrics API-backed, watchlist local, y flujo manual de CSV upload; si no existe harness suficiente, documentar el baseline mínimo y crearlo antes de implementar fases 1-7.

## Fase 1 — Design system y layout base

- [ ] 1.1 Consolidar tokens visuales desde `client/src/styles/tokens.css` y los estándares de diseño del repo.
  **Acceptance**: los tokens de color, tipografía, espaciado y motion están documentados y son reutilizables.
- [ ] 1.2 Crear/ajustar componentes base reutilizables: KPI cards, status badges, filter chips, tabs, side panels, tables, empty states, timeline rows, progress rows.
  **Acceptance**: cada componente tiene un contrato de props claro, estados `loading`/`empty`/`error`/`unavailable` definidos, y se puede usar tanto en Opportunity Workspace como en Ingestion Center.
- [ ] 1.3 Definir el vocabulario de estados de disponibilidad: `Sin dato`, `Cobertura parcial`, y estados source-backed.
  **Acceptance**: el UI System expone un helper o componente que recibe `availability` y renderiza el estado correcto.
- [ ] 1.4 Shapear el app shell con sidebar, header y layout para que `/licitaciones` e `Ingestion Center` compartan navegación sin compartir responsabilidades de datos.
  **Acceptance**: el shell renderiza correctamente en desktop-first (1920px → 1280px) y el sidebar tiene las entradas `Oportunidades` e `Ingesta`.
- [ ] 1.5 Sin cambiar contratos API en esta fase.
  **Acceptance**: los endpoints actuales siguen funcionando sin modificaciones.
- [ ] 1.6 Tests primero para estados de disponibilidad y shell.
  **Acceptance**: antes de cambiar componentes compartidos, agregar o actualizar pruebas de `loading`/`empty`/`error`/`unavailable`, labels en español, y navegación activa/inactiva.

## Fase 2 — Workspace de oportunidades v1 (Lista + Tabla + panel lateral)

- [ ] 2.1 Rediseñar la vista `Lista` usando solo campos que ya existen en los contratos actuales de `/opportunities`.
  **Acceptance**: cada row muestra título, código, estado oficial, tipo, comprador, región, fechas, monto estimado, días restantes y categoría — con `Sin dato` donde falte.
- [ ] 2.2 Añadir `Tabla` como modo de presentación densa sobre los mismos datos, no como dataset separado.
  **Acceptance**: filtros, ordenamiento y selección se preservan al cambiar entre `Lista` y `Tabla`.
- [ ] 2.3 Refinar el panel lateral de detalle como paquete de evidencia con estados de disponibilidad explícitos por sección.
  **Acceptance**: el drawer muestra datos oficiales, timeline, líneas, ofertas, OCs y marca `Sin dato` en documentos/bases/anexos.
- [ ] 2.4 Mantener la ruta `/licitaciones` y los contratos de URL state actuales.
  **Acceptance**: deep links existentes siguen funcionando; `localStorage` watchlist se preserva.
- [ ] 2.5 Exponer chips de cobertura activa (ej. filtro `source_view=publicadas`) y visibilidad del monto como badge informativo.
  **Acceptance**: el usuario ve cuándo está filtrando por cobertura y la visibilidad del monto se muestra como campo cualitativo.
- [ ] 2.6 Tests primero para `Lista`, `Tabla` y drawer.
  **Acceptance**: antes de implementar la nueva UI, las pruebas fijan que `Lista` y `Tabla` comparten dataset/filtros, no sintetizan KPIs desde la página, preservan selección/deep links, y muestran documentos/bases/anexos como `Sin dato`.

## Fase 3 — Priorización y seguimiento v1

- [ ] 3.1 Implementar `Priorización` con buckets determinísticos derivables de campos existentes: "Revisar hoy" (cierre ≤2 días), "Cierra esta semana" (cierre ≤7 días), "Abierta con plazo", "En radar".
  **Acceptance**: cada bucket tiene una regla explícita documentada; no hay scores numéricos, editor de criterios ponderados ni predicciones.
- [ ] 3.2 No incluir `Decision Brief` ni `Por qué revisar` como texto generado en v1. Dejar como placeholder `Sin dato` hasta que exista un contrato de síntesis determinística.
  **Acceptance**: las secciones de brief y review están marcadas como futuras, sin texto inventado, y el rail de criterios ponderados permanece fuera de v1.
- [ ] 3.3 Mantener `Seguimiento` como watchlist local (`localStorage`) con copia explícita de que es local-session.
  **Acceptance**: el usuario ve "Seguimiento local — no persistido entre dispositivos" o equivalente.
- [ ] 3.4 Añadir chips de alerta solo para señales determinísticas: cierre inminente, reclamos activos, banderas oficiales (`multiple_stages_flag`, `hidden_budget_flag`).
  **Acceptance**: cada alerta tiene source field y regla documentada; no hay "sistema de alertas" genérico.
- [ ] 3.5 Tests primero para Priorización y Seguimiento.
  **Acceptance**: las pruebas fallan si aparece `Puntaje`, editor de criterios, score ordering, alert delivery, trend sparklines, drag/drop, asignación, etiquetas, o seguimiento persistido entre dispositivos.

## Fase 4 — Detalle completo

- [ ] 4.1 Crear vista de detalle dedicada usando los campos ya expuestos por `GET /opportunities/{notice_id}`.
  **Acceptance**: datos oficiales, timeline, buyer, líneas, ofertas, y OCs visibles con sus estados de disponibilidad.
- [ ] 4.2 Marcar documentos, bases y anexos como `Sin dato — requiere registro documental futuro`.
  **Acceptance**: no se inventan documentos ni se insinúa que existen.
- [ ] 4.3 Incluir `Buyer history snapshot` como derivación determinística si `silver_notice` + `silver_purchase_order` alcanzan; si no, mostrar `Sin historial suficiente`.
  **Acceptance**: el snapshot se deriva de datos reales o se marca como no disponible.
- [ ] 4.4 Exponer `Actividad reciente` desde el timeline actual + metadatos de runs si están disponibles; `Cambios hoy` queda como `Sin dato` hasta que exista daily snapshot.
  **Acceptance**: la actividad reciente es event-based, no predicción de tendencia.
- [ ] 4.5 Tests primero para detalle completo.
  **Acceptance**: las pruebas fijan que `Decision Brief`, `Por qué revisar`, `Descargar expediente completo`, documentos, alertas, compartir, comparar, carpeta y proveedores drill-down se renderizan como no disponibles/futuros salvo que exista contrato source-backed.

## Fase 5 — Centro de ingesta v1 (overview + carga CSV)

- [ ] 5.1 Extraer el flujo actual de CSV upload a una superficie dedicada (`/ingesta`) con los mismos endpoints de preflight, proceso y job polling.
  **Acceptance**: el flujo de upload funciona idéntico al actual pero vive en `/ingesta`, no en `/licitaciones`.
- [ ] 5.2 Añadir overview operativo usando `GET /runs`, `GET /files`, `GET /datasets/summary`.
  **Acceptance**: KPI cards muestran ejecuciones recientes, archivos procesados y snapshot freshness.
- [ ] 5.3 Implementar vista de historial de runs con expand para steps, batches y lineage.
  **Acceptance**: cada run muestra source file, estado terminal, steps y telemetría disponible; el historial se presenta como una ventana acotada con rango visible y no como una lista infinita.
- [ ] 5.4 Exponer trazabilidad y reproducibilidad con file hash, run ID y source metadata.
  **Acceptance**: un operador puede trazar un job desde source file hasta silver rows.
- [ ] 5.5 Tests primero para `/ingesta` CSV.
  **Acceptance**: las pruebas fijan que las únicas mutaciones permitidas son seleccionar CSV, preflight, procesar el archivo staged y polling del job; programación, notas, descargas no respaldadas y orquestación API quedan deshabilitadas o `Sin dato`.

## Fase 6 — Centro de ingesta API + logs + historial

- [ ] 6.1 Añadir lane de API diagnostics solo para datos sourcedos de `api_source_request`: conteo de llamadas, último status HTTP, rate limit del día.
  **Acceptance**: si el modelo `api_source_request` no expone el campo, se muestra `Sin dato`.
- [ ] 6.2 Exponer logs en vivo y errores activos solo si existe un endpoint de `pipeline_runs.error_summary` + `data_quality_issues` con ventana de tiempo definida.
  **Acceptance**: sin endpoint, se muestra estado no disponible con mensaje explícito.
- [ ] 6.3 Worker activo y archivos en cola quedan como `Sin dato — visibilidad de runtime no implementada`.
  **Acceptance**: no se inventa un worker status; se deja el placeholder documentado.
- [ ] 6.4 Implementar vista de payload/log/reproceso como read-only y provenance-heavy solo si los datos existen en `api_source_payload`.
  **Acceptance**: no se promete replay; solo se muestra lo que ya está persistido.
- [ ] 6.5 Añadir sección de incidencias con datos de `DataQualityIssue` si existe un endpoint; si no, `Sin dato`.
  **Acceptance**: la sección de incidencias tiene un umbral de tiempo definido o se marca como no disponible.
- [ ] 6.6 Notas operativas solo si se añade campo `operator_notes` en `pipeline_runs`; si no, `Sin dato`.
  **Acceptance**: no se inventa campo de notas.
- [ ] 6.7 Tests primero para API/logs/historial.
  **Acceptance**: las pruebas fallan si se muestran live logs, worker activo, latencia, retry/replay/reproceso, endpoint creation, schedule editing, o notas como disponibles sin endpoint/tabla explícita.

## Fase 7 — Backend/API extensions (solo si el audit lo justifica)

- [ ] 7.1 Añadir endpoint mínimo para `Nuevas hoy` (count de notices con `publication_date = today`) si se decide incluir el KPI.
  **Acceptance**: el endpoint devuelve un count respaldado por `silver_notice.publication_date`, no una estimación.
- [ ] 7.2 Añadir endpoint mínimo para `Cargas hoy` solo si una propuesta futura lo reinstala con una ventana temporal explícita.
  **Acceptance**: el endpoint devuelve un count respaldado por `pipeline_runs` y el contrato publica la ventana de tiempo en el label; esta proposal no depende de él.
- [ ] 7.3 Exponer campos de `api_source_request` necesarios para diagnostics si el audit los marca como `requires_endpoint_extension`.
  **Acceptance**: cada campo nuevo tiene un modelo DTO y una query source-backed.
- [ ] 7.4 Añadir migraciones Alembic solo si se crean nuevas tablas, vistas materializadas o columnas (ej. `operator_notes` en `pipeline_runs`).
  **Acceptance**: cada migración es atómica, versionada y documentada en el changelog de Alembic.
- [ ] 7.5 No crear tablas Gold. Cualquier campo `*_score`, `*_probability`, `forecast_*` o `recommendation_*` se rechaza en esta fase.
  **Acceptance**: zero predictive fields in new backend code.
- [ ] 7.6 Tests de contrato antes de cada extensión backend.
  **Acceptance**: cada endpoint nuevo o extendido tiene prueba roja/baseline previa que verifica source table, availability metadata, empty state, and no page-derived fake metrics.

## Fase 8 — Tests, docs y validación

- [ ] 8.1 Tests unitarios frontend para cambio de vistas, estados de disponibilidad, watchlist local, y flujo de upload.
  **Acceptance**: `pnpm test` pasa sin errores; coverage no disminuye.
- [ ] 8.2 Tests de contratos para cualquier endpoint nuevo o extendido.
  **Acceptance**: ruta container-first equivalente pasa (`rtk just test-unit`, `rtk just ci-fast`, o receta `just` disponible); host-local `uv run pytest tests/unit/ -k "opportunities or operations"` solo se usa como fallback documentado si el contenedor no está disponible.
- [ ] 8.3 Tests de integración para nuevos endpoints backend si se añadieron en Fase 7.
  **Acceptance**: Docker-first smoke con `just docker-smoke` (si existe) o equivalente.
- [ ] 8.4 Correr quality gates: `just ci-fast` o equivalente (lint, typecheck, build).
  **Acceptance**: `rtk just ci-fast` o receta container-first equivalente corre sin errores de lint, typecheck y build; si se usa fallback host-local, documentar la razón.
- [ ] 8.5 Actualizar `PRODUCT.md`, docs de arquitectura y `CHANGELOG.md` con los nuevos surfaces, límites y reglas de disponibilidad.
  **Acceptance**: un nuevo developer puede leer los docs y entender qué datos están disponibles y cuáles son futuros.
- [ ] 8.6 Ejecutar o recomendar `openspec validate` si el comando existe en el repo.
  **Acceptance**: la proposal pasa validación OpenSpec sin errores.

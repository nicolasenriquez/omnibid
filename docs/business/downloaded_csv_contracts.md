# Downloaded CSV Contracts

## Purpose
Document the contracts observed in the Datos Abiertos monthly downloads. These are observations from the download interface, not immutable guarantees.

## Audience
- ingestion and normalization implementers
- agents that must map CSV batches without inventing headers

## Official sources
- [Datos Abiertos site](https://datos-abiertos.chilecompra.cl/)
- [Datos Abiertos page](https://www.chilecompra.cl/datos-abiertos/)

## Licitaciones CSV mensual

### Observed columns
- CodigoExterno
- Tipo de Adquisicion
- FuenteFinanciamiento
- FechaPublicacion
- FechaAdjudicacion
- Estado
- NombreUnidad
- Nombre producto generico
- NombreProveedor
- Nombre de la Oferta
- CantidadAdjudicada
- Oferta seleccionada

### Grain hypothesis
Una fila puede representar una combinacion de licitacion, item/producto, proveedor/oferta y adjudicacion.
Validar contra un CSV real antes de fijar el grain.

### Mapping candidate
- `CodigoExterno` -> `notice_id` / `codigo_externo`
- `NombreUnidad` -> contracting unit display
- `Nombre producto generico` -> notice line / product text
- `NombreProveedor` -> supplier display
- `CantidadAdjudicada` -> award quantity
- `Oferta seleccionada` -> selected offer flag

### Validation tasks
- download one recent monthly CSV
- verify exact headers
- count rows per `CodigoExterno`
- count items per licitacion
- validate whether non-selected offers appear
- validate whether one row can duplicate items, offers, or awards

## Ordenes de Compra CSV mensual

### Observed columns
- Codigo
- FechaEnvio
- Estado
- DescripcionTipoOC
- TipoMonedaOC
- MontoTotalOC
- ImpuestosOC
- CodigoLicitacion
- UnidadCompra
- NombreProveedor
- CodigoProductoONU
- TotalLineaNeto

### Grain hypothesis
Una fila puede representar una linea de orden de compra o una OC con producto ONU asociado.
Validar contra un CSV real antes de fijar el grain.

### Mapping candidate
- `Codigo` -> `purchase_order_id` / `codigo_oc`
- `FechaEnvio` -> `order_sent_at`
- `Estado` -> `purchase_order_status`
- `DescripcionTipoOC` -> `purchase_order_type`
- `TipoMonedaOC` -> `currency`
- `MontoTotalOC` -> `purchase_order_total_amount`
- `ImpuestosOC` -> `tax_amount`
- `CodigoLicitacion` -> optional `notice_id` link
- `UnidadCompra` -> contracting unit display
- `NombreProveedor` -> supplier display
- `CodigoProductoONU` -> `onu_product_code`
- `TotalLineaNeto` -> `line_net_total`

### Validation tasks
- download one recent monthly CSV
- verify whether `Codigo` repeats across multiple lines
- validate whether `CodigoLicitacion` is empty for non-tender purchases
- validate cardinality `Codigo -> CodigoProductoONU`
- validate line totals against order totals
- validate encoding, separator, quotes, and variable columns

## Validation checklist
- Keep the observed download contract separate from the API contract.
- Revalidate headers by dataset, month, and year.
- Document drift in `docs/evidence/`.

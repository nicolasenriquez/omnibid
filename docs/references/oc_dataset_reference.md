# OC Dataset Reference (202601-oc / 202604-oc)

This repository version includes normalized mappings aligned to the OC CSV schema used in:

- `202601-oc.csv`
- `202604-oc.csv`

## Raw granularity

Raw rows are treated as **order + item** grain (not one row per order).

## Header business key

- `Codigo` -> `normalized_ordenes_compra.codigo_oc`

## Item business key

- `(Codigo, IDItem)` -> `normalized_ordenes_compra_items (codigo_oc, id_item)`

## Included OC header fields (high-level)

- order identity/state/type:
  - `ID`, `Codigo`, `Tipo`, `ProcedenciaOC`, `DescripcionTipoOC`, `Estado`, `EstadoProveedor`
- dates:
  - `FechaCreacion`, `FechaEnvio`, `FechaSolicitudCancelacion`, `FechaAceptacion`, `FechaCancelacion`, `fechaUltimaModificacion`
- amount/payment:
  - `MontoTotalOC`, `MontoTotalOC_PesosChilenos`, `Impuestos`, `Descuentos`, `Cargos`, `TotalNetoOC`, `TipoMonedaOC`, `FormaPago` / `Forma de Pago`
- relationship:
  - `CodigoLicitacion`, `Codigo_ConvenioMarco`
- buyer:
  - `CodigoUnidadCompra`, `RutUnidadCompra`, `UnidadCompra`, `CodigoOrganismoPublico`, `OrganismoPublico`, `sector`, `ActividadComprador`, `CiudadUnidadCompra`, `RegionUnidadCompra`, `PaisUnidadCompra`
- supplier:
  - `CodigoProveedor`, `NombreProveedor`, `ActividadProveedor`, `CodigoSucursal`, `RutSucursal`, `Sucursal`, `ComunaProveedor`, `RegionProveedor`, `PaisProveedor`

## Included OC item fields (high-level)

- item identity:
  - `IDItem`, `codigoCategoria`, `Categoria`, `codigoProductoONU`
- product/spec:
  - `NombreroductoGenerico`, `RubroN1`, `RubroN2`, `RubroN3`, `EspecificacionComprador`, `EspecificacionProveedor`
- quantity/amount:
  - `cantidad`, `UnidadMedida`, `monedaItem`, `precioNeto`, `totalCargos`, `totalDescuentos`, `totalImpuestos`, `totalLineaNeto`

## Canonicalization rules

- numeric parsing supports comma decimals and scientific notation.
- boolean parsing supports `1/0`, `true/false`, `si/no`, `yes/no`.
- null-like values (`NA`, empty, sentinel date values) are normalized to null.
- `Forma de Pago` is preferred over `FormaPago` if both are present.

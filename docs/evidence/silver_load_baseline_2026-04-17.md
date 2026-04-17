# Silver Load Baseline and Edge Cases (Tasks 1.1-1.2)

Date: 2026-04-16

## Scope

- Baseline on one licitaciones file and one orden-compra file using the current Silver builders.
- Measured builder outputs and unique business keys at file level.
- Identified parse edge cases for numeric/date/boolean fields.
- Note: DB-level upsert telemetry could not be measured in this sandbox due blocked localhost:5432 connectivity.

## Selected Files

- Licitaciones: `/Users/NicolasEnriquez/Desktop/App ChileCompra/dataset-mercado-publico/licitacion/202601_lic.csv`
- Ordenes de compra: `/Users/NicolasEnriquez/Desktop/App ChileCompra/dataset-mercado-publico/orden-compra/202604-oc.csv`

## 1.1 Baseline Results

### Licitaciones
- File rows: **116,658**
- Transform exceptions: **0**
- Header payloads built: **116,658** (unique `codigo_externo`: **7,149**) 
- Item payloads built: **116,658** (unique `(codigo_externo,codigo_item)`: **31,414**) 
- Oferta payloads built: **116,658** (unique `oferta_key_sha256`: **116,440**) 

### Ordenes de compra
- File rows: **208,252**
- Transform exceptions: **0**
- Header payloads built: **208,252** (unique `codigo_oc`: **71,082**) 
- Item payloads built: **208,252** (unique `(codigo_oc,id_item)`: **208,252**) 

## 1.2 Parsing Edge Cases

### Licitaciones parse edge cases
- No parse edge failures detected in this file.

### Ordenes de compra parse edge cases
- No parse edge failures detected in this file.

## Interpretation

- Builder-level mapping is stable for both selected files (no exceptions observed).
- Parse edge failures were not observed for the selected fields/files, so hardening will focus on stricter contracts and explicit rejection accounting for future schema drift.
- Unique key counts confirm item-grain raw data and reinforce explicit business-key upsert behavior.

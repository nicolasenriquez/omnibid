# Silver Procurement Cycle Grain Baseline

Date: 2026-04-22

## Scope

Validate actual source-row grain for the next Silver expansion proposal, using parser-level CSV reads (not physical line counts) on local source files:

- `/Users/NicolasEnriquez/Desktop/App ChileCompra/dataset-mercado-publico/licitacion/202603_lic.csv`
- `/Users/NicolasEnriquez/Desktop/App ChileCompra/dataset-mercado-publico/orden-compra/202604-oc.csv`

This baseline confirms modeling assumptions for:
- process entity separation
- optional notice-to-OC linkage
- supplier participation grain

## Method

Command used (executed on 2026-04-22):

```bash
uv run python - <<'PY'
import csv
from pathlib import Path

def clean(v):
    if v is None:
        return ""
    t = v.strip().strip('"').strip()
    if t.upper() in {"", "NA", "N/A", "NULL"}:
        return ""
    return t

def open_reader(path):
    for enc in ("utf-8-sig", "latin-1", "cp1252"):
        try:
            f = path.open("r", encoding=enc, newline="")
            r = csv.DictReader(f, delimiter=";")
            _ = r.fieldnames
            return f, r, enc
        except UnicodeDecodeError:
            try:
                f.close()
            except Exception:
                pass
    raise RuntimeError(f"encoding not detected for {path}")

lic = Path("/Users/NicolasEnriquez/Desktop/App ChileCompra/dataset-mercado-publico/licitacion/202603_lic.csv")
oc = Path("/Users/NicolasEnriquez/Desktop/App ChileCompra/dataset-mercado-publico/orden-compra/202604-oc.csv")

f, r, enc = open_reader(lic)
with f:
    rows = 0
    notices = set()
    notice_lines = set()
    notice_line_supplier = set()
    for row in r:
        rows += 1
        n = clean(row.get("CodigoExterno"))
        i = clean(row.get("Codigoitem")) or clean(row.get("CodigoItem"))
        s = clean(row.get("CodigoProveedor"))
        if n:
            notices.add(n)
        if n and i:
            notice_lines.add((n, i))
            if s:
                notice_line_supplier.add((n, i, s))
print("lic_encoding", enc)
print("lic_rows", rows)
print("lic_unique_notice", len(notices))
print("lic_unique_notice_line", len(notice_lines))
print("lic_unique_notice_line_supplier", len(notice_line_supplier))

f, r, enc = open_reader(oc)
with f:
    rows = 0
    po = set()
    po_lines = set()
    linked_rows = 0
    linked_notices = set()
    for row in r:
        rows += 1
        p = clean(row.get("Codigo"))
        li = clean(row.get("IDItem"))
        n = clean(row.get("CodigoLicitacion"))
        if p:
            po.add(p)
        if p and li:
            po_lines.add((p, li))
        if n:
            linked_rows += 1
            linked_notices.add(n)
print("oc_encoding", enc)
print("oc_rows", rows)
print("oc_unique_po", len(po))
print("oc_unique_po_lines", len(po_lines))
print("oc_rows_with_linked_notice", linked_rows)
print("oc_linked_notice_unique", len(linked_notices))
print("oc_linked_row_pct", round(100.0 * linked_rows / rows, 2))
PY
```

## Results

### Licitaciones (`202603_lic.csv`)

- Encoding detected: `latin-1`
- Logical rows: `104,844`
- Unique notices (`CodigoExterno`): `5,332`
- Unique notice-line combinations (`CodigoExterno`, `Codigoitem`): `25,300`
- Unique notice-line-supplier combinations (`CodigoExterno`, `Codigoitem`, `CodigoProveedor`): `104,390`

Interpretation:
- Source row grain is not "one row per notice."
- Supplier-level offer participation is part of row identity.
- Canonical notice, line, bid, and award entities should be separated in Silver.

### Purchase Orders (`202604-oc.csv`)

- Encoding detected: `latin-1`
- Logical rows: `208,252`
- Unique purchase orders (`Codigo`): `71,082`
- Unique purchase-order lines (`Codigo`, `IDItem`): `208,252`
- Rows with linked notice code (`CodigoLicitacion` non-null): `72,920`
- Unique linked notices (`CodigoLicitacion`): `14,618`
- Linked-row ratio: `35.02%`

Interpretation:
- Source row grain behaves as purchase-order-line.
- Notice linkage exists but is optional.
- Silver must represent explicit optional notice-to-OC linking (not mandatory FK at row level).

## Decision Impact

This evidence directly supports the next-stage proposal:
- full procurement-cycle canonical entities in Silver
- explicit bridge for notice-to-purchase-order links
- deterministic feature engineering foundations without predictive scoring in Silver

from __future__ import annotations

from typing import Any

from backend.normalized.transform_common import pick


def resolve_buyer_identity_key(raw: dict[str, Any]) -> str | None:
    return pick(raw, "CodigoUnidadCompra")


def resolve_supplier_identity_key(raw: dict[str, Any]) -> str | None:
    codigo_proveedor = pick(raw, "CodigoProveedor")
    if codigo_proveedor is not None:
        return f"codigo:{codigo_proveedor}"

    rut_proveedor = pick(raw, "RutProveedor")
    if rut_proveedor is not None:
        return f"rut:{rut_proveedor}"
    return None


def resolve_category_identity_key(raw: dict[str, Any]) -> str | None:
    category_code = pick(raw, "codigoCategoria")
    if category_code is not None:
        return category_code

    onu_code = pick(raw, "codigoProductoONU", "CodigoProductoONU")
    if onu_code is not None:
        # Prefix ONU fallback keys to avoid collisions with native category codes.
        return f"onu:{onu_code}"
    return None


def resolve_buying_org_identity_key(raw: dict[str, Any]) -> str | None:
    return pick(raw, "CodigoOrganismoPublico", "CodigoOrganismo")


def resolve_contracting_unit_identity_key(raw: dict[str, Any]) -> str | None:
    return pick(raw, "CodigoUnidadCompra", "CodigoUnidad")


def resolve_category_ref_identity_key(raw: dict[str, Any]) -> str | None:
    category_code = pick(raw, "codigoCategoria")
    if category_code is not None:
        return f"cat:{category_code}"

    onu_code = pick(raw, "codigoProductoONU", "CodigoProductoONU")
    if onu_code is not None:
        return f"onu:{onu_code}"
    return None

from __future__ import annotations

import importlib.util
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "build_nlp_annotations.py"
SPEC = importlib.util.spec_from_file_location("build_nlp_annotations_script", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load build_nlp_annotations module from {SCRIPT_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_build_annotation_record_emits_only_present_payloads() -> None:
    raw = {
        "CodigoExterno": "N-1",
        "Descripcion": "Servicio de mantencion y soporte de software",
        "Descripcion linea Adquisicion": "Mantencion de red y soporte tecnico",
        "Codigoitem": "IT-1",
        "Codigo": "OC-1",
        "IDItem": "1",
        "EspecificacionComprador": "Mantencion de red",
        "EspecificacionProveedor": "Soporte tecnico",
    }
    record = MODULE.build_annotation_record(
        raw,
        UUID("12345678-1234-5678-1234-567812345678"),
    )

    assert record["source_file_id"] == "12345678-1234-5678-1234-567812345678"
    assert record["row_hash_sha256"]
    assert {item["kind"] for item in record["payloads"]} == {
        "notice_text_ann",
        "notice_line_text_ann",
        "purchase_order_line_text_ann",
    }

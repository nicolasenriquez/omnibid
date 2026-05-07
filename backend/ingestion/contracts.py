from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_DATASET_TYPES: frozenset[str] = frozenset({"licitacion", "orden_compra"})


REQUIRED_COLUMNS: dict[str, set[str]] = {
    "licitacion": {
        "Codigo",
        "CodigoExterno",
        "Tipo de Adquisicion",
        "FechaPublicacion",
        "FechaCierre",
        "Codigoitem",
    },
    "orden_compra": {
        "Codigo",
        "FechaEnvio",
        "Estado",
        "DescripcionTipoOC",
        "IDItem",
        "codigoProductoONU",
        "totalLineaNeto",
    },
}


@dataclass(frozen=True)
class ContractValidationResult:
    dataset_type: str
    missing_required_columns: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing_required_columns


def normalize_dataset_type(dataset_type: str) -> str:
    normalized = dataset_type.strip().lower()
    if normalized not in SUPPORTED_DATASET_TYPES:
        raise ValueError(f"unsupported dataset type: {dataset_type}")
    return normalized


def validate_required_columns(dataset_type: str, columns: list[str]) -> ContractValidationResult:
    normalized_dataset_type = normalize_dataset_type(dataset_type)
    required = REQUIRED_COLUMNS[normalized_dataset_type]
    available = set(columns)
    missing = tuple(sorted(required - available))
    return ContractValidationResult(dataset_type=normalized_dataset_type, missing_required_columns=missing)


def assert_required_columns(dataset_type: str, columns: list[str], file_name: str) -> None:
    result = validate_required_columns(dataset_type, columns)
    if result.ok:
        return

    missing = ", ".join(result.missing_required_columns)
    raise ValueError(
        f"Missing required columns for dataset={dataset_type} file={file_name}: {missing}"
    )

import pytest

from backend.ingestion.contracts import assert_required_columns, validate_required_columns


def test_validate_required_columns_ok_for_licitacion() -> None:
    columns = [
        "Codigo",
        "CodigoExterno",
        "Tipo de Adquisicion",
        "FechaPublicacion",
        "FechaCierre",
        "Codigoitem",
    ]
    result = validate_required_columns("licitacion", columns)
    assert result.ok is True
    assert result.missing_required_columns == ()


def test_assert_required_columns_raises_on_missing_columns() -> None:
    columns = ["Codigo", "CodigoExterno"]
    with pytest.raises(ValueError, match="Missing required columns"):
        assert_required_columns("licitacion", columns, "test.csv")

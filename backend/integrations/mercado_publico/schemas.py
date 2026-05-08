from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _parse_optional_date(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return value

    normalized = value.strip()
    if not normalized:
        return None
    if normalized.isdigit() and len(normalized) == 8:
        return datetime.strptime(normalized, "%d%m%Y").date()
    if len(normalized) == 10 and normalized[4] == "-" and normalized[7] == "-":
        return date.fromisoformat(normalized)
    if normalized.count("/") == 2:
        return datetime.strptime(normalized, "%d/%m/%Y").date()
    if "T" in normalized:
        iso_value = normalized.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(iso_value).date()
        except ValueError:
            return value
    return value


class LicitacionNotice(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    external_notice_code: str | None = Field(default=None, alias="CodigoExterno")
    title: str | None = Field(default=None, alias="Nombre")
    official_status_code: int | None = Field(default=None, alias="CodigoEstado")
    official_status_name: str | None = Field(default=None, alias="Estado")
    publication_date: date | None = Field(default=None, alias="FechaPublicacion")
    close_date: date | None = Field(default=None, alias="FechaCierre")
    buyer_org_code: str | None = Field(default=None, alias="CodigoOrganismo")
    buyer_org_name: str | None = Field(default=None, alias="NombreOrganismo")
    buyer_unit_code: str | None = Field(default=None, alias="CodigoUnidad")
    buyer_unit_name: str | None = Field(default=None, alias="NombreUnidad")
    currency_code: str | None = Field(default=None, alias="Moneda")
    estimated_amount: Decimal | None = Field(default=None, alias="MontoEstimado")

    @field_validator("publication_date", "close_date", mode="before")
    @classmethod
    def _validate_dates(cls, value: Any) -> Any:
        return _parse_optional_date(value)


class LicitacionesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    code: int | None = Field(default=None, alias="Codigo")
    description: str | None = Field(default=None, alias="Descripcion")
    created_at: date | None = Field(default=None, alias="FechaCreacion")
    count: int = Field(default=0, alias="Cantidad")
    notices: list[LicitacionNotice] = Field(
        default_factory=lambda: cast(list[LicitacionNotice], []),
        alias="Listado",
    )

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: Any) -> Any:
        return _parse_optional_date(value)


def parse_licitaciones_response(payload: Mapping[str, Any]) -> LicitacionesResponse:
    return LicitacionesResponse.model_validate(payload)

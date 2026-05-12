from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class CompradorPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    codigo_organismo: str | None = Field(default=None, alias="CodigoOrganismo")
    nombre_organismo: str | None = Field(default=None, alias="NombreOrganismo")
    rut_unidad: str | None = Field(default=None, alias="RutUnidad")
    codigo_unidad: str | None = Field(default=None, alias="CodigoUnidad")
    nombre_unidad: str | None = Field(default=None, alias="NombreUnidad")
    direccion_unidad: str | None = Field(default=None, alias="DireccionUnidad")
    comuna_unidad: str | None = Field(default=None, alias="ComunaUnidad")
    region_unidad: str | None = Field(default=None, alias="RegionUnidad")
    rut_usuario: str | None = Field(default=None, alias="RutUsuario")
    codigo_usuario: str | None = Field(default=None, alias="CodigoUsuario")
    nombre_usuario: str | None = Field(default=None, alias="NombreUsuario")
    cargo_usuario: str | None = Field(default=None, alias="CargoUsuario")


class FechasPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    fecha_creacion: date | None = Field(default=None, alias="FechaCreacion")
    fecha_cierre: date | None = Field(default=None, alias="FechaCierre")
    fecha_inicio: date | None = Field(default=None, alias="FechaInicio")
    fecha_final: date | None = Field(default=None, alias="FechaFinal")
    fecha_pub_respuestas: date | None = Field(default=None, alias="FechaPubRespuestas")
    fecha_acto_apertura_tecnica: date | None = Field(default=None, alias="FechaActoAperturaTecnica")
    fecha_acto_apertura_economica: date | None = Field(default=None, alias="FechaActoAperturaEconomica")
    fecha_publicacion: date | None = Field(default=None, alias="FechaPublicacion")
    fecha_adjudicacion: date | None = Field(default=None, alias="FechaAdjudicacion")
    fecha_estimada_adjudicacion: date | None = Field(default=None, alias="FechaEstimadaAdjudicacion")

    @field_validator(
        "fecha_creacion", "fecha_cierre", "fecha_inicio", "fecha_final",
        "fecha_pub_respuestas", "fecha_acto_apertura_tecnica",
        "fecha_acto_apertura_economica", "fecha_publicacion",
        "fecha_adjudicacion", "fecha_estimada_adjudicacion",
        mode="before",
    )
    @classmethod
    def _validate_dates(cls, value: Any) -> Any:
        return _parse_optional_date(value)


class ItemPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    correlativo: int | None = Field(default=None, alias="Correlativo")
    codigo_producto: str | None = Field(default=None, alias="CodigoProducto")
    codigo_categoria: str | None = Field(default=None, alias="CodigoCategoria")
    categoria: str | None = Field(default=None, alias="Categoria")
    nombre_producto: str | None = Field(default=None, alias="NombreProducto")
    descripcion: str | None = Field(default=None, alias="Descripcion")
    unidad_medida: str | None = Field(default=None, alias="UnidadMedida")
    cantidad: str | None = Field(default=None, alias="Cantidad")


class ItemsPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    cantidad: int | None = Field(default=None, alias="Cantidad")
    listado: list[ItemPayload] = Field(
        default_factory=lambda: cast(list[ItemPayload], []),
        alias="Listado",
    )


class AdjudicacionPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    tipo: str | None = Field(default=None, alias="Tipo")
    fecha: date | None = Field(default=None, alias="Fecha")
    numero: str | None = Field(default=None, alias="Numero")
    numero_oferentes: int | None = Field(default=None, alias="NumeroOferentes")
    url_acta: str | None = Field(default=None, alias="UrlActa")

    @field_validator("fecha", mode="before")
    @classmethod
    def _validate_fecha(cls, value: Any) -> Any:
        return _parse_optional_date(value)


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

    description: str | None = Field(default=None, alias="Descripcion")
    comprador: CompradorPayload | None = Field(default=None, alias="Comprador")
    fechas: FechasPayload | None = Field(default=None, alias="Fechas")
    items: ItemsPayload | None = Field(default=None, alias="Items")
    adjudicacion: AdjudicacionPayload | None = Field(default=None, alias="Adjudicacion")
    tipo: str | None = Field(default=None, alias="Tipo")
    codigo_tipo: str | None = Field(default=None, alias="CodigoTipo")
    tipo_convocatoria: str | None = Field(default=None, alias="TipoConvocatoria")
    dias_cierre_licitacion: int | None = Field(default=None, alias="DiasCierreLicitacion")
    claim_count: int | None = Field(default=None, alias="CantidadReclamos")
    funding_source: str | None = Field(default=None, alias="FundingSource")
    visibility_amount: str | None = Field(default=None, alias="VisibilityAmount")

    @field_validator("publication_date", "close_date", mode="before")
    @classmethod
    def _validate_dates(cls, value: Any) -> Any:
        return _parse_optional_date(value)

    @model_validator(mode="after")
    def _apply_nested_fallbacks(self) -> LicitacionNotice:
        if self.fechas is not None:
            if self.fechas.fecha_publicacion is not None:
                object.__setattr__(self, "publication_date", self.fechas.fecha_publicacion)
            if self.fechas.fecha_cierre is not None:
                object.__setattr__(self, "close_date", self.fechas.fecha_cierre)
        if self.comprador is not None:
            comp = self.comprador
            if comp.codigo_organismo is not None:
                object.__setattr__(self, "buyer_org_code", comp.codigo_organismo)
            if comp.nombre_organismo is not None:
                object.__setattr__(self, "buyer_org_name", comp.nombre_organismo)
            if comp.codigo_unidad is not None:
                object.__setattr__(self, "buyer_unit_code", comp.codigo_unidad)
            if comp.nombre_unidad is not None:
                object.__setattr__(self, "buyer_unit_name", comp.nombre_unidad)
        return self


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
    return LicitacionesResponse(**payload)

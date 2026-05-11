from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import json
from time import sleep
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .config import MercadoPublicoSettings, validate_settings
from .errors import (
    MercadoPublicoConfigError,
    MercadoPublicoContractDriftError,
    MercadoPublicoRequestError,
)
from .rate_limit import DailyRequestBudget, retry_backoff_seconds
from .schemas import LicitacionesResponse, parse_licitaciones_response

REDACTED_SECRET = "***redacted***"
LICITACIONES_ENDPOINT = "/licitaciones.json"


def format_query_date(value: date) -> str:
    return value.strftime("%d%m%Y")


def redact_query_params(params: dict[str, str]) -> dict[str, str]:
    safe: dict[str, str] = {}
    for key, value in params.items():
        if key.lower() == "ticket":
            safe[key] = REDACTED_SECRET
            continue
        safe[key] = value
    return safe


@dataclass(frozen=True)
class MercadoPublicoClient:
    settings: MercadoPublicoSettings
    _daily_request_budget: DailyRequestBudget = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        try:
            validate_settings(self.settings)
        except ValueError as exc:
            raise MercadoPublicoConfigError(str(exc)) from exc
        object.__setattr__(
            self,
            "_daily_request_budget",
            DailyRequestBudget(limit=self.settings.daily_request_limit),
        )

    def build_active_discovery_params(self) -> dict[str, str]:
        return {"estado": "activas", "ticket": self.settings.api_key}

    def build_rolling_window_params(self, *, day: date, estado: str | None = None) -> dict[str, str]:
        params: dict[str, str] = {"fecha": format_query_date(day), "ticket": self.settings.api_key}
        if estado:
            params["estado"] = estado
        return params

    def build_detail_by_codigo_params(self, *, codigo: str) -> dict[str, str]:
        normalized = codigo.strip()
        if not normalized:
            raise ValueError("codigo must not be blank")
        return {"codigo": normalized, "ticket": self.settings.api_key}

    def build_url(self, *, endpoint: str, params: dict[str, str]) -> str:
        base = self.settings.normalized_base_url
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        query = urlencode(sorted(params.items()))
        return f"{base}{path}?{query}"

    def build_safe_url(self, *, endpoint: str, params: dict[str, str]) -> str:
        return self.build_url(endpoint=endpoint, params=redact_query_params(params))

    def _fetch_json(self, *, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        self._daily_request_budget.consume(1)
        url = self.build_url(endpoint=endpoint, params=params)

        max_attempts = self.settings.retry_budget + 1
        for attempt in range(1, max_attempts + 1):
            try:
                request = Request(url=url, method="GET")
                with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                    body = response.read().decode("utf-8")
                decoded: Any = json.loads(body)
                if not isinstance(decoded, dict):
                    raise MercadoPublicoContractDriftError("expected JSON object response")
                return cast(dict[str, Any], decoded)
            except HTTPError as exc:
                if attempt >= max_attempts or exc.code < 500 and exc.code != 429:
                    raise MercadoPublicoRequestError(
                        f"Mercado Publico request failed with status={exc.code}"
                    ) from exc
            except URLError as exc:
                if attempt >= max_attempts:
                    raise MercadoPublicoRequestError("Mercado Publico request failed") from exc
            except json.JSONDecodeError as exc:
                raise MercadoPublicoContractDriftError("invalid JSON response from Mercado Publico") from exc

            sleep(retry_backoff_seconds(attempt=attempt))

        raise MercadoPublicoRequestError("Mercado Publico request failed")

    def fetch_active_discovery(self) -> LicitacionesResponse:
        _payload, response = self.fetch_active_discovery_with_raw()
        return response

    def fetch_active_discovery_with_raw(self) -> tuple[dict[str, Any], LicitacionesResponse]:
        payload = self._fetch_json(
            endpoint=LICITACIONES_ENDPOINT,
            params=self.build_active_discovery_params(),
        )
        return payload, parse_licitaciones_response(payload)

    def fetch_rolling_window(self, *, day: date, estado: str | None = None) -> LicitacionesResponse:
        _payload, response = self.fetch_rolling_window_with_raw(day=day, estado=estado)
        return response

    def fetch_rolling_window_with_raw(
        self,
        *,
        day: date,
        estado: str | None = None,
    ) -> tuple[dict[str, Any], LicitacionesResponse]:
        payload = self._fetch_json(
            endpoint=LICITACIONES_ENDPOINT,
            params=self.build_rolling_window_params(day=day, estado=estado),
        )
        return payload, parse_licitaciones_response(payload)

    def fetch_detail_by_codigo(self, *, codigo: str) -> LicitacionesResponse:
        _payload, response = self.fetch_detail_by_codigo_with_raw(codigo=codigo)
        return response

    def fetch_detail_by_codigo_with_raw(self, *, codigo: str) -> tuple[dict[str, Any], LicitacionesResponse]:
        payload = self._fetch_json(
            endpoint=LICITACIONES_ENDPOINT,
            params=self.build_detail_by_codigo_params(codigo=codigo),
        )
        return payload, parse_licitaciones_response(payload)

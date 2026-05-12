from __future__ import annotations

from datetime import date
from urllib.error import HTTPError

import pytest

from backend.pipeline.extract.mp_api_client import MercadoPublicoClient, redact_query_params
from backend.pipeline.extract.mp_api_config import MercadoPublicoSettings, validate_settings
from backend.pipeline.extract.mp_api_errors import (
    MercadoPublicoConfigError,
    MercadoPublicoContractDriftError,
    MercadoPublicoRateLimitError,
    MercadoPublicoRequestError,
)


def test_validate_settings_rejects_enabled_without_api_key() -> None:
    settings = MercadoPublicoSettings(enabled=True, api_key="", base_url="https://api.mercadopublico.cl/servicios/v1/publico")

    with pytest.raises(ValueError, match="requires MERCADO_PUBLICO_API_KEY"):
        validate_settings(settings)


def test_build_active_discovery_url_uses_canonical_params() -> None:
    client = MercadoPublicoClient(
        settings=MercadoPublicoSettings(
            enabled=True,
            api_key="ticket-value",
            base_url="https://api.mercadopublico.cl/servicios/v1/publico/",
        )
    )

    url = client.build_url(endpoint="/licitaciones.json", params=client.build_active_discovery_params())
    assert (
        url
        == "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json?estado=activas&ticket=ticket-value"
    )


def test_build_detail_by_codigo_request_includes_ticket() -> None:
    client = MercadoPublicoClient(
        settings=MercadoPublicoSettings(
            enabled=True,
            api_key="ticket-value",
            base_url="https://api.mercadopublico.cl/servicios/v1/publico",
        )
    )

    params = client.build_detail_by_codigo_params(codigo="1274285-76-LR25")
    url = client.build_url(endpoint="licitaciones.json", params=params)
    assert url == (
        "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json?"
        "codigo=1274285-76-LR25&ticket=ticket-value"
    )


def test_build_rolling_window_formats_date_ddmmyyyy() -> None:
    client = MercadoPublicoClient(
        settings=MercadoPublicoSettings(
            enabled=True,
            api_key="ticket-value",
            base_url="https://api.mercadopublico.cl/servicios/v1/publico",
        )
    )

    params = client.build_rolling_window_params(day=date(2026, 5, 8), estado="publicada")
    assert params["fecha"] == "08052026"
    assert params["estado"] == "publicada"


def test_redaction_never_echoes_ticket_value() -> None:
    safe = redact_query_params({"estado": "activas", "ticket": "13F12BA1-CBC1-4A8B-BA97-2B0D7E69CBD8"})

    assert safe["ticket"] == "***redacted***"
    assert "13F12BA1-CBC1-4A8B-BA97-2B0D7E69CBD8" not in repr(safe)


def test_fetch_active_discovery_retries_then_exhausts_on_5xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}
    client = MercadoPublicoClient(
        settings=MercadoPublicoSettings(
            enabled=True,
            api_key="ticket-value",
            base_url="https://api.mercadopublico.cl/servicios/v1/publico",
            retry_budget=2,
        )
    )

    def fake_urlopen(*args, **kwargs):
        _ = args, kwargs
        attempts["count"] += 1
        raise HTTPError(url="https://example", code=500, msg="boom", hdrs=None, fp=None)

    monkeypatch.setattr("backend.pipeline.extract.mp_api_client.urlopen", fake_urlopen)
    monkeypatch.setattr("backend.pipeline.extract.mp_api_client.sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(MercadoPublicoRequestError, match="status=500"):
        client.fetch_active_discovery()
    assert attempts["count"] == 3


def test_fetch_active_discovery_fails_on_contract_drift_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MercadoPublicoClient(
        settings=MercadoPublicoSettings(
            enabled=True,
            api_key="ticket-value",
            base_url="https://api.mercadopublico.cl/servicios/v1/publico",
        )
    )

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return None

        def read(self):
            return b"not-json"

    monkeypatch.setattr(
        "backend.pipeline.extract.mp_api_client.urlopen",
        lambda *_args, **_kwargs: _FakeResponse(),
    )

    with pytest.raises(MercadoPublicoContractDriftError, match="invalid JSON"):
        client.fetch_active_discovery()


def test_fetch_budget_persists_across_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MercadoPublicoClient(
        settings=MercadoPublicoSettings(
            enabled=True,
            api_key="ticket-value",
            base_url="https://api.mercadopublico.cl/servicios/v1/publico",
            daily_request_limit=2,
            retry_budget=0,
        )
    )

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            _ = exc_type, exc, tb
            return None

        def read(self):
            return b'{"Codigo":0,"Descripcion":"OK","Cantidad":0,"Listado":[]}'

    monkeypatch.setattr(
        "backend.pipeline.extract.mp_api_client.urlopen",
        lambda *_args, **_kwargs: _FakeResponse(),
    )

    client.fetch_active_discovery()
    client.fetch_active_discovery()

    with pytest.raises(MercadoPublicoRateLimitError, match="daily request budget exhausted"):
        client.fetch_active_discovery()

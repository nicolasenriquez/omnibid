from __future__ import annotations


class MercadoPublicoIntegrationError(RuntimeError):
    """Base error for Mercado Publico integration failures."""


class MercadoPublicoConfigError(MercadoPublicoIntegrationError):
    """Raised when integration settings are invalid."""


class MercadoPublicoRequestError(MercadoPublicoIntegrationError):
    """Raised for HTTP/network request failures."""


class MercadoPublicoRateLimitError(MercadoPublicoIntegrationError):
    """Raised when local request budget is exhausted."""


class MercadoPublicoContractDriftError(MercadoPublicoIntegrationError):
    """Raised when upstream response shape is invalid."""


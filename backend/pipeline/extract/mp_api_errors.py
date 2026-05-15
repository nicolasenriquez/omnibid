from __future__ import annotations


class MercadoPublicoIntegrationError(RuntimeError):
    """Base error for Mercado Publico integration failures."""


class MercadoPublicoConfigError(MercadoPublicoIntegrationError):
    """Raised when integration settings are invalid."""


class MercadoPublicoContractDriftError(MercadoPublicoIntegrationError):
    """Raised when API response contract changes unexpectedly."""


class MercadoPublicoRequestError(MercadoPublicoIntegrationError):
    """Raised when an API request fails after retries."""


class MercadoPublicoRateLimitError(MercadoPublicoIntegrationError):
    """Raised when daily request budget is exhausted."""

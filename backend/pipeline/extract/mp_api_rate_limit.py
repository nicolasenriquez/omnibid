from __future__ import annotations

from dataclasses import dataclass

from backend.pipeline.extract.mp_api_errors import MercadoPublicoRateLimitError


@dataclass
class DailyRequestBudget:
    limit: int
    used: int = 0

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("limit must be >= 1")
        if self.used < 0:
            raise ValueError("used must be >= 0")

    def can_consume(self, units: int = 1) -> bool:
        if units < 1:
            raise ValueError("units must be >= 1")
        return self.used + units <= self.limit

    def consume(self, units: int = 1) -> None:
        if not self.can_consume(units):
            raise MercadoPublicoRateLimitError(
                f"daily request budget exhausted: used={self.used}, requested={units}, limit={self.limit}"
            )
        self.used += units


def retry_backoff_seconds(*, attempt: int, base_seconds: int = 2, cap_seconds: int = 120) -> int:
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    if base_seconds < 1:
        raise ValueError("base_seconds must be >= 1")
    if cap_seconds < 1:
        raise ValueError("cap_seconds must be >= 1")
    backoff = base_seconds * (2 ** (attempt - 1))
    return backoff if backoff < cap_seconds else cap_seconds

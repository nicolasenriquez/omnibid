from __future__ import annotations

from datetime import date
from decimal import Decimal

from backend.api.opportunities_query import (
    COUNT_AND_SUMMARY_FILTER_SQL,
    LIST_FILTER_SQL,
    build_opportunities_filter_params,
)


def test_build_opportunities_filter_params_wraps_contains_filters() -> None:
    payload = build_opportunities_filter_params(
        q="licitacion",
        official_status="Publicada",
        buyer_region="RM",
        primary_category="Servicios",
        publication_from=date(2026, 1, 1),
        publication_to=date(2026, 12, 31),
        close_from=date(2026, 4, 1),
        close_to=date(2026, 4, 30),
        min_amount=Decimal("10"),
        max_amount=Decimal("100"),
        procurement_type="public",
        less_than_100_utm=True,
        stage="open",
        source_view=None,
    )

    assert payload["q"] == "%licitacion%"
    assert payload["official_status"] == "%Publicada%"
    assert payload["buyer_region"] == "%RM%"
    assert payload["primary_category"] == "%Servicios%"
    assert payload["min_amount"] == Decimal("10")
    assert payload["max_amount"] == Decimal("100")
    assert payload["procurement_type"] == "public"
    assert payload["less_than_100_utm"] is True
    assert payload["stage"] == "open"


def test_filter_sql_variants_keep_stage_and_procurement_logic() -> None:
    assert "when :procurement_type = 'public'" in LIST_FILTER_SQL
    assert "when :procurement_type = 'public'" in COUNT_AND_SUMMARY_FILTER_SQL
    assert "when :stage = 'closing_soon'" in LIST_FILTER_SQL
    assert "when :stage = 'closing_soon'" in COUNT_AND_SUMMARY_FILTER_SQL
    assert "when :source_view = 'publicadas'" in LIST_FILTER_SQL
    assert "when :source_view = 'publicadas'" in COUNT_AND_SUMMARY_FILTER_SQL
    assert "api_detail" not in LIST_FILTER_SQL
    assert "api_detail" not in COUNT_AND_SUMMARY_FILTER_SQL


def test_build_opportunities_filter_params_supports_publicadas_source_view() -> None:
    payload = build_opportunities_filter_params(
        q=None,
        official_status=None,
        buyer_region=None,
        primary_category=None,
        publication_from=None,
        publication_to=None,
        close_from=None,
        close_to=None,
        min_amount=None,
        max_amount=None,
        procurement_type=None,
        less_than_100_utm=None,
        stage=None,
        source_view="publicadas",
    )
    assert payload["source_view"] == "publicadas"

from __future__ import annotations

from datetime import date, timedelta
import os
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import backend.models  # noqa: F401
from backend.db.base import Base
from backend.integrations.mercado_publico.schemas import (
    LicitacionesResponse,
    parse_licitaciones_response,
)
from backend.integrations.mercado_publico.sync import DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE
from backend.models.api_source import ApiSourcePayload, ApiSourceRequest, MercadoPublicoNoticeSnapshot
from backend.models.normalized import (
    NormalizedLicitacion,
    NormalizedLicitacionItem,
    NormalizedOferta,
    NormalizedSupplier,
    SilverAwardOutcome,
    SilverBidSubmission,
    SilverBuyingOrg,
    SilverCategoryRef,
    SilverContractingUnit,
    SilverNotice,
    SilverNoticeLine,
    SilverNoticePurchaseOrderLink,
    SilverPurchaseOrder,
    SilverPurchaseOrderLine,
    SilverSupplier,
    SilverSupplierParticipation,
)
from backend.models.operational import PipelineRun, PipelineRunStep, SourceFile
from backend.pipeline import application


def _prepare_schema(engine: sa.Engine) -> None:
    tables = [
        PipelineRun.__table__,
        PipelineRunStep.__table__,
        SourceFile.__table__,
        ApiSourcePayload.__table__,
        ApiSourceRequest.__table__,
        MercadoPublicoNoticeSnapshot.__table__,
        NormalizedLicitacion.__table__,
        NormalizedLicitacionItem.__table__,
        NormalizedOferta.__table__,
        NormalizedSupplier.__table__,
        SilverBuyingOrg.__table__,
        SilverContractingUnit.__table__,
        SilverSupplier.__table__,
        SilverCategoryRef.__table__,
        SilverNotice.__table__,
        SilverNoticeLine.__table__,
        SilverBidSubmission.__table__,
        SilverAwardOutcome.__table__,
        SilverSupplierParticipation.__table__,
        SilverPurchaseOrder.__table__,
        SilverPurchaseOrderLine.__table__,
        SilverNoticePurchaseOrderLink.__table__,
    ]
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # Keep integration schema deterministic even when prior runs left stale table shapes.
    # Drop all model-managed tables first so FK-dependent tables don't block cleanup.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine, tables=tables)


def _response_for_codes(*, publication_day: date, codes: list[str]) -> LicitacionesResponse:
    payload = {
        "Codigo": 0,
        "Descripcion": "OK",
        "Cantidad": len(codes),
        "FechaCreacion": publication_day.strftime("%d%m%Y"),
        "Listado": [
            {
                "CodigoExterno": code,
                "Nombre": f"Licitacion {code}",
                "Codigo": code.split("-")[0],
                "CodigoEstado": 5,
                "Estado": "Publicada",
                "FechaPublicacion": publication_day.strftime("%d%m%Y"),
                "FechaCierre": (publication_day + timedelta(days=2)).strftime("%d%m%Y"),
                "Tipo de Adquisicion": "Licitacion Publica",
                "Moneda Adquisicion": "Peso Chileno",
                "CodigoMoneda": "CLP",
                "NumeroOferentes": 2,
                "CodigoOrganismo": "7010",
                "NombreOrganismo": "Municipalidad",
                "CodigoUnidad": "U-10",
                "NombreUnidad": "Unidad Compras",
                "ComunaUnidad": "Santiago",
                "RegionUnidad": "Metropolitana",
                "Moneda": "CLP",
                "MontoEstimado": "12345.67",
            }
            for code in codes
        ],
    }
    return parse_licitaciones_response(payload)


class _FakeRollingClient:
    def __init__(
        self,
        responses_by_day: dict[date, LicitacionesResponse],
        *,
        detail_responses_by_codigo: dict[str, LicitacionesResponse] | None = None,
        fail_on_fetch: bool = False,
    ) -> None:
        self._responses_by_day = responses_by_day
        self._detail_responses_by_codigo = detail_responses_by_codigo or {}
        self._fail_on_fetch = fail_on_fetch

    def fetch_rolling_window(self, *, day: date, estado: str | None = None) -> LicitacionesResponse:
        _ = estado
        if self._fail_on_fetch:
            raise AssertionError("fetch_rolling_window should not be called in refresh-only mode")
        return self._responses_by_day[day]

    def build_rolling_window_params(self, *, day: date, estado: str | None = None) -> dict[str, str]:
        params = {"fecha": day.strftime("%d%m%Y"), "ticket": "secret"}
        if estado is not None:
            params["estado"] = estado
        return params

    def fetch_rolling_window_with_raw(self, *, day: date, estado: str | None = None):
        _ = estado
        if self._fail_on_fetch:
            raise AssertionError("fetch_rolling_window should not be called in refresh-only mode")
        response = self._responses_by_day[day]
        raw = {
            "Codigo": response.code or 0,
            "Descripcion": response.description or "OK",
            "Cantidad": response.count,
            "FechaCreacion": day.strftime("%d%m%Y"),
            "Listado": [notice.model_dump(by_alias=True, exclude_none=True) for notice in response.notices],
        }
        return raw, response

    def fetch_detail_by_codigo_with_raw(self, *, codigo: str):
        if self._fail_on_fetch:
            raise AssertionError("fetch_detail_by_codigo should not be called in refresh-only mode")
        response = self._detail_responses_by_codigo.get(codigo)
        if response is None:
            response = _response_for_codes(publication_day=date(2026, 5, 8), codes=[codigo])
        raw = {
            "Codigo": response.code or 0,
            "Descripcion": response.description or "OK",
            "Cantidad": response.count,
            "FechaCreacion": date(2026, 5, 8).strftime("%d%m%Y"),
            "Listado": [notice.model_dump(by_alias=True, exclude_none=True) for notice in response.notices],
        }
        return raw, response

    def build_detail_by_codigo_params(self, *, codigo: str) -> dict[str, str]:
        return {"codigo": codigo, "ticket": "secret"}

    def build_safe_url(self, *, endpoint: str, params: dict[str, str]) -> str:
        if "codigo" in params:
            return f"https://example.invalid/{endpoint}?codigo={params['codigo']}"
        if "fecha" in params:
            return f"https://example.invalid/{endpoint}?fecha={params['fecha']}"
        return f"https://example.invalid/{endpoint}"


@pytest.mark.integration
def test_daily_pipeline_happy_path_and_rerun_is_idempotent() -> None:
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    assert test_database_url, "TEST_DATABASE_URL must be set for integration tests"

    engine = create_engine(test_database_url, pool_pre_ping=True, future=True)
    _prepare_schema(engine)

    target_day = date(2026, 5, 8)
    day_minus_one = target_day - timedelta(days=1)
    suffix = uuid4().hex[:8]
    code_a = f"{suffix}-A-LR26"
    code_b = f"{suffix}-B-LR26"
    code_c = f"{suffix}-C-LR26"
    responses_by_day = {
        target_day: _response_for_codes(publication_day=target_day, codes=[code_a, code_b]),
        day_minus_one: _response_for_codes(publication_day=day_minus_one, codes=[code_b, code_c]),
    }
    client = _FakeRollingClient(responses_by_day)

    with Session(engine, future=True) as first_session:
        first = application.run_mp_api_daily_notice_pipeline(
            first_session,
            client=client,  # type: ignore[arg-type]
            target_date=target_day,
            window_days=2,
        )
        first_session.commit()

        first_notice_count = first_session.execute(
            sa.select(sa.func.count())
            .select_from(SilverNotice)
            .where(SilverNotice.notice_id.in_([code_a, code_b, code_c]))
        ).scalar_one()

    with Session(engine, future=True) as second_session:
        second = application.run_mp_api_daily_notice_pipeline(
            second_session,
            client=client,  # type: ignore[arg-type]
            target_date=target_day,
            window_days=2,
        )
        second_session.commit()

        second_notice_count = second_session.execute(
            sa.select(sa.func.count())
            .select_from(SilverNotice)
            .where(SilverNotice.notice_id.in_([code_a, code_b, code_c]))
        ).scalar_one()

    assert first.sync_summary.requests == 2
    assert first.sync_summary.notices_seen == 4
    assert first.sync_summary.notices_skipped_missing_external_notice_code == 0
    assert first.sync_summary.snapshots_upserted == 4
    assert first.sync_summary.snapshots_inserted == 4
    assert first.sync_summary.snapshots_updated == 0
    assert first.detail_summary.requests == 3
    assert first.detail_summary.snapshots_upserted == 3
    assert first.silver_summary.notice_candidates == 3
    assert first.silver_summary.upserted_notices == 3
    assert int(first_notice_count or 0) == 3
    assert int(second_notice_count or 0) == 3
    assert first.source_file_id is not None
    assert second.source_file_id is not None
    assert second.sync_summary.requests == 2
    assert second.sync_summary.notices_seen == 4
    assert second.sync_summary.notices_skipped_missing_external_notice_code == 0
    assert second.sync_summary.snapshots_upserted == 4
    assert second.sync_summary.snapshots_inserted == 0
    assert second.sync_summary.snapshots_updated == 4
    assert second.detail_summary.requests == 0
    assert second.detail_summary.snapshots_upserted == 0


@pytest.mark.integration
def test_daily_pipeline_failure_after_sync_preserves_lineage_and_refresh_only_replay() -> None:
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    assert test_database_url, "TEST_DATABASE_URL must be set for integration tests"

    engine = create_engine(test_database_url, pool_pre_ping=True, future=True)
    _prepare_schema(engine)

    target_day = date(2026, 5, 9)
    suffix = uuid4().hex[:8]
    code = f"{suffix}-FAIL-LR26"
    client = _FakeRollingClient(
        {
            target_day: _response_for_codes(publication_day=target_day, codes=[code]),
        }
    )

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        application,
        "canonicalize_mp_api_payloads_to_read_model",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("forced canonicalization failure")),
    )

    with Session(engine, future=True) as failing_session:
        existing_run_ids = {
            UUID(str(run_id))
            for run_id in failing_session.execute(
                sa.select(PipelineRun.id).where(
                    PipelineRun.dataset_type == DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE
                )
            ).scalars()
        }
        with pytest.raises(RuntimeError, match="forced canonicalization failure"):
            application.run_mp_api_daily_notice_pipeline(
                failing_session,
                client=client,  # type: ignore[arg-type]
                target_date=target_day,
                window_days=1,
            )
        failing_session.commit()

        current_runs = failing_session.execute(
            sa.select(PipelineRun).where(
                PipelineRun.dataset_type == DATASET_TYPE_MERCADO_PUBLICO_API_NOTICE
            )
        ).scalars().all()
        created_runs = [run for run in current_runs if UUID(str(run.id)) not in existing_run_ids]
        assert len(created_runs) == 1
        failed_run = created_runs[0]
        assert failed_run.status == "failed"
        assert failed_run.source_file_id is not None

        steps = failing_session.execute(
            sa.select(PipelineRunStep)
            .where(PipelineRunStep.run_id == failed_run.id)
            .order_by(PipelineRunStep.started_at.asc(), PipelineRunStep.id.asc())
        ).scalars().all()
        assert [step.step_name for step in steps] == [
            "mp_api_rolling_refresh",
            "mp_api_detail_enrichment",
            "mp_api_payload_canonicalization",
            "mp_api_silver_postprocess",
        ]
        assert steps[0].status == "completed"
        assert steps[1].status == "completed"
        assert steps[2].status == "failed"
        assert steps[3].status == "failed"

        snapshot_count = failing_session.execute(
            sa.select(sa.func.count())
            .select_from(MercadoPublicoNoticeSnapshot)
            .where(MercadoPublicoNoticeSnapshot.pipeline_run_id == failed_run.id)
        ).scalar_one()
        assert int(snapshot_count or 0) >= 1

    monkeypatch.undo()

    replay_client = _FakeRollingClient({}, fail_on_fetch=True)
    with Session(engine, future=True) as replay_session:
        before_snapshot_count = replay_session.execute(
            sa.select(sa.func.count())
            .select_from(MercadoPublicoNoticeSnapshot)
            .where(MercadoPublicoNoticeSnapshot.external_notice_code == code)
        ).scalar_one()

        replay = application.run_mp_api_daily_notice_pipeline(
            replay_session,
            client=replay_client,  # type: ignore[arg-type]
            target_date=target_day,
            window_days=1,
            refresh_only=True,
        )
        replay_session.commit()

        after_snapshot_count = replay_session.execute(
            sa.select(sa.func.count())
            .select_from(MercadoPublicoNoticeSnapshot)
            .where(MercadoPublicoNoticeSnapshot.external_notice_code == code)
        ).scalar_one()
        silver_count = replay_session.execute(
            sa.select(sa.func.count())
            .select_from(SilverNotice)
            .where(SilverNotice.notice_id == code)
        ).scalar_one()

    assert replay.sync_summary.requests == 0
    assert replay.detail_summary.requests == 0
    assert replay.silver_summary.notice_candidates >= 1
    assert replay.silver_summary.upserted_notices >= 1
    assert int(before_snapshot_count or 0) == int(after_snapshot_count or 0)
    assert int(silver_count or 0) == 1


@pytest.mark.integration
def test_daily_pipeline_tracks_skipped_notices_without_external_code() -> None:
    test_database_url = os.environ.get("TEST_DATABASE_URL")
    assert test_database_url, "TEST_DATABASE_URL must be set for integration tests"

    engine = create_engine(test_database_url, pool_pre_ping=True, future=True)
    _prepare_schema(engine)

    target_day = date(2026, 5, 10)
    suffix = uuid4().hex[:8]
    valid_code = f"{suffix}-VALID-LR26"
    client = _FakeRollingClient(
        {
            target_day: _response_for_codes(publication_day=target_day, codes=[valid_code, ""]),
        }
    )

    with Session(engine, future=True) as session:
        summary = application.run_mp_api_daily_notice_pipeline(
            session,
            client=client,  # type: ignore[arg-type]
            target_date=target_day,
            window_days=1,
        )
        session.commit()

        snapshot_count = session.execute(
            sa.select(sa.func.count())
            .select_from(MercadoPublicoNoticeSnapshot)
            .where(MercadoPublicoNoticeSnapshot.pipeline_run_id == summary.run_id)
        ).scalar_one()
        silver_count = session.execute(
            sa.select(sa.func.count())
            .select_from(SilverNotice)
            .where(SilverNotice.notice_id == valid_code)
        ).scalar_one()

    assert summary.sync_summary.requests == 1
    assert summary.sync_summary.notices_seen == 2
    assert summary.sync_summary.notices_skipped_missing_external_notice_code == 1
    assert summary.sync_summary.snapshots_upserted == 1
    assert summary.sync_summary.snapshots_inserted == 1
    assert summary.sync_summary.snapshots_updated == 0
    assert summary.detail_summary.requests == 1
    assert summary.detail_summary.snapshots_upserted == 1
    assert summary.silver_summary.notice_candidates == 1
    assert summary.silver_summary.upserted_notices == 1
    assert int(snapshot_count or 0) == summary.sync_summary.snapshots_upserted + summary.detail_summary.snapshots_upserted
    assert int(silver_count or 0) == 1

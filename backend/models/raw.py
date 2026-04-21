import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.db.base import Base


class RawLicitacion(Base):
    __tablename__ = "raw_licitaciones"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    batch_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("ingestion_batches.id"), nullable=False)
    raw_row_num = sa.Column(sa.BigInteger, nullable=False)
    codigo = sa.Column(sa.Text)
    codigo_externo = sa.Column(sa.Text)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)
    raw_json = sa.Column(JSONB, nullable=False)
    ingested_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.UniqueConstraint("source_file_id", "raw_row_num", name="uq_raw_lic_raw_file_row"),
    )


class RawOrdenCompra(Base):
    __tablename__ = "raw_ordenes_compra"

    id = sa.Column(sa.BigInteger, primary_key=True, autoincrement=True)
    source_file_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("source_files.id"), nullable=False)
    batch_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("ingestion_batches.id"), nullable=False)
    raw_row_num = sa.Column(sa.BigInteger, nullable=False)
    codigo_oc = sa.Column(sa.Text)
    codigo_licitacion = sa.Column(sa.Text)
    id_item = sa.Column(sa.Text)
    row_hash_sha256 = sa.Column(sa.String(64), nullable=False)
    raw_json = sa.Column(JSONB, nullable=False)
    ingested_at = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))

    __table_args__ = (
        sa.UniqueConstraint("source_file_id", "raw_row_num", name="uq_raw_oc_raw_file_row"),
    )

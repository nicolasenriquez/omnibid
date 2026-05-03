"""allow duplicate source file hashes for manual append lineage

Revision ID: 202605021830_source_hash_idx
Revises: 202604230040_silver_text_ann
Create Date: 2026-05-02 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "202605021830_source_hash_idx"
down_revision: Union[str, None] = "202604230040_silver_text_ann"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE source_files
        DROP CONSTRAINT IF EXISTS source_files_file_hash_sha256_key
        """
    )
    op.create_index(
        "ix_source_files_file_hash_sha256",
        "source_files",
        ["file_hash_sha256"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_source_files_file_hash_sha256", table_name="source_files")
    op.execute(
        """
        ALTER TABLE source_files
        ADD CONSTRAINT source_files_file_hash_sha256_key UNIQUE (file_hash_sha256)
        """
    )

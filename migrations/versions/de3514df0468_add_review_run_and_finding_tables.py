"""
add review run and finding tables

Revision ID: de3514df0468
Revises: 475e0a8c012d
Create Date: 2026-10-27 21:46:35.415695
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'de3514df0468'
down_revision = '475e0a8c012d'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create review_runs table
    op.create_table(
        "review_runs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("webhook_delivery_id", sa.Integer, sa.ForeignKey('webhook_deliveries.id'), nullable=False),
        sa.Column("created_at", sa.DateTime, default=sa.func.utcnow(), nullable=False),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String, default='pending', nullable=False),
    )
    # Create findings table
    op.create_table(
        "findings",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("review_run_id", sa.Integer, sa.ForeignKey('review_runs.id'), nullable=False),
        sa.Column("file_path", sa.String, nullable=False),
        sa.Column("line_number", sa.Integer, nullable=True),
        sa.Column("severity", sa.String, nullable=False),
        sa.Column("confidence", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=False),
        sa.Column("suggestion", sa.String, nullable=True),
        sa.Column("metadata_json", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    # Drop findings table first due to FK dependency
    op.drop_table("findings")
    # Then drop review_runs table
    op.drop_table("review_runs")


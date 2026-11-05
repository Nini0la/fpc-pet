"""Optional field-level intention evidence alongside existing authoritative plan fields."""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = depends_on = None


def upgrade():
    op.add_column("users", sa.Column("conversation_recall_after", sa.DateTime(timezone=True)))
    # Conservatively retain existing forget/correction boundaries on upgrade.
    op.execute("UPDATE users SET conversation_recall_after=context_reset_at")
    for table in ("threads", "commitments", "reminder_plans"):
        op.add_column(
            table, sa.Column("intention_context", sa.JSON(), nullable=False, server_default="{}")
        )


def downgrade():
    # Loss-aware: export intention metadata before downgrade. Existing plan fields remain.
    for table in ("reminder_plans", "commitments", "threads"):
        op.drop_column(table, "intention_context")
    op.drop_column("users", "conversation_recall_after")

"""Separate proven non-deletion legacy resets from the historical forgetting boundary."""

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = depends_on = None


def upgrade():
    # 0015 conservatively copied the old reset. Release it only when every durable
    # deletion indicator is absent; unknown/deleted histories retain the stricter cutoff.
    op.execute("""
        UPDATE users SET conversation_recall_after = NULL
        WHERE conversation_recall_after = context_reset_at
          AND (EXISTS (SELECT 1 FROM commitments c WHERE c.user_id = users.id
                       AND NOT c.deleted AND c.version > 1 AND c.last_touched_at = users.context_reset_at)
               OR EXISTS (SELECT 1 FROM journal_entries j WHERE j.user_id = users.id
                          AND NOT j.deleted AND j.version > 1 AND j.updated_at = users.context_reset_at))
          AND NOT EXISTS (SELECT 1 FROM provenance_links p
                          WHERE p.user_id = users.id AND p.source_type = 'deletion_tombstone')
          AND NOT EXISTS (SELECT 1 FROM assistance_runs r WHERE r.user_id = users.id
                          AND r.trace_status = 'cleared_by_memory_deletion')
          AND NOT EXISTS (SELECT 1 FROM threads t WHERE t.user_id = users.id AND t.deleted)
          AND NOT EXISTS (SELECT 1 FROM commitments c WHERE c.user_id = users.id AND c.deleted)
          AND NOT EXISTS (SELECT 1 FROM journal_entries j WHERE j.user_id = users.id AND j.deleted)
          AND NOT EXISTS (SELECT 1 FROM episodes e WHERE e.user_id = users.id AND e.deleted)
          AND NOT EXISTS (SELECT 1 FROM vocabulary_items v WHERE v.user_id = users.id AND v.deleted)
    """)


def downgrade():
    # Restore the previous conservative policy, never expose additional forgotten history.
    op.execute("""
        UPDATE users SET conversation_recall_after = context_reset_at
        WHERE conversation_recall_after IS NULL AND context_reset_at IS NOT NULL
    """)

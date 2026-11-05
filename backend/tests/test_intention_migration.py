from datetime import datetime, timezone

from sqlalchemy import MetaData, create_engine, inspect, select, text
from test_migrations import run_alembic


def test_0015_preserves_existing_data_and_downgrade_is_loss_aware(tmp_path):
    exercise_migration(f"sqlite:///{tmp_path}/intentions.db")


def exercise_migration(url):
    result = run_alembic(url, "upgrade", "0014")
    assert result.returncode == 0, result.stderr
    engine = create_engine(url)
    old = MetaData()
    old.reflect(engine)
    now = datetime(2026, 10, 30, 9, tzinfo=timezone.utc)
    with engine.begin() as db:
        db.execute(
            old.tables["users"]
            .insert()
            .values(id="owner", username="owner", created_at=now, context_reset_at=now)
        )
        db.execute(
            old.tables["commitments"]
            .insert()
            .values(
                id="task",
                user_id="owner",
                title="Essay",
                purpose="Original purpose",
                state="open",
                confidence=1,
                derivation="fixture",
                version=1,
                priority=0,
                deleted=False,
                created_at=now,
                last_touched_at=now,
            )
        )
        before = {
            name: db.execute(select(table)).all()
            for name, table in old.tables.items()
            if name != "alembic_version"
        }
    for _ in range(2):
        result = run_alembic(url, "upgrade", "0015")
        assert result.returncode == 0, result.stderr
        with engine.begin() as db:
            for name, table in old.tables.items():
                if name != "alembic_version":
                    assert db.execute(select(table)).all() == before[name]
            assert (
                db.scalar(text("SELECT conversation_recall_after = context_reset_at FROM users"))
                == 1
            )
            assert db.scalar(text("SELECT intention_context FROM commitments")) in ({}, "{}")
            db.execute(
                text(
                    'UPDATE commitments SET intention_context=\'{"purpose":{"basis":"inferred"}}\''
                )
            )
        result = run_alembic(url, "downgrade", "0014")
        assert result.returncode == 0, result.stderr
        assert "intention_context" not in {
            c["name"] for c in inspect(engine).get_columns("commitments")
        }
        with engine.connect() as db:
            assert db.scalar(text("SELECT purpose FROM commitments")) == "Original purpose"
    engine.dispose()


if __name__ == "__main__":
    import os

    from sqlalchemy.engine import make_url

    url = os.environ["DATABASE_URL"]
    target = make_url(url)
    assert target.host in {None, "localhost", "127.0.0.1", "::1"}
    assert (target.database or "").endswith("_smoke_test")
    engine = create_engine(url)
    assert not inspect(engine).get_table_names(), "Use a fresh, empty isolated database"
    engine.dispose()
    exercise_migration(url)
    print("Two PostgreSQL 0014 -> 0015 -> 0014 cycles passed; all legacy columns preserved.")

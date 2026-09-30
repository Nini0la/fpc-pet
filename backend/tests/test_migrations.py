import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text


def run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"DATABASE_URL": database_url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def table_names(database_path: Path) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {row[0] for row in rows}


def column_names(database_path: Path, table: str) -> set[str]:
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def test_database_url_overrides_ini_for_upgrade_and_downgrade(tmp_path: Path):
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path}"

    upgraded = run_alembic(database_url, "upgrade", "head")

    assert upgraded.returncode == 0, upgraded.stderr
    assert {"users", "messages", "alembic_version"} <= table_names(database_path)
    assert database_url not in upgraded.stdout + upgraded.stderr

    downgraded = run_alembic(database_url, "downgrade", "base")

    assert downgraded.returncode == 0, downgraded.stderr
    assert "users" not in table_names(database_path)
    assert database_url not in downgraded.stdout + downgraded.stderr


def test_database_url_is_converted_to_a_sync_driver(tmp_path: Path):
    database_path = tmp_path / "async-configured.db"
    database_url = f"sqlite+aiosqlite:///{database_path}"

    upgraded = run_alembic(database_url, "upgrade", "head")

    assert upgraded.returncode == 0, upgraded.stderr
    assert "users" in table_names(database_path)
    assert database_url not in upgraded.stdout + upgraded.stderr


def test_initial_migration_uses_explicit_alembic_operations():
    migration = Path("alembic/versions/0001_persistent_continuity.py").read_text()

    assert "op.create_table" in migration
    assert "op.drop_table" in migration
    assert "metadata.create_all" not in migration
    assert "metadata.drop_all" not in migration


def test_daily_loop_migration_upgrades_and_downgrades_explicitly(tmp_path: Path):
    database_path = tmp_path / "daily-loop.db"
    database_url = f"sqlite:///{database_path}"

    upgraded = run_alembic(database_url, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr
    assert {"daily_briefings", "journal_entries", "reflection_prompts"} <= table_names(
        database_path
    )
    assert "timezone" in column_names(database_path, "users")
    assert "priority" in column_names(database_path, "commitments")

    downgraded = run_alembic(database_url, "downgrade", "0001")
    assert downgraded.returncode == 0, downgraded.stderr
    assert "users" in table_names(database_path)
    assert "journal_entries" not in table_names(database_path)
    assert "timezone" not in column_names(database_path, "users")
    migration = Path("alembic/versions/0002_daily_continuity_loop.py").read_text()
    assert "op.create_table" in migration
    assert "op.drop_table" in migration


def seed_duplicate_conversations(database_url: str) -> None:
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, username, created_at, timezone) "
                "VALUES ('user-1', 'owner', CURRENT_TIMESTAMP, 'UTC')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO conversation_sessions "
                "(id, user_id, created_at, last_activity_at) VALUES "
                "('conversation-1', 'user-1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
                "('conversation-2', 'user-1', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO messages "
                "(id, user_id, created_at, conversation_id, role, content, actor, ordinal) VALUES "
                "('message-1', 'user-1', CURRENT_TIMESTAMP, 'conversation-1', "
                "'user', 'first', 'user', 1), "
                "('message-2', 'user-1', CURRENT_TIMESTAMP, 'conversation-2', "
                "'assistant', 'second', 'assistant', 1)"
            )
        )
    engine.dispose()


def assert_conversation_constraints(database_url: str) -> None:
    engine = create_engine(database_url)
    inspector = inspect(engine)
    conversation_uniques = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("conversation_sessions")
    }
    message_uniques = {
        tuple(item["column_names"]) for item in inspector.get_unique_constraints("messages")
    }
    with engine.connect() as connection:
        conversations = connection.execute(
            text("SELECT id FROM conversation_sessions WHERE user_id = 'user-1'")
        ).all()
        messages = connection.execute(
            text(
                "SELECT conversation_id, ordinal FROM messages "
                "WHERE user_id = 'user-1' ORDER BY ordinal"
            )
        ).all()
    engine.dispose()
    assert len(conversations) == 1
    assert ("user_id",) in conversation_uniques
    assert ("conversation_id", "ordinal") in message_uniques
    assert messages == [(conversations[0][0], 1), (conversations[0][0], 2)]


def test_conversation_invariants_migrate_existing_rows_and_downgrade(tmp_path: Path):
    database_path = tmp_path / "conversation-invariants.db"
    database_url = f"sqlite:///{database_path}"
    assert run_alembic(database_url, "upgrade", "0002").returncode == 0
    seed_duplicate_conversations(database_url)

    upgraded = run_alembic(database_url, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr
    assert_conversation_constraints(database_url)

    downgraded = run_alembic(database_url, "downgrade", "0002")
    assert downgraded.returncode == 0, downgraded.stderr
    migration = Path("alembic/versions/0003_conversation_concurrency.py").read_text()
    assert "create_unique_constraint" in migration
    assert "drop_constraint" in migration


def test_conversation_invariant_migration_cycle_on_real_postgres():
    database_url = os.getenv("POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("POSTGRES_TEST_URL is required for PostgreSQL migration tests")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()

    assert run_alembic(database_url, "upgrade", "0002").returncode == 0
    seed_duplicate_conversations(database_url)
    upgraded = run_alembic(database_url, "upgrade", "head")
    assert upgraded.returncode == 0, upgraded.stderr
    assert_conversation_constraints(database_url)
    assert run_alembic(database_url, "downgrade", "0002").returncode == 0
    assert run_alembic(database_url, "upgrade", "head").returncode == 0

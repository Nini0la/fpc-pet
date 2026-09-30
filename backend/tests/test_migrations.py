import os
import sqlite3
import subprocess
import sys
from pathlib import Path


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

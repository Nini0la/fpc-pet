from __future__ import annotations

from enum import Enum
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session


class MutationResult(Enum):
    UPDATED = "updated"
    CONFLICT = "conflict"
    NOT_FOUND = "not_found"


def atomic_update(
    db: Session,
    model: Any,
    record_id: str,
    user_id: str,
    expected_version: int,
    values: dict[str, Any],
) -> MutationResult:
    """Tenant-scoped compare-and-swap for mutable owned records."""
    result = cast(
        CursorResult[Any],
        db.execute(
            update(model)
            .where(
                model.id == record_id,
                model.user_id == user_id,
                model.version == expected_version,
                model.deleted.is_(False),
            )
            .values(**values, version=expected_version + 1)
            .execution_options(synchronize_session=False)
        )
    )
    if result.rowcount == 1:
        db.expire_all()
        return MutationResult.UPDATED
    exists = db.scalar(
        select(model.id).where(
            model.id == record_id,
            model.user_id == user_id,
            model.deleted.is_(False),
        )
    )
    return MutationResult.CONFLICT if exists is not None else MutationResult.NOT_FOUND

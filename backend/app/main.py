from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import timedelta
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, or_, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from .agent import AgentRuntime, ConcurrentMutation, IdempotencyConflict, RuntimeEvent
from .models import (
    Base,
    Commitment,
    ConversationSession,
    Episode,
    Message,
    ProvenanceLink,
    Session,
    Thread,
    User,
    utcnow,
)
from .persistence import MutationResult, atomic_update
from .security import resolve_login_username

ENV = os.getenv("APP_ENV", "production")
MODEL_MODE = os.getenv("MODEL_MODE", "deterministic" if ENV in {"development", "test"} else "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
ACCESS_CODE = os.getenv("ACCESS_CODE", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
ORIGINS = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "").split(",") if x.strip()]
if ENV == "production" and MODEL_MODE == "deterministic":
    raise RuntimeError("Deterministic model disabled in production")
if MODEL_MODE != "deterministic":
    raise RuntimeError("No live model adapter is configured")
if ENV == "production" and (
    not DATABASE_URL or not ACCESS_CODE or len(SESSION_SECRET) < 32 or not ORIGINS
):
    raise RuntimeError(
        "Production requires DATABASE_URL, ACCESS_CODE, 32+ char SESSION_SECRET, "
        "and ALLOWED_ORIGINS"
    )
DATABASE_URL = DATABASE_URL or "sqlite:///./continuity.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
if ENV == "test":
    Base.metadata.create_all(engine)

app = FastAPI(title="Continuity API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
runtime = AgentRuntime()


def digest(value: str) -> str:
    return hmac.new(SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(request: Request, db: DBSession = Depends(db_session)) -> User:
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(401, "Authentication required")
    auth = db.scalar(
        select(Session).where(Session.token_hash == digest(token), Session.expires_at > utcnow())
    )
    if not auth:
        raise HTTPException(401, "Authentication required")
    user = db.get(User, auth.user_id)
    if not user:
        raise HTTPException(401, "Authentication required")
    return user


def mutation_guard(
    request: Request,
    x_csrf_token: Annotated[str | None, Header()] = None,
    db: DBSession = Depends(db_session),
) -> None:
    origin = request.headers.get("origin")
    if origin not in ORIGINS:
        raise HTTPException(403, "Mutation origin rejected")
    token = request.cookies.get("session")
    csrf = request.cookies.get("csrf_token")
    auth = db.scalar(select(Session).where(Session.token_hash == digest(token or "")))
    if (
        not auth
        or not csrf
        or not x_csrf_token
        or not hmac.compare_digest(csrf, x_csrf_token)
        or not hmac.compare_digest(auth.csrf_hash, digest(csrf))
    ):
        raise HTTPException(403, "CSRF validation failed")


class LoginIn(BaseModel):
    access_code: str = Field(min_length=1, max_length=512)
    username: str = Field(
        default="owner", min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$"
    )


@app.post("/api/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: DBSession = Depends(db_session)):
    if request.headers.get("origin") not in ORIGINS or not hmac.compare_digest(
        body.access_code, ACCESS_CODE
    ):
        raise HTTPException(401, "Invalid credentials")
    username = resolve_login_username(body.username, ENV)
    user = db.scalar(select(User).where(User.username == username))
    if not user:
        user = User(username=username)
        db.add(user)
        db.flush()
    raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    db.add(
        Session(
            user_id=user.id,
            token_hash=digest(raw),
            csrf_hash=digest(csrf),
            expires_at=utcnow() + timedelta(days=7),
        )
    )
    db.commit()
    secure = ENV == "production"
    response.set_cookie(
        "session", raw, httponly=True, secure=secure, samesite="strict", max_age=604800
    )
    response.set_cookie(
        "csrf_token", csrf, httponly=False, secure=secure, samesite="strict", max_age=604800
    )
    return {"username": user.username}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "username": user.username}


@app.post("/api/auth/logout", status_code=204, dependencies=[Depends(mutation_guard)])
def logout(
    request: Request,
    response: Response,
    db: DBSession = Depends(db_session),
    user: User = Depends(current_user),
):
    token = request.cookies.get("session")
    auth = db.scalar(
        select(Session).where(Session.token_hash == digest(token or ""), Session.user_id == user.id)
    )
    if auth:
        db.delete(auth)
        db.commit()
    response.delete_cookie("session")
    response.delete_cookie("csrf_token")


class ChatIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    event_id: str = Field(min_length=1, max_length=100)


@app.post("/api/chat/messages", status_code=201, dependencies=[Depends(mutation_guard)])
def send_message(
    body: ChatIn,
    response: Response,
    db: DBSession = Depends(db_session),
    user: User = Depends(current_user),
):
    conversation = db.scalar(
        select(ConversationSession)
        .where(ConversationSession.user_id == user.id)
        .order_by(ConversationSession.created_at)
    )
    if not conversation:
        conversation = ConversationSession(user_id=user.id)
        db.add(conversation)
        db.flush()
    try:
        result = runtime.handle(
            db, user.id, RuntimeEvent(body.event_id, "user_message", body.content, conversation.id)
        )
    except (IdempotencyConflict, ConcurrentMutation) as error:
        db.rollback()
        raise HTTPException(409, str(error)) from error
    if result["idempotent"]:
        response.status_code = 200
    return result


@app.get("/api/chat/messages")
def messages(db: DBSession = Depends(db_session), user: User = Depends(current_user)):
    rows = db.scalars(
        select(Message).where(Message.user_id == user.id).order_by(Message.created_at, Message.id)
    ).all()
    return [
        {"id": x.id, "role": x.role, "content": x.content, "created_at": x.created_at} for x in rows
    ]


def item_dict(x: Any) -> dict[str, Any]:
    return {
        c.name: getattr(x, c.name)
        for c in x.__table__.columns
        if c.name not in {"user_id", "deleted"}
    }


@app.get("/api/threads")
def threads(db: DBSession = Depends(db_session), user: User = Depends(current_user)):
    return [
        item_dict(x)
        for x in db.scalars(
            select(Thread).where(Thread.user_id == user.id, Thread.deleted.is_(False))
        ).all()
    ]


@app.get("/api/commitments")
def commitments(db: DBSession = Depends(db_session), user: User = Depends(current_user)):
    return [
        item_dict(x)
        for x in db.scalars(
            select(Commitment).where(Commitment.user_id == user.id, Commitment.deleted.is_(False))
        ).all()
    ]


def owned_thread(id: str, user: User, db: DBSession) -> Thread:
    item = db.scalar(
        select(Thread).where(Thread.id == id, Thread.user_id == user.id, Thread.deleted.is_(False))
    )
    if not item:
        raise HTTPException(404, "Not found")
    return item


def require_mutation(result: MutationResult) -> None:
    if result is MutationResult.CONFLICT:
        raise HTTPException(409, "Version conflict")
    if result is MutationResult.NOT_FOUND:
        raise HTTPException(404, "Not found")


@app.get("/api/threads/{id}")
def get_thread(id: str, db: DBSession = Depends(db_session), user: User = Depends(current_user)):
    return item_dict(owned_thread(id, user, db))


class Correction(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    version: int = Field(ge=1)


@app.patch("/api/threads/{id}", dependencies=[Depends(mutation_guard)])
def correct_thread(
    id: str,
    body: Correction,
    db: DBSession = Depends(db_session),
    user: User = Depends(current_user),
):
    require_mutation(atomic_update(db, Thread, id, user.id, body.version, {"title": body.title}))
    db.add(
        ProvenanceLink(
            user_id=user.id,
            target_id=id,
            source_type="correction",
            source_id=None,
            confidence=1.0,
            derivation="user-correction",
            metadata_only=True,
        )
    )
    db.commit()
    return item_dict(owned_thread(id, user, db))


@app.delete("/api/threads/{id}", status_code=204, dependencies=[Depends(mutation_guard)])
def delete_thread(
    id: str,
    version: Annotated[int | None, Query(ge=1)] = None,
    db: DBSession = Depends(db_session),
    user: User = Depends(current_user),
):
    item = owned_thread(id, user, db)
    require_mutation(
        atomic_update(
            db,
            Thread,
            id,
            user.id,
            version if version is not None else item.version,
            {"deleted": True, "title": "[deleted]"},
        )
    )
    db.commit()


def owned_record(model: Any, id: str, user: User, db: DBSession) -> Any:
    item = db.scalar(
        select(model).where(model.id == id, model.user_id == user.id, model.deleted.is_(False))
    )
    if not item:
        raise HTTPException(404, "Not found")
    return item


@app.get("/api/commitments/{id}")
def get_commitment(
    id: str, db: DBSession = Depends(db_session), user: User = Depends(current_user)
):
    return item_dict(owned_record(Commitment, id, user, db))


@app.patch("/api/commitments/{id}", dependencies=[Depends(mutation_guard)])
def correct_commitment(
    id: str,
    body: Correction,
    db: DBSession = Depends(db_session),
    user: User = Depends(current_user),
):
    require_mutation(
        atomic_update(db, Commitment, id, user.id, body.version, {"title": body.title})
    )
    db.add(
        ProvenanceLink(
            user_id=user.id,
            target_id=id,
            source_type="correction",
            source_id=None,
            confidence=1.0,
            derivation="user-correction",
            metadata_only=True,
        )
    )
    db.commit()
    return item_dict(owned_record(Commitment, id, user, db))


@app.delete("/api/commitments/{id}", status_code=204, dependencies=[Depends(mutation_guard)])
def delete_commitment(
    id: str,
    version: Annotated[int | None, Query(ge=1)] = None,
    db: DBSession = Depends(db_session),
    user: User = Depends(current_user),
):
    item = owned_record(Commitment, id, user, db)
    require_mutation(
        atomic_update(
            db,
            Commitment,
            id,
            user.id,
            version if version is not None else item.version,
            {"deleted": True, "title": "[deleted]"},
        )
    )
    db.commit()


@app.get("/api/provenance/{target_id}")
def provenance(
    target_id: str, db: DBSession = Depends(db_session), user: User = Depends(current_user)
):
    rows = db.scalars(
        select(ProvenanceLink)
        .where(ProvenanceLink.target_id == target_id, ProvenanceLink.user_id == user.id)
        .order_by(ProvenanceLink.created_at)
    ).all()
    if not rows:
        raise HTTPException(404, "Not found")
    return [
        {
            "id": x.id,
            "source_type": x.source_type,
            "source_id": x.source_id,
            "confidence": x.confidence,
            "derivation": x.derivation,
            "metadata_only": x.metadata_only,
        }
        for x in rows
    ]


class EpisodeIn(BaseModel):
    summary: str = Field(min_length=1, max_length=1000)
    actor: str = Field(pattern=r"^(user|assistant|joint|discussed_only)$")


@app.post("/api/episodes", status_code=201, dependencies=[Depends(mutation_guard)])
def create_episode(
    body: EpisodeIn, db: DBSession = Depends(db_session), user: User = Depends(current_user)
):
    e = Episode(
        user_id=user.id,
        summary=body.summary,
        actor=body.actor,
        source="explicit episode",
        confidence=1.0,
        derivation="user-authored",
    )
    db.add(e)
    db.flush()
    db.add(
        ProvenanceLink(
            user_id=user.id,
            target_id=e.id,
            source_type="episode",
            source_id=e.id,
            confidence=1.0,
            derivation="user-authored",
        )
    )
    db.commit()
    return item_dict(e)


class EpisodeCorrection(BaseModel):
    summary: str = Field(min_length=1, max_length=1000)
    version: int = Field(ge=1)


@app.get("/api/episodes/{id}")
def get_episode(id: str, db: DBSession = Depends(db_session), user: User = Depends(current_user)):
    return item_dict(owned_record(Episode, id, user, db))


@app.patch("/api/episodes/{id}", dependencies=[Depends(mutation_guard)])
def correct_episode(
    id: str,
    body: EpisodeCorrection,
    db: DBSession = Depends(db_session),
    user: User = Depends(current_user),
):
    require_mutation(
        atomic_update(db, Episode, id, user.id, body.version, {"summary": body.summary})
    )
    db.add(
        ProvenanceLink(
            user_id=user.id,
            target_id=id,
            source_type="correction",
            source_id=None,
            confidence=1.0,
            derivation="user-correction",
            metadata_only=True,
        )
    )
    db.commit()
    return item_dict(owned_record(Episode, id, user, db))


@app.delete("/api/episodes/{id}", status_code=204, dependencies=[Depends(mutation_guard)])
def delete_episode(
    id: str,
    version: Annotated[int | None, Query(ge=1)] = None,
    db: DBSession = Depends(db_session),
    user: User = Depends(current_user),
):
    item = owned_record(Episode, id, user, db)
    require_mutation(
        atomic_update(
            db,
            Episode,
            id,
            user.id,
            version if version is not None else item.version,
            {"deleted": True, "summary": "[deleted]"},
        )
    )
    db.commit()


@app.get("/api/history/recall")
def recall(
    q: str = Query(min_length=1, max_length=500),
    db: DBSession = Depends(db_session),
    user: User = Depends(current_user),
):
    terms = [t for t in q.split() if len(t) > 2][:20]
    condition = (
        or_(*[Episode.summary.ilike(f"%{t}%") for t in terms]) if terms else Episode.id == ""
    )
    rows = db.scalars(
        select(Episode)
        .where(Episode.user_id == user.id, Episode.deleted.is_(False), condition)
        .order_by(Episode.created_at)
    ).all()
    return [
        {
            "id": x.id,
            "summary": x.summary,
            "actor": x.actor,
            "confidence": x.confidence,
            "source": x.source,
        }
        for x in rows
    ]


class ScheduledIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    kind: str = Field(min_length=1, max_length=50)


@app.post("/api/events/scheduled", status_code=202, dependencies=[Depends(mutation_guard)])
def scheduled(
    body: ScheduledIn, db: DBSession = Depends(db_session), user: User = Depends(current_user)
):
    try:
        return runtime.handle(db, user.id, RuntimeEvent(body.event_id, body.kind))
    except (IdempotencyConflict, ConcurrentMutation) as error:
        db.rollback()
        raise HTTPException(409, str(error)) from error

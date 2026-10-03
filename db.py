"""
Storage for assessments and expert corrections.

Uses PostgreSQL when DATABASE_URL is set in .env, for example:
    DATABASE_URL=postgresql://user:password@host:5432/chronos
Without it, falls back to a local SQLite file (chronos.db) so the app still runs
with no setup. Tables are created automatically on startup.

Every reading is stored with exactly what the model was shown (input_text),
what it said (raw_output) and the parsed numbers. Corrections are kept as a
history: nothing is overwritten, and the newest active correction wins.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from sqlalchemy import create_engine, event, text


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{Path(__file__).parent / 'chronos.db'}"
    # Hosting providers hand out postgres:// or postgresql:// URLs; SQLAlchemy needs
    # to be told to use the psycopg (v3) driver.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _database_url()
IS_SQLITE = DATABASE_URL.startswith("sqlite")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("PRAGMA journal_mode = WAL")
        cur.close()

_ID = "INTEGER PRIMARY KEY AUTOINCREMENT" if IS_SQLITE else "BIGSERIAL PRIMARY KEY"
_REF = "INTEGER" if IS_SQLITE else "BIGINT"
_REAL = "REAL" if IS_SQLITE else "DOUBLE PRECISION"

SCHEMA = [
    f"""
    CREATE TABLE IF NOT EXISTS assessments (
        id                {_ID},
        created_at        TEXT NOT NULL,
        source            TEXT NOT NULL CHECK (source IN ('manual', 'pdf')),
        chronological_age {_REAL},
        filename          TEXT,
        answers_json      TEXT,
        input_text        TEXT NOT NULL,
        raw_output        TEXT NOT NULL,
        biological_age    {_REAL},
        life_expectancy   {_REAL},
        health_score      {_REAL},
        scores_json       TEXT,
        explanation       TEXT,
        examples_used     TEXT
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS corrections (
        id              {_ID},
        assessment_id   {_REF} NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
        created_at      TEXT NOT NULL,
        expert_name     TEXT NOT NULL,
        reason          TEXT NOT NULL,
        biological_age  {_REAL},
        life_expectancy {_REAL},
        health_score    {_REAL},
        scores_json     TEXT,
        active          INTEGER NOT NULL DEFAULT 1
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_corrections_assessment ON corrections(assessment_id)",
]

if not IS_SQLITE:
    # Supabase publishes every table in the public schema through its REST API, reachable
    # with the project's anon key. Turning on row level security with no policies closes
    # that door. This app connects as the database owner, which bypasses RLS, so it is
    # unaffected.
    SCHEMA += [
        "ALTER TABLE assessments ENABLE ROW LEVEL SECURITY",
        "ALTER TABLE corrections ENABLE ROW LEVEL SECURITY",
    ]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db() -> None:
    with engine.begin() as conn:
        for statement in SCHEMA:
            conn.execute(text(statement))


def _reading(row) -> dict:
    return {
        "biological_age": row["biological_age"],
        "life_expectancy": row["life_expectancy"],
        "health_score": row["health_score"],
        "scores": json.loads(row["scores_json"]) if row["scores_json"] else {},
    }


def _correction(row) -> dict:
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "expert_name": row["expert_name"],
        "reason": row["reason"],
        "active": bool(row["active"]),
        "reading": _reading(row),
    }


def save_assessment(*, source, input_text, raw_output, reading, chronological_age=None,
                    filename=None, answers=None, examples_used=None) -> int:
    with engine.begin() as conn:
        return conn.execute(
            text("""
                INSERT INTO assessments (
                    created_at, source, chronological_age, filename, answers_json, input_text,
                    raw_output, biological_age, life_expectancy, health_score, scores_json,
                    explanation, examples_used
                ) VALUES (
                    :created_at, :source, :chronological_age, :filename, :answers_json, :input_text,
                    :raw_output, :biological_age, :life_expectancy, :health_score, :scores_json,
                    :explanation, :examples_used
                )
                RETURNING id
            """),
            {
                "created_at": _now(),
                "source": source,
                "chronological_age": chronological_age,
                "filename": filename,
                "answers_json": json.dumps(answers) if answers is not None else None,
                "input_text": input_text,
                "raw_output": raw_output,
                "biological_age": reading.get("biological_age"),
                "life_expectancy": reading.get("life_expectancy"),
                "health_score": reading.get("health_score"),
                "scores_json": json.dumps(reading.get("scores") or {}),
                "explanation": reading.get("explanation"),
                "examples_used": json.dumps(examples_used or []),
            },
        ).scalar_one()


def get_assessment(assessment_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM assessments WHERE id = :id"), {"id": assessment_id}
        ).mappings().first()
        if row is None:
            return None
        fixes = conn.execute(
            text("SELECT * FROM corrections WHERE assessment_id = :id ORDER BY id"),
            {"id": assessment_id},
        ).mappings().all()

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "source": row["source"],
        "chronological_age": row["chronological_age"],
        "filename": row["filename"],
        "answers": json.loads(row["answers_json"]) if row["answers_json"] else None,
        "input_text": row["input_text"],
        "reading": {**_reading(row), "explanation": row["explanation"]},
        "examples_used": json.loads(row["examples_used"] or "[]"),
        "corrections": [_correction(f) for f in fixes],
    }


def list_assessments(limit: int = 50, offset: int = 0) -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT a.id, a.created_at, a.source, a.chronological_age, a.filename,
                       a.biological_age, a.health_score,
                       (SELECT COUNT(*) FROM corrections c
                         WHERE c.assessment_id = a.id AND c.active = 1) AS correction_count
                FROM assessments a
                ORDER BY a.id DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        ).mappings().all()
    return [dict(r) for r in rows]


def add_correction(assessment_id: int, *, expert_name: str, reason: str, reading: dict) -> int:
    with engine.begin() as conn:
        return conn.execute(
            text("""
                INSERT INTO corrections (
                    assessment_id, created_at, expert_name, reason,
                    biological_age, life_expectancy, health_score, scores_json
                ) VALUES (
                    :assessment_id, :created_at, :expert_name, :reason,
                    :biological_age, :life_expectancy, :health_score, :scores_json
                )
                RETURNING id
            """),
            {
                "assessment_id": assessment_id,
                "created_at": _now(),
                "expert_name": expert_name,
                "reason": reason,
                "biological_age": reading.get("biological_age"),
                "life_expectancy": reading.get("life_expectancy"),
                "health_score": reading.get("health_score"),
                "scores_json": json.dumps(reading.get("scores") or {}),
            },
        ).scalar_one()


def latest_correction(assessment_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT * FROM corrections
                WHERE assessment_id = :id AND active = 1
                ORDER BY id DESC LIMIT 1
            """),
            {"id": assessment_id},
        ).mappings().first()
    return _correction(row) if row else None


def corrected_assessment_ids() -> list[int]:
    """Every assessment with at least one active correction, used to rebuild the learning index."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT assessment_id FROM corrections WHERE active = 1 ORDER BY assessment_id")
        ).all()
    return [r[0] for r in rows]
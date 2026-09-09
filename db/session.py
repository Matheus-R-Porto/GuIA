"""Engine e sessão do banco.

Fase 1: SQLite local em %APPDATA%/GuIA/guia.db (mesmo padrão do config.json
em user_config.py). Trocar de banco no futuro (ex: Turso) é mudar só a
_DB_URL abaixo — nada mais no projeto depende do backend específico.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session

from db.models import Base

_PENDING_COLUMNS = {
    "users": {
        "password_hash": "VARCHAR(200) DEFAULT ''",
        "institution_id": "INTEGER",
    },
}

_DATA_DIR = Path(os.getenv("APPDATA") or Path.home()) / "GuIA"
_DB_PATH = _DATA_DIR / "guia.db"
_DB_URL = f"sqlite:///{_DB_PATH}"

_engine = None
_SessionLocal = None


def _ensure_engine():
    global _engine, _SessionLocal
    if _engine is None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(_DB_URL, connect_args={"check_same_thread": False})
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def _migrate_missing_columns(engine):
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    for table, columns in _PENDING_COLUMNS.items():
        if table not in existing_tables:
            continue  # tabela nova — create_all() já criou com as colunas certas
        existing_cols = {c["name"] for c in inspector.get_columns(table)}
        missing = {name: ddl for name, ddl in columns.items() if name not in existing_cols}
        if not missing:
            continue
        with engine.begin() as conn:
            for name, ddl in missing.items():
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db():
    """Cria as tabelas que faltam e migra colunas novas em tabelas já
    existentes. Chamar uma vez no início do app."""
    engine = _ensure_engine()
    Base.metadata.create_all(engine)
    _migrate_missing_columns(engine)


def get_session() -> Session:
    _ensure_engine()
    return _SessionLocal()

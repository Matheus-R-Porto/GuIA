"""Persistência do GuIA (SQLAlchemy).

Fase 1 (atual): SQLite local em %APPDATA%/GuIA/guia.db.
Fase 2 (futura, com login multi-dispositivo): trocar a connection string em
`db/session.py` para um banco na nuvem (Turso é o primeiro candidato — já é
SQLite-nativo, então a migração é de baixo atrito). O resto do código (models,
repository) não muda.
"""
from .repository import (
    create_conversation,
    add_message,
    log_safety_block,
    list_conversations,
    get_conversation_messages,
    rename_conversation,
    delete_conversation,
    seed_test_institution,
    get_institution_by_code,
    create_user,
    list_users,
    get_user,
    check_user_password,
)
from .session import init_db

__all__ = [
    "init_db",
    "create_conversation",
    "add_message",
    "log_safety_block",
    "list_conversations",
    "get_conversation_messages",
    "rename_conversation",
    "delete_conversation",
    "seed_test_institution",
    "get_institution_by_code",
    "create_user",
    "list_users",
    "get_user",
    "check_user_password",
]

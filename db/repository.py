"""Camada de acesso ao banco — funções de alto nível usadas pelo resto do app.

O app_controller e a UI não devem importar db.models/db.session diretamente;
tudo passa por aqui, para que trocar de backend (SQLite -> Turso) ou reformar
o schema não vaze para o resto do código.
"""
import json

from auth import hash_password, verify_password
from db.models import User, Conversation, Message, SafetyBlock
from db.session import get_session

def create_user(name: str, password: str) -> dict:
    """Cria um perfil local com acesso de aluno, sem privilégios por instituição."""
    name = (name or "").strip()
    if not name or not password:
        raise ValueError("Nome e senha são obrigatórios para criar um perfil.")
    with get_session() as session:
        user = User(
            name=(name or "").strip(),
            role="aluno",
            password_hash=hash_password(password) if password else "",
            institution_id=None,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return {"id": user.id, "name": user.name, "role": "aluno"}


def list_users() -> list[dict]:
    """Lista os perfis locais para o seletor de login."""
    with get_session() as session:
        rows = session.query(User).order_by(User.created_at).all()
        return [
            {
                "id": u.id,
                "name": u.name,
                "role": "aluno",
                "has_password": bool(u.password_hash),
            }
            for u in rows
        ]


def get_user(user_id: int) -> dict | None:
    with get_session() as session:
        user = session.get(User, user_id)
        if user is None:
            return None
        return {
            "id": user.id,
            "name": user.name,
            "role": "aluno",
            "education_level": user.education_level,
        }


def check_user_password(user_id: int, password: str) -> bool:
    """True se a senha bater. Perfis legados sem senha (password_hash vazio,
    de antes deste campo existir) entram sem checagem."""
    with get_session() as session:
        user = session.get(User, user_id)
        if user is None:
            return False
        if not user.password_hash:
            return True
        return verify_password(password, user.password_hash)


def create_conversation(user_id: int, title: str = "Nova conversa", provider_used: str = "") -> int:
    with get_session() as session:
        conv = Conversation(user_id=user_id, title=title, provider_used=provider_used)
        session.add(conv)
        session.commit()
        session.refresh(conv)
        return conv.id


def add_message(conversation_id: int, role: str, content: str) -> int:
    """Adiciona uma mensagem ao fim da conversa. Retorna o id da mensagem."""
    with get_session() as session:
        count = (
            session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .count()
        )
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            order_index=count,
        )
        session.add(msg)
        session.commit()
        session.refresh(msg)
        return msg.id


def log_safety_block(message_id: int, pattern_matched: str = ""):
    with get_session() as session:
        session.add(SafetyBlock(message_id=message_id, pattern_matched=pattern_matched))
        session.commit()


def list_conversations(user_id: int) -> list[dict]:
    """Lista as conversas do usuário, mais recentes primeiro."""
    with get_session() as session:
        rows = (
            session.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        return [
            {
                "id": c.id,
                "title": c.title,
                "provider_used": c.provider_used,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in rows
        ]


def get_conversation_messages(conversation_id: int) -> list[dict]:
    with get_session() as session:
        rows = (
            session.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.order_index)
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in rows]


def rename_conversation(conversation_id: int, title: str):
    title = (title or "").strip()
    if not title:
        return
    with get_session() as session:
        conv = session.get(Conversation, conversation_id)
        if conv is not None:
            conv.title = title[:200]
            session.commit()


def delete_conversation(conversation_id: int):
    with get_session() as session:
        conv = session.get(Conversation, conversation_id)
        if conv is not None:
            session.delete(conv)
            session.commit()


def create_quiz_conversation(user_id: int, title: str, context: dict, intro: str) -> int:
    """Persist the question snapshot and welcome message in one transaction."""
    with get_session() as session:
        conv = Conversation(user_id=user_id, title=title[:200],
                            quiz_context=json.dumps(context, ensure_ascii=False))
        session.add(conv)
        session.flush()
        session.add(Message(conversation_id=conv.id, role="assistant", content=intro, order_index=0))
        session.commit()
        return conv.id


def get_quiz_context(conversation_id: int) -> dict | None:
    with get_session() as session:
        conv = session.get(Conversation, conversation_id)
        if conv is None or not conv.quiz_context:
            return None
        try:
            context = json.loads(conv.quiz_context)
        except (ValueError, TypeError):
            return None
        return context if isinstance(context, dict) else None

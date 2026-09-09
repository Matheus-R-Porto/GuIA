"""Camada de acesso ao banco — funções de alto nível usadas pelo resto do app.

O app_controller e a UI não devem importar db.models/db.session diretamente;
tudo passa por aqui, para que trocar de backend (SQLite -> Turso) ou reformar
o schema não vaze para o resto do código.
"""
from auth import hash_password, verify_password
from db.models import User, Conversation, Message, SafetyBlock, Institution
from db.session import get_session

_TEST_INSTITUTION_CODE = "IFSUL2026"
_TEST_INSTITUTION_NAME = "IFSul - Campus Sapiranga (código de teste)"


def seed_test_institution():
    """Cria a instituição de teste, se ainda não existir — permite testar o
    fluxo de criação de perfil professor sem um processo real de emissão de
    código (isso é trabalho futuro, fora de escopo por ora)."""
    with get_session() as session:
        exists = (
            session.query(Institution)
            .filter(Institution.code == _TEST_INSTITUTION_CODE)
            .first()
        )
        if exists is None:
            session.add(Institution(name=_TEST_INSTITUTION_NAME, code=_TEST_INSTITUTION_CODE))
            session.commit()


def get_institution_by_code(code: str) -> dict | None:
    code = (code or "").strip()
    if not code:
        return None
    with get_session() as session:
        inst = session.query(Institution).filter(Institution.code == code).first()
        if inst is None:
            return None
        return {"id": inst.id, "name": inst.name, "code": inst.code}


def create_user(name: str, password: str, institution_code: str = "") -> dict:
    """Cria um perfil local. Role NUNCA é auto-declarado: só vira "professor"
    se institution_code bater com uma instituição cadastrada."""
    institution = get_institution_by_code(institution_code)
    role = "professor" if institution else "aluno"
    with get_session() as session:
        user = User(
            name=(name or "").strip(),
            role=role,
            password_hash=hash_password(password) if password else "",
            institution_id=institution["id"] if institution else None,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return {"id": user.id, "name": user.name, "role": user.role}


def list_users() -> list[dict]:
    """Lista os perfis locais para o seletor de login."""
    with get_session() as session:
        rows = session.query(User).order_by(User.created_at).all()
        return [
            {
                "id": u.id,
                "name": u.name,
                "role": u.role,
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
            "role": user.role,
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

"""Modelos SQLAlchemy do GuIA.

Schema baseado no modelo conceitual já presente no relatório do 1º semestre
(Conversa -> Mensagem -> Bloqueio), estendido com User para preparar o Login
que vem no roadmap do 2º semestre.
"""
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Institution(Base):
    """Instituição com código de acesso ao modo professor.

    Uma única linha por escola — o código é compartilhado por todos os
    professores dela (não é emitido por professor individual). Sem geração/
    revogação dinâmica ainda: por ora, semeado manualmente (ver
    db.seed_test_institution) para permitir testar o fluxo.
    """
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class User(Base):
    """Perfil local do usuário (login por perfil, não por conta de rede).

    Senha é opcional apenas para perfis legados (criados antes deste campo
    existir, password_hash=""); todo perfil novo exige senha. O papel
    (aluno/professor) NUNCA é auto-declarado: só vira "professor" se o
    código de instituição informado na criação for válido.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), default="")
    role: Mapped[str] = mapped_column(String(20), default="aluno")  # "aluno" | "professor"
    education_level: Mapped[str] = mapped_column(String(20), default="")
    password_hash: Mapped[str] = mapped_column(String(200), default="")
    institution_id: Mapped[int | None] = mapped_column(
        ForeignKey("institutions.id"), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="Nova conversa")
    provider_used: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.order_index",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    safety_block: Mapped["SafetyBlock | None"] = relationship(
        back_populates="message", cascade="all, delete-orphan", uselist=False
    )


class SafetyBlock(Base):
    """Registro de bloqueio do safety.py — dado bruto para a pesquisa do TCC
    (quantas tentativas de má-fé ocorreram, com qual padrão)."""
    __tablename__ = "safety_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True)
    pattern_matched: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    message: Mapped["Message"] = relationship(back_populates="safety_block")

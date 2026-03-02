from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    credits_balance: Mapped[float] = mapped_column(Float, default=1000.0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())

    credit_records: Mapped[List["CreditRecord"]] = relationship(back_populates="user", lazy="selectin")
    projects: Mapped[List["Project"]] = relationship(back_populates="user", lazy="selectin")
    generations: Mapped[List["GenerationHistory"]] = relationship(back_populates="user", lazy="selectin")


class CreditRecord(Base):
    __tablename__ = "credit_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(200))
    feature_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="credit_records")


class GenerationHistory(Base):
    __tablename__ = "generation_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("projects.id"), index=True, nullable=True)
    feature_key: Mapped[str] = mapped_column(String(100))
    prompt_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    room_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    input_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    result_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    credits_cost: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="generations")
    project: Mapped[Optional["Project"]] = relationship(back_populates="generations")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="projects")
    generations: Mapped[List["GenerationHistory"]] = relationship(back_populates="project", lazy="selectin")
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.models_base import Base, TimestampMixin


class University(Base, TimestampMixin):
    __tablename__ = "universities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    templates: Mapped[list["Template"]] = relationship(back_populates="university")


class Gost(Base, TimestampMixin):
    __tablename__ = "gosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    templates: Mapped[list["TemplateVersionGost"]] = relationship(back_populates="gost")


class Template(Base, TimestampMixin):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    university_id: Mapped[int] = mapped_column(ForeignKey("universities.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type_work: Mapped[str] = mapped_column(String(64), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    university: Mapped[University] = relationship(back_populates="templates")
    versions: Mapped[list["TemplateVersion"]] = relationship(back_populates="template")


class TemplateVersion(Base, TimestampMixin):
    """
    Версионированный шаблон проверки.

    Поле rules_json хранит универсальный конфиг проверки (ГОСТ + профиль вуза),
    который понимает rules engine.
    """

    __tablename__ = "template_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("templates.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    rules_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)

    template: Mapped[Template] = relationship(back_populates="versions")
    gost_bindings: Mapped[list["TemplateVersionGost"]] = relationship(back_populates="template_version")
    checks: Mapped[list["Check"]] = relationship(back_populates="template_version")


class TemplateVersionGost(Base, TimestampMixin):
    """
    Связка версии шаблона и ГОСТа/стиля.

    Позволяет переиспользовать один универсальный конфиг с разными наборами правил для ГОСТ.
    """

    __tablename__ = "template_versions_gosts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_version_id: Mapped[int] = mapped_column(ForeignKey("template_versions.id"), nullable=False)
    gost_id: Mapped[int] = mapped_column(ForeignKey("gosts.id"), nullable=False)

    template_version: Mapped[TemplateVersion] = relationship(back_populates="gost_bindings")
    gost: Mapped[Gost] = relationship(back_populates="templates")


class File(Base, TimestampMixin):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)


class Check(Base, TimestampMixin):
    __tablename__ = "checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    template_version_id: Mapped[int] = mapped_column(ForeignKey("template_versions.id"), nullable=False)
    gost_id: Mapped[int | None] = mapped_column(ForeignKey("gosts.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")

    input_file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), nullable=False)
    result_report_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"), nullable=True)
    output_file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id"), nullable=True)

    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="checks")
    template_version: Mapped[TemplateVersion] = relationship(back_populates="checks")
    gost: Mapped[Gost | None] = relationship()


class BotContent(Base, TimestampMixin):
    __tablename__ = "bot_content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)








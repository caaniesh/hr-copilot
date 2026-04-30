from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ResumeUpload(Base):
    __tablename__ = "resume_uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parser_used: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_preview: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    parsing_warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    versions: Mapped[list["CandidateVersion"]] = relationship(back_populates="upload")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latest_version_number: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    versions: Mapped[list["CandidateVersion"]] = relationship(
        back_populates="candidate",
        order_by="CandidateVersion.version_number",
        cascade="all, delete-orphan",
    )


class CandidateVersion(Base):
    __tablename__ = "candidate_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), nullable=False, index=True)
    upload_id: Mapped[str | None] = mapped_column(ForeignKey("resume_uploads.id"), nullable=True, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    job_role: Mapped[str] = mapped_column(String(255), nullable=False)
    job_context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    validation_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    bias_reduced_profile: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    skill_analysis: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    role_alignment: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    scoring_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    confidence_result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ai_insights: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    interview_questions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    coding_assessment: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    final_decision: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    override_recommendation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    candidate: Mapped["Candidate"] = relationship(back_populates="versions")
    upload: Mapped[ResumeUpload | None] = relationship(back_populates="versions")


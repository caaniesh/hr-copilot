from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db import Candidate, CandidateVersion, ResumeUpload
from app.models.schemas import (
    AIInsightsResult,
    BiasReducedProfile,
    CodingAssessment,
    ConfidenceResult,
    FinalDecisionResult,
    JobContext,
    RoleAlignmentResult,
    ScoreBreakdown,
    SkillAnalysisResult,
    ValidationResult,
)


class CandidateStorageService:
    """Persists uploads, versions, and decision overrides."""

    def create_upload(
        self,
        db: Session,
        *,
        filename: str,
        stored_path: Path,
        content_type: str | None,
        parser_used: str,
        raw_text: str,
        extracted_preview: dict,
        warnings: list[str],
    ) -> ResumeUpload:
        upload = ResumeUpload(
            original_filename=filename,
            stored_path=str(stored_path),
            content_type=content_type,
            parser_used=parser_used,
            raw_text=raw_text,
            extracted_preview=extracted_preview,
            parsing_warnings=warnings,
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)
        return upload

    def get_upload(self, db: Session, upload_id: str) -> ResumeUpload | None:
        return db.get(ResumeUpload, upload_id)

    def save_analysis(
        self,
        db: Session,
        *,
        upload: ResumeUpload,
        validation: ValidationResult,
        bias_profile: BiasReducedProfile,
        skill_analysis: SkillAnalysisResult,
        role_alignment: RoleAlignmentResult,
        score_breakdown: ScoreBreakdown,
        confidence: ConfidenceResult,
        insights: AIInsightsResult,
        interview_questions: list[dict],
        coding_assessment: CodingAssessment,
        final_decision: FinalDecisionResult,
        job_context: JobContext,
        override_recommendation: str | None = None,
        override_reason: str | None = None,
    ) -> tuple[Candidate, CandidateVersion]:
        candidate = self._find_or_create_candidate(db, validation.normalized_data.email, validation.normalized_data.phone)
        normalized = validation.normalized_data
        candidate.name = normalized.name or candidate.name
        candidate.email = normalized.email or candidate.email
        candidate.phone = normalized.phone or candidate.phone
        candidate.location = normalized.location or candidate.location
        candidate.latest_version_number += 1

        version = CandidateVersion(
            candidate=candidate,
            upload=upload,
            version_number=candidate.latest_version_number,
            source_filename=upload.original_filename,
            job_role=job_context.role,
            job_context=job_context.model_dump(),
            raw_text=upload.raw_text,
            extracted_data=normalized.model_dump(),
            validation_result=validation.model_dump(),
            bias_reduced_profile=bias_profile.model_dump(),
            skill_analysis=skill_analysis.model_dump(),
            role_alignment=role_alignment.model_dump(),
            scoring_result=score_breakdown.model_dump(),
            confidence_result=confidence.model_dump(),
            ai_insights=insights.model_dump(),
            interview_questions=interview_questions,
            coding_assessment=coding_assessment.model_dump(),
            final_decision=final_decision.model_dump(),
            override_recommendation=override_recommendation,
            override_reason=override_reason,
        )
        db.add(candidate)
        db.add(version)
        db.commit()
        db.refresh(candidate)
        db.refresh(version)
        return candidate, version

    def get_candidate(self, db: Session, candidate_id: str) -> Candidate | None:
        return db.get(Candidate, candidate_id)

    def get_version(
        self,
        db: Session,
        candidate_id: str,
        version_id: str | None = None,
    ) -> CandidateVersion | None:
        if version_id:
            version = db.get(CandidateVersion, version_id)
            if version and version.candidate_id == candidate_id:
                return version
            return None

        stmt = (
            select(CandidateVersion)
            .where(CandidateVersion.candidate_id == candidate_id)
            .order_by(CandidateVersion.version_number.desc())
        )
        return db.execute(stmt).scalars().first()

    def list_latest_versions(self, db: Session, candidate_id: str | None = None) -> list[tuple[Candidate, CandidateVersion]]:
        candidates: list[Candidate]
        if candidate_id:
            candidate = db.get(Candidate, candidate_id)
            candidates = [candidate] if candidate else []
        else:
            candidates = list(db.execute(select(Candidate)).scalars().all())

        results: list[tuple[Candidate, CandidateVersion]] = []
        for candidate in candidates:
            version = self.get_version(db, candidate.id)
            if version:
                results.append((candidate, version))
        return results

    def apply_override(
        self,
        db: Session,
        *,
        candidate_id: str,
        version_id: str | None,
        recommendation: str,
        reason: str,
    ) -> CandidateVersion:
        version = self.get_version(db, candidate_id, version_id)
        if not version:
            raise ValueError("Candidate version not found.")

        final_decision = dict(version.final_decision)
        original_recommendation = final_decision.get("recommendation", "Unknown")
        final_decision["recommendation"] = recommendation
        final_decision["overridden_by_hr"] = True
        final_decision["override_reason"] = reason
        final_decision["explanation"] = (
            f"Recommendation was overridden by HR from {original_recommendation} to {recommendation}. "
            f"Reason: {reason}"
        )

        version.override_recommendation = recommendation
        version.override_reason = reason
        version.final_decision = final_decision
        db.add(version)
        db.commit()
        db.refresh(version)
        return version

    def _find_or_create_candidate(self, db: Session, email: str | None, phone: str | None) -> Candidate:
        by_email = (
            db.execute(select(Candidate).where(Candidate.email == email)).scalars().first()
            if email
            else None
        )
        by_phone = (
            db.execute(select(Candidate).where(Candidate.phone == phone)).scalars().first()
            if phone
            else None
        )

        if by_email and by_phone and by_email.id != by_phone.id:
            raise ValueError("Email and phone already belong to different candidate records.")

        candidate = by_email or by_phone
        if candidate:
            return candidate

        candidate = Candidate(email=email, phone=phone, latest_version_number=0)
        db.add(candidate)
        db.flush()
        return candidate

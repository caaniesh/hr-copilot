from __future__ import annotations

from app.models.schemas import ExtractedCandidateData, ValidationResult
from app.utils.text import deduplicate_preserve_order, normalize_phone, normalize_skill


class ValidationService:
    """Normalizes extracted data and flags low-confidence records."""

    def validate(self, extracted: ExtractedCandidateData) -> ValidationResult:
        normalized = extracted.model_copy(deep=True)
        normalized.email = normalized.email.lower() if normalized.email else None
        normalized.phone = normalize_phone(normalized.phone)
        normalized.skills = deduplicate_preserve_order(
            normalize_skill(skill) for skill in normalized.skills if skill.strip()
        )
        normalized.projects = [
            project.model_copy(
                update={
                    "title": project.title.strip(),
                    "summary": project.summary.strip(),
                    "technologies": deduplicate_preserve_order(
                        normalize_skill(tech) for tech in project.technologies if tech.strip()
                    ),
                }
            )
            for project in normalized.projects
            if project.title.strip() and project.summary.strip()
        ]

        missing_fields: list[str] = []
        if not normalized.name:
            missing_fields.append("name")
        if not normalized.email:
            missing_fields.append("email")
        if not normalized.phone:
            missing_fields.append("phone")
        if not normalized.experience and normalized.experience_years is None:
            missing_fields.append("experience")
        if not normalized.skills:
            missing_fields.append("skills")
        if not normalized.projects:
            missing_fields.append("projects")

        completeness = self._data_completeness(normalized)
        warnings: list[str] = []
        if normalized.extraction_confidence < 70:
            warnings.append("Extraction confidence is below 70; manual review is recommended.")
        if not normalized.email and not normalized.phone:
            warnings.append("Primary contact details are incomplete.")
        if not normalized.projects:
            warnings.append("No project evidence was extracted, so interview depth may be limited.")
        if completeness < 60:
            warnings.append("Profile completeness is low; check the resume formatting or source quality.")

        return ValidationResult(
            normalized_data=normalized,
            missing_fields=missing_fields,
            warnings=warnings,
            warning_flag=normalized.extraction_confidence < 70,
            data_completeness=completeness,
        )

    def _data_completeness(self, candidate: ExtractedCandidateData) -> float:
        checks = [
            bool(candidate.name),
            bool(candidate.email),
            bool(candidate.phone),
            bool(candidate.experience or candidate.experience_years is not None),
            bool(candidate.skills),
            bool(candidate.projects),
        ]
        score = (sum(checks) / len(checks)) * 100
        return round(score, 2)


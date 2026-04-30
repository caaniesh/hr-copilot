from __future__ import annotations

from app.models.schemas import BiasReducedProfile, ValidationResult


class BiasRemovalService:
    """Provides a redacted profile so analysis ignores personal identifiers."""

    def redact(self, validation_result: ValidationResult) -> BiasReducedProfile:
        profile = validation_result.normalized_data
        return BiasReducedProfile(
            experience=profile.experience,
            experience_years=profile.experience_years,
            skills=profile.skills,
            projects=profile.projects,
        )


from __future__ import annotations

import re

from app.models.schemas import (
    BiasReducedProfile,
    ConfidenceResult,
    ExperienceLevel,
    FinalDecisionResult,
    JobContext,
    RoleAlignmentResult,
    ScoreBreakdown,
    SkillAnalysisResult,
    SkillAssessment,
)
from app.utils.text import deduplicate_preserve_order, normalize_skill, skill_in_text


class ScoringService:
    """Deterministic scoring and decision logic."""

    def analyze_skills(self, profile: BiasReducedProfile, job_context: JobContext) -> SkillAnalysisResult:
        required_skills = {normalize_skill(skill) for skill in job_context.required_skills if skill.strip()}
        primary: list[SkillAssessment] = []
        secondary: list[SkillAssessment] = []

        for skill in profile.skills:
            normalized_skill = normalize_skill(skill)
            evidence_projects = [
                project.title
                for project in profile.projects
                if skill_in_text(normalized_skill, project.summary)
                or any(skill_in_text(normalized_skill, tech) for tech in project.technologies)
                or skill_in_text(normalized_skill, project.title)
            ]
            evidence_count = len(evidence_projects)
            depth = self._estimate_depth(
                evidence_count=evidence_count,
                experience_years=profile.experience_years,
                primary_skill=normalized_skill in required_skills,
            )
            confidence = 90.0 if evidence_count else 55.0
            evidence = (
                f"Referenced in project(s): {', '.join(evidence_projects)}"
                if evidence_projects
                else "Listed in the resume without project evidence."
            )
            assessment = SkillAssessment(
                name=normalized_skill,
                category="Primary" if normalized_skill in required_skills else "Secondary",
                depth=depth,
                confidence=confidence,
                evidence=evidence,
            )
            if normalized_skill in required_skills:
                primary.append(assessment)
            else:
                secondary.append(assessment)

        return SkillAnalysisResult(primary_skills=primary, secondary_skills=secondary)

    def check_role_alignment(
        self,
        profile: BiasReducedProfile,
        job_context: JobContext,
        score_breakdown: ScoreBreakdown | None = None,
    ) -> RoleAlignmentResult:
        matched_skills = score_breakdown.matched_skills if score_breakdown else []
        required = [normalize_skill(skill) for skill in job_context.required_skills if skill.strip()]
        skill_match_score = (len(matched_skills) / len(required) * 100) if required else 100.0

        role_terms = [
            token
            for token in re.findall(r"[A-Za-z]+", job_context.role)
            if len(token) > 2 and token.casefold() not in {"and", "for", "the", "with", "senior", "junior"}
        ]
        profile_text = " ".join(
            [
                *profile.skills,
                *(project.title for project in profile.projects),
                *(project.summary for project in profile.projects),
            ]
        ).casefold()
        role_term_hits = sum(1 for term in role_terms if skill_in_text(term, profile_text))
        role_term_score = (role_term_hits / len(role_terms) * 100) if role_terms else 50.0

        alignment_score = round((skill_match_score * 0.7) + (role_term_score * 0.3), 2)
        aligned = alignment_score >= 45 and (not required or len(matched_skills) >= max(1, round(len(required) * 0.35)))
        warning = None
        if not aligned:
            warning = (
                f"Role alignment is weak for '{job_context.role}'. Only "
                f"{len(matched_skills)} of {len(required)} required skills matched."
            )

        rationale = (
            f"Skill overlap contributes {round(skill_match_score, 2)} and role-term evidence contributes "
            f"{round(role_term_score, 2)} to the alignment score."
        )
        return RoleAlignmentResult(
            aligned=aligned,
            alignment_score=alignment_score,
            warning=warning,
            rationale=rationale,
        )

    def score_candidate(
        self,
        profile: BiasReducedProfile,
        job_context: JobContext,
        skill_analysis: SkillAnalysisResult,
    ) -> ScoreBreakdown:
        required = deduplicate_preserve_order(
            normalize_skill(skill) for skill in job_context.required_skills if skill.strip()
        )
        candidate_skills = {normalize_skill(skill) for skill in profile.skills}
        matched_skills = [skill for skill in required if skill in candidate_skills]
        missing_skills = [skill for skill in required if skill not in candidate_skills]

        skill_score = round((len(matched_skills) / len(required) * 100), 2) if required else 100.0
        project_score = self._project_score(required, profile.projects)
        experience_score = self._experience_score(job_context.experience_level, profile.experience_years, profile.experience)
        weights = self._weights(job_context.experience_level)

        final_score = round(
            (skill_score * weights["skills"] / 100)
            + (project_score * weights["projects"] / 100)
            + (experience_score * weights["experience"] / 100),
            2,
        )

        explanation = [
            f"Matched {len(matched_skills)} of {len(required)} required skills." if required else "No required skills were provided, so skill score defaults to full credit.",
            f"Project evidence score is {project_score} based on {len(profile.projects)} extracted project(s).",
            (
                "Experience score is not weighted for fresher profiles."
                if job_context.experience_level == ExperienceLevel.FRESHER
                else f"Experience score is {experience_score} based on extracted experience evidence."
            ),
        ]

        return ScoreBreakdown(
            weights=weights,
            skill_score=skill_score,
            project_score=project_score,
            experience_score=experience_score,
            final_score=final_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            score_explanation=explanation,
        )

    def confidence_score(
        self,
        extraction_confidence: float,
        skill_match_score: float,
        data_completeness: float,
    ) -> ConfidenceResult:
        score = round(
            (extraction_confidence * 0.4) + (skill_match_score * 0.3) + (data_completeness * 0.3),
            2,
        )
        if score >= 75:
            band = "High"
        elif score >= 50:
            band = "Medium"
        else:
            band = "Low"
        explanation = (
            f"Confidence combines extraction ({extraction_confidence}), skill match ({skill_match_score}), "
            f"and completeness ({data_completeness})."
        )
        return ConfidenceResult(
            score=score,
            band=band,
            explanation=explanation,
            confidence_score=score,
            confidence_label=band,
        )

    def final_decision(
        self,
        *,
        score_breakdown: ScoreBreakdown,
        confidence: ConfidenceResult,
        strengths: list[str],
        weaknesses: list[str],
        role_alignment: RoleAlignmentResult,
        override_recommendation: str | None = None,
        override_reason: str | None = None,
        alternative_role_suggestion: str | None = None,
    ) -> FinalDecisionResult:
        recommendation = self._base_recommendation(score_breakdown.final_score, confidence.band, role_alignment.aligned)
        overridden = False
        if override_recommendation:
            recommendation = override_recommendation
            overridden = True

        explanation = (
            f"Recommendation is {recommendation} because the final score is {score_breakdown.final_score}, "
            f"confidence is {confidence.band}, and role alignment is "
            f"{'strong' if role_alignment.aligned else 'weak'}."
        )
        if overridden and override_reason:
            explanation += f" HR override reason: {override_reason}"

        return FinalDecisionResult(
            final_score=score_breakdown.final_score,
            top_strengths=strengths[:3],
            top_weaknesses=weaknesses[:3],
            recommendation=recommendation,
            confidence=confidence.band,
            recommendation_confidence=confidence.band,
            alternative_role_suggestion=alternative_role_suggestion,
            explanation=explanation,
            overridden_by_hr=overridden,
            override_reason=override_reason if overridden else None,
        )

    def _estimate_depth(
        self,
        *,
        evidence_count: int,
        experience_years: float | None,
        primary_skill: bool,
    ) -> str:
        years = experience_years or 0
        if evidence_count >= 2 or (primary_skill and years >= 4):
            return "Advanced"
        if evidence_count >= 1 or years >= 2:
            return "Intermediate"
        return "Beginner"

    def _project_score(self, required_skills: list[str], projects: list) -> float:
        if not projects:
            return 0.0

        if not required_skills:
            return round(min(len(projects), 3) / 3 * 100, 2)

        evidenced: set[str] = set()
        for project in projects:
            project_text = f"{project.title} {project.summary} {' '.join(project.technologies)}"
            for skill in required_skills:
                if skill_in_text(skill, project_text):
                    evidenced.add(skill)

        relevance_score = (len(evidenced) / len(required_skills)) * 80
        volume_score = (min(len(projects), 3) / 3) * 20
        return round(relevance_score + volume_score, 2)

    def _experience_score(
        self,
        experience_level: ExperienceLevel,
        experience_years: float | None,
        experience_text: str | None,
    ) -> float:
        if experience_level == ExperienceLevel.FRESHER:
            return 0.0
        years = experience_years or 0
        if years >= 5:
            return 100.0
        if years >= 3:
            return 85.0
        if years >= 2:
            return 70.0
        if years >= 1:
            return 50.0
        if experience_text:
            return 35.0
        return 20.0

    def _weights(self, experience_level: ExperienceLevel) -> dict[str, float]:
        if experience_level == ExperienceLevel.FRESHER:
            return {"skills": 50.0, "projects": 50.0, "experience": 0.0}
        return {"skills": 40.0, "projects": 30.0, "experience": 30.0}

    def _base_recommendation(self, final_score: float, confidence_band: str, aligned: bool) -> str:
        if not aligned and final_score < 70:
            return "Reject"
        if final_score >= 80 and confidence_band != "Low":
            return "Hire"
        if final_score >= 60:
            return "Hold"
        return "Reject"

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.models.schemas import (
    BiasReducedProfile,
    ConfidenceResult,
    FinalDecisionResult,
    JobContext,
    RoleAlignmentResult,
    ScoreBreakdown,
    SkillAnalysisResult,
)
from app.services.explainability import (
    build_skill_buckets,
    build_summary_card,
    build_why_this_score,
    infer_alternative_role,
)
from app.services.storage import CandidateStorageService
from app.utils.config import settings


class ExportService:
    """Creates Excel reports for one candidate or the latest version of all candidates."""

    headers = [
        "Name",
        "Email",
        "Phone",
        "Role",
        "Relevant Skills",
        "Other Skills",
        "Score",
        "Confidence",
        "Why This Score (summary)",
        "Strengths",
        "Weaknesses",
        "Recommendation",
        "Recommendation Confidence",
        "Better Fit Role",
        "Hiring Risk",
    ]

    def __init__(self) -> None:
        self.storage = CandidateStorageService()

    def export(self, db: Session, candidate_id: str | None = None) -> Path:
        rows = self._build_rows(db, candidate_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = settings.export_dir / f"candidate_report_{timestamp}.xlsx"

        try:
            import pandas as pd  # type: ignore

            dataframe = pd.DataFrame(rows, columns=self.headers)
            dataframe.to_excel(output_path, index=False, engine="openpyxl")
            return output_path
        except ImportError:
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Candidates"
            sheet.append(self.headers)
            for row in rows:
                sheet.append(row)
            workbook.save(output_path)
            return output_path

    def _build_rows(self, db: Session, candidate_id: str | None) -> list[list[str]]:
        records = self.storage.list_latest_versions(db, candidate_id)
        rows: list[list[str]] = []
        for candidate, version in records:
            extracted = version.extracted_data
            scoring = version.scoring_result
            insights = version.ai_insights
            decision = version.final_decision
            job_context = JobContext.model_validate(version.job_context)
            bias_profile = BiasReducedProfile.model_validate(version.bias_reduced_profile)
            skill_analysis = SkillAnalysisResult.model_validate(version.skill_analysis)
            score_breakdown = ScoreBreakdown.model_validate(scoring)
            role_alignment = RoleAlignmentResult.model_validate(version.role_alignment)
            confidence = ConfidenceResult.model_validate(version.confidence_result)
            fd = FinalDecisionResult.model_validate(decision)
            alt = infer_alternative_role(
                job_context=job_context,
                profile=bias_profile,
                role_alignment=role_alignment,
                score_breakdown=score_breakdown,
            )
            buckets = build_skill_buckets(
                job_context=job_context,
                profile=bias_profile,
                skill_analysis=skill_analysis,
            )
            why_lines = build_why_this_score(
                job_context=job_context,
                profile=bias_profile,
                score_breakdown=score_breakdown,
                role_alignment=role_alignment,
            )
            summary = build_summary_card(
                final_score=score_breakdown.final_score,
                role_alignment=role_alignment,
                recommendation=fd.recommendation,
                confidence_band=confidence.band,
                best_role_hint=alt or fd.alternative_role_suggestion,
            )
            rows.append(
                [
                    extracted.get("name") or candidate.name or "",
                    extracted.get("email") or candidate.email or "",
                    extracted.get("phone") or candidate.phone or "",
                    version.job_role,
                    ", ".join(buckets.relevant_skills),
                    ", ".join(buckets.other_skills),
                    str(scoring.get("final_score", "")),
                    f"{confidence.confidence_label} ({float(confidence.confidence_score or confidence.score):.0f}%)",
                    (why_lines[0] if why_lines else ""),
                    " | ".join(insights.get("strengths", [])[:3]),
                    " | ".join(insights.get("weaknesses", [])[:3]),
                    decision.get("recommendation", ""),
                    decision.get("recommendation_confidence") or decision.get("confidence", ""),
                    decision.get("alternative_role_suggestion") or "",
                    summary.hiring_risk,
                ]
            )
        return rows


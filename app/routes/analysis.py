from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BiasReducedProfile,
    CandidateReportResponse,
    CandidateSummary,
    CodingAssessment,
    ConfidenceResult,
    ExtractedCandidateData,
    FinalDecisionResult,
    InterviewQuestion,
    JobContext,
    RoleAlignmentResult,
    ScoreBreakdown,
    SkillAnalysisResult,
)
from app.services.ai_engine import AIInsightService
from app.services.bias import BiasRemovalService
from app.services.coding import CodingAssessmentService
from app.services.explainability import (
    build_skill_buckets,
    build_summary_card,
    build_why_this_score,
    infer_alternative_role,
    role_mismatch_warning,
)
from app.services.scoring import ScoringService
from app.services.storage import CandidateStorageService
from app.services.validation import ValidationService
from app.utils.hr_notes import humanize_parsing_warnings, humanize_validation_warnings


router = APIRouter(tags=["analysis"])

validation_service = ValidationService()
bias_service = BiasRemovalService()
scoring_service = ScoringService()
ai_service = AIInsightService()
coding_service = CodingAssessmentService()
storage_service = CandidateStorageService()


def _build_explainability_bundle(
    *,
    job_context: JobContext,
    bias_profile: BiasReducedProfile,
    skill_analysis: SkillAnalysisResult,
    score_breakdown: ScoreBreakdown,
    role_alignment: RoleAlignmentResult,
    confidence: ConfidenceResult,
    final_decision: FinalDecisionResult,
    alternative_role: str | None = None,
):
    alternative = alternative_role
    if alternative is None:
        alternative = infer_alternative_role(
            job_context=job_context,
            profile=bias_profile,
            role_alignment=role_alignment,
            score_breakdown=score_breakdown,
        )
    summary_card = build_summary_card(
        final_score=score_breakdown.final_score,
        role_alignment=role_alignment,
        recommendation=final_decision.recommendation,
        confidence_band=confidence.band,
        best_role_hint=alternative,
    )
    why_this_score = build_why_this_score(
        job_context=job_context,
        profile=bias_profile,
        score_breakdown=score_breakdown,
        role_alignment=role_alignment,
    )
    skill_buckets = build_skill_buckets(
        job_context=job_context,
        profile=bias_profile,
        skill_analysis=skill_analysis,
    )
    mismatch = role_mismatch_warning(
        job_context=job_context,
        profile=bias_profile,
        role_alignment=role_alignment,
        alternative=alternative,
    )
    return summary_card, why_this_score, skill_buckets, mismatch


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_candidate(request: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    upload = storage_service.get_upload(db, request.upload_id)
    if not upload:
        raise HTTPException(status_code=404, detail="Uploaded resume was not found.")

    extracted = ExtractedCandidateData.model_validate(upload.extracted_preview)
    validation = validation_service.validate(extracted)
    bias_profile = bias_service.redact(validation)
    skill_analysis = scoring_service.analyze_skills(bias_profile, request.job_context)
    score_breakdown = scoring_service.score_candidate(bias_profile, request.job_context, skill_analysis)
    role_alignment = scoring_service.check_role_alignment(bias_profile, request.job_context, score_breakdown)
    confidence = scoring_service.confidence_score(
        extraction_confidence=validation.normalized_data.extraction_confidence,
        skill_match_score=score_breakdown.skill_score,
        data_completeness=validation.data_completeness,
    )
    insights = ai_service.generate_insights(
        profile=bias_profile,
        validation=validation,
        skill_analysis=skill_analysis,
        score_breakdown=score_breakdown,
        role_alignment=role_alignment,
    )
    questions = ai_service.generate_questions(
        profile=bias_profile,
        skill_analysis=skill_analysis,
        job_context=request.job_context,
    )
    coding_questions = coding_service.generate_questions(bias_profile, request.job_context)
    coding_assessment = coding_service.evaluate(coding_questions, request.coding_submissions)
    alternative_role = infer_alternative_role(
        job_context=request.job_context,
        profile=bias_profile,
        role_alignment=role_alignment,
        score_breakdown=score_breakdown,
    )
    final_decision = scoring_service.final_decision(
        score_breakdown=score_breakdown,
        confidence=confidence,
        strengths=insights.strengths,
        weaknesses=insights.weaknesses,
        role_alignment=role_alignment,
        override_recommendation=request.override_recommendation,
        override_reason=request.override_reason,
        alternative_role_suggestion=alternative_role,
    )
    summary_card, why_this_score, skill_buckets, mismatch = _build_explainability_bundle(
        job_context=request.job_context,
        bias_profile=bias_profile,
        skill_analysis=skill_analysis,
        score_breakdown=score_breakdown,
        role_alignment=role_alignment,
        confidence=confidence,
        final_decision=final_decision,
        alternative_role=alternative_role,
    )

    try:
        candidate, version = storage_service.save_analysis(
            db,
            upload=upload,
            validation=validation,
            bias_profile=bias_profile,
            skill_analysis=skill_analysis,
            role_alignment=role_alignment,
            score_breakdown=score_breakdown,
            confidence=confidence,
            insights=insights,
            interview_questions=[question.model_dump() for question in questions],
            coding_assessment=coding_assessment,
            final_decision=final_decision,
            job_context=request.job_context,
            override_recommendation=request.override_recommendation,
            override_reason=request.override_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    candidate_summary = CandidateSummary(
        candidate_id=candidate.id,
        version_id=version.id,
        name=validation.normalized_data.name,
        email=validation.normalized_data.email,
        phone=validation.normalized_data.phone,
        location=validation.normalized_data.location,
        experience=validation.normalized_data.experience,
        experience_years=validation.normalized_data.experience_years,
        skills=validation.normalized_data.skills,
        projects=validation.normalized_data.projects,
        role=request.job_context.role,
    )

    hr_warnings = [
        *humanize_parsing_warnings(upload.parsing_warnings),
        *humanize_validation_warnings(validation.warnings),
    ]

    return AnalyzeResponse(
        candidate=candidate_summary,
        score_breakdown=score_breakdown,
        confidence=confidence,
        skill_analysis=skill_analysis,
        role_alignment=role_alignment,
        insights=insights,
        questions=questions,
        coding_assessment=coding_assessment,
        final_decision=final_decision,
        warnings=hr_warnings,
        summary_card=summary_card,
        why_this_score=why_this_score,
        skill_buckets=skill_buckets,
        role_mismatch_warning=mismatch,
    )


@router.get("/candidate/{candidate_id}", response_model=CandidateReportResponse)
def get_candidate_report(
    candidate_id: str,
    version_id: str | None = None,
    db: Session = Depends(get_db),
) -> CandidateReportResponse:
    candidate = storage_service.get_candidate(db, candidate_id)
    version = storage_service.get_version(db, candidate_id, version_id)
    if not candidate or not version:
        raise HTTPException(status_code=404, detail="Candidate analysis was not found.")

    extracted = ExtractedCandidateData.model_validate(version.extracted_data)
    questions = [InterviewQuestion.model_validate(item) for item in version.interview_questions]
    coding_assessment = CodingAssessment.model_validate(version.coding_assessment)

    job_context = JobContext.model_validate(version.job_context)
    bias_profile = BiasReducedProfile.model_validate(version.bias_reduced_profile)
    skill_analysis = SkillAnalysisResult.model_validate(version.skill_analysis)
    score_breakdown = ScoreBreakdown.model_validate(version.scoring_result)
    role_alignment = RoleAlignmentResult.model_validate(version.role_alignment)
    confidence = ConfidenceResult.model_validate(version.confidence_result)
    fd = FinalDecisionResult.model_validate(version.final_decision)
    summary_card, why_this_score, skill_buckets, mismatch = _build_explainability_bundle(
        job_context=job_context,
        bias_profile=bias_profile,
        skill_analysis=skill_analysis,
        score_breakdown=score_breakdown,
        role_alignment=role_alignment,
        confidence=confidence,
        final_decision=fd,
        alternative_role=fd.alternative_role_suggestion,
    )

    return CandidateReportResponse(
        candidate=CandidateSummary(
            candidate_id=candidate.id,
            version_id=version.id,
            name=extracted.name or candidate.name,
            email=extracted.email or candidate.email,
            phone=extracted.phone or candidate.phone,
            location=extracted.location or candidate.location,
            experience=extracted.experience,
            experience_years=extracted.experience_years,
            skills=extracted.skills,
            projects=extracted.projects,
            role=version.job_role,
        ),
        score_breakdown=version.scoring_result,
        confidence=version.confidence_result,
        insights=version.ai_insights,
        questions=questions,
        coding_assessment=coding_assessment,
        final_decision=version.final_decision,
        summary_card=summary_card,
        why_this_score=why_this_score,
        skill_buckets=skill_buckets,
        role_mismatch_warning=mismatch,
    )


from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExperienceLevel(str, Enum):
    FRESHER = "Fresher"
    EXPERIENCED = "Experienced"


class JobContext(BaseModel):
    role: str = Field(..., min_length=2)
    experience_level: ExperienceLevel
    required_skills: list[str] = Field(default_factory=list)


class ProjectInfo(BaseModel):
    title: str
    summary: str
    technologies: list[str] = Field(default_factory=list)


class ExtractedCandidateData(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    experience: str | None = None
    experience_years: float | None = None
    skills: list[str] = Field(default_factory=list)
    projects: list[ProjectInfo] = Field(default_factory=list)
    extraction_confidence: float = 0.0


class ValidationResult(BaseModel):
    normalized_data: ExtractedCandidateData
    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    warning_flag: bool = False
    data_completeness: float = 0.0


class BiasReducedProfile(BaseModel):
    experience: str | None = None
    experience_years: float | None = None
    skills: list[str] = Field(default_factory=list)
    projects: list[ProjectInfo] = Field(default_factory=list)


class SkillAssessment(BaseModel):
    name: str
    category: str
    depth: str
    confidence: float
    evidence: str


class SkillAnalysisResult(BaseModel):
    primary_skills: list[SkillAssessment] = Field(default_factory=list)
    secondary_skills: list[SkillAssessment] = Field(default_factory=list)


class RoleAlignmentResult(BaseModel):
    aligned: bool
    alignment_score: float
    warning: str | None = None
    rationale: str


class ScoreBreakdown(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    skill_score: float = 0.0
    project_score: float = 0.0
    experience_score: float = 0.0
    final_score: float = 0.0
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    score_explanation: list[str] = Field(default_factory=list)


class ConfidenceResult(BaseModel):
    """Overall trust in the analysis (0–100) and human-readable band."""

    score: float = 0.0
    band: str = "Low"
    explanation: str = ""
    confidence_score: float | None = None
    confidence_label: str | None = None

    @model_validator(mode="after")
    def sync_confidence_aliases(self) -> "ConfidenceResult":
        cs = self.confidence_score if self.confidence_score is not None else self.score
        cl = (self.confidence_label or self.band or "Low").strip() or "Low"
        object.__setattr__(self, "confidence_score", float(cs))
        object.__setattr__(self, "confidence_label", cl)
        return self


class AIInsightsResult(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    question: str
    expected_answer: str
    difficulty: str
    why_this_question: str
    project_name: str


class CodingQuestion(BaseModel):
    question_id: str
    prompt: str
    expected_answer: str
    evaluation_rubric: list[str] = Field(default_factory=list)
    difficulty: str
    skill_target: str


class CodingSubmission(BaseModel):
    question_id: str
    answer: str


class CodingAssessment(BaseModel):
    questions: list[CodingQuestion] = Field(default_factory=list)
    coding_score: float = 0.0
    observation: str = ""
    submission_results: list[dict[str, Any]] = Field(default_factory=list)


class FinalDecisionResult(BaseModel):
    final_score: float
    top_strengths: list[str] = Field(default_factory=list)
    top_weaknesses: list[str] = Field(default_factory=list)
    recommendation: str
    confidence: str
    recommendation_confidence: str = ""
    alternative_role_suggestion: str | None = None
    explanation: str
    overridden_by_hr: bool = False
    override_reason: str | None = None

    @model_validator(mode="after")
    def sync_recommendation_confidence(self) -> "FinalDecisionResult":
        if not self.recommendation_confidence:
            object.__setattr__(self, "recommendation_confidence", self.confidence)
        return self


class UploadResumeResponse(BaseModel):
    upload_id: str
    filename: str
    parser_used: str
    preview: ExtractedCandidateData
    warnings: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    upload_id: str
    job_context: JobContext
    coding_submissions: list[CodingSubmission] = Field(default_factory=list)
    override_recommendation: str | None = None
    override_reason: str | None = None


class CandidateSummary(BaseModel):
    candidate_id: str
    version_id: str
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    experience: str | None = None
    experience_years: float | None = None
    skills: list[str] = Field(default_factory=list)
    projects: list[ProjectInfo] = Field(default_factory=list)
    role: str


class AnalysisSummaryCard(BaseModel):
    fit_level: str
    best_role: str
    hiring_risk: str


class SkillBuckets(BaseModel):
    relevant_skills: list[str] = Field(default_factory=list)
    other_skills: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    candidate: CandidateSummary
    score_breakdown: ScoreBreakdown
    confidence: ConfidenceResult
    skill_analysis: SkillAnalysisResult
    role_alignment: RoleAlignmentResult
    insights: AIInsightsResult
    questions: list[InterviewQuestion] = Field(default_factory=list)
    coding_assessment: CodingAssessment
    final_decision: FinalDecisionResult
    warnings: list[str] = Field(default_factory=list)
    summary_card: AnalysisSummaryCard | None = None
    why_this_score: list[str] = Field(default_factory=list)
    skill_buckets: SkillBuckets | None = None
    role_mismatch_warning: str | None = None


class AssistantChatMessage(BaseModel):
    role: str
    content: str


class AssistantChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    view: str = "criteria"
    active_tab: str | None = None
    job_context: JobContext | None = None
    analysis: AnalyzeResponse | None = None
    history: list[AssistantChatMessage] = Field(default_factory=list)


class AssistantChatResponse(BaseModel):
    answer: str
    model: str | None = None
    provider: str = "ollama"
    warning: str | None = None


class QuestionsResponse(BaseModel):
    candidate_id: str
    version_id: str
    questions: list[InterviewQuestion] = Field(default_factory=list)
    coding_questions: list[CodingQuestion] = Field(default_factory=list)


class CopilotRequest(BaseModel):
    """Interview copilot: use saved candidate or pass `candidate_context` from the client."""

    candidate_id: str | None = None
    version_id: str | None = None
    hr_command: str = ""
    command: str | None = None
    current_question_index: int = 0
    candidate_context: dict[str, Any] | None = None

    def resolved_command(self) -> str:
        return (self.command or self.hr_command or "").strip()


class CopilotResponse(BaseModel):
    suggested_question: str
    expected_direction: str
    difficulty: str
    coaching_note: str
    reason: str = ""


class OverrideDecisionRequest(BaseModel):
    candidate_id: str
    version_id: str | None = None
    recommendation: str
    reason: str


class CandidateReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate: CandidateSummary
    score_breakdown: ScoreBreakdown
    confidence: ConfidenceResult
    insights: AIInsightsResult
    questions: list[InterviewQuestion]
    coding_assessment: CodingAssessment
    final_decision: FinalDecisionResult
    summary_card: AnalysisSummaryCard | None = None
    why_this_score: list[str] = Field(default_factory=list)
    skill_buckets: SkillBuckets | None = None
    role_mismatch_warning: str | None = None

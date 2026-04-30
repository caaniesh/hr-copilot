from __future__ import annotations

import json
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from app.models.schemas import (
    AIInsightsResult,
    BiasReducedProfile,
    InterviewQuestion,
    JobContext,
    RoleAlignmentResult,
    ScoreBreakdown,
    SkillAnalysisResult,
    ValidationResult,
)
from app.utils.config import settings
from app.utils.text import summarize_text


class LLMClient(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, payload: dict) -> str:
        """Optional hook for future narrative refinement."""


class MockLLMClient(LLMClient):
    def generate(self, system_prompt: str, payload: dict) -> str:
        return json.dumps({"system_prompt": system_prompt, "payload": payload})


class AIMLClient(LLMClient):
    def generate(self, system_prompt: str, payload: dict) -> str:
        if not settings.aiml_api_url or not settings.aiml_api_key:
            raise RuntimeError("AIML client is configured without API URL or API key.")

        request_body = json.dumps(
            {
                "system_prompt": system_prompt,
                "input": payload,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            settings.aiml_api_url,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.aiml_api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.read().decode("utf-8")
        except urllib.error.URLError as exc:  # pragma: no cover - network path
            raise RuntimeError(f"AIML request failed: {exc}") from exc


class AIInsightService:
    """Deterministic HR-facing narratives backed only by extracted evidence."""

    def __init__(self) -> None:
        self.llm_client: LLMClient = AIMLClient() if settings.ai_provider == "aiml" else MockLLMClient()

    def generate_insights(
        self,
        *,
        profile: BiasReducedProfile,
        validation: ValidationResult,
        skill_analysis: SkillAnalysisResult,
        score_breakdown: ScoreBreakdown,
        role_alignment: RoleAlignmentResult,
    ) -> AIInsightsResult:
        strengths: list[str] = []
        for skill in skill_analysis.primary_skills:
            if skill.confidence >= 80:
                strengths.append(f"{skill.name} has project-backed evidence. {skill.evidence}")
        if profile.projects:
            strengths.append(f"{len(profile.projects)} project(s) were extracted, giving concrete interview anchors.")
        if profile.experience_years is not None:
            strengths.append(f"The resume explicitly indicates about {profile.experience_years} year(s) of experience.")

        weaknesses: list[str] = []
        if score_breakdown.missing_skills:
            weaknesses.append(
                f"Missing required skills for this role: {', '.join(score_breakdown.missing_skills[:4])}."
            )
        low_confidence_primary = [skill.name for skill in skill_analysis.primary_skills if skill.confidence < 80]
        if low_confidence_primary:
            weaknesses.append(
                f"These matched skills are listed without project proof: {', '.join(low_confidence_primary[:4])}."
            )
        if len(profile.projects) <= 1:
            weaknesses.append(f"Only {len(profile.projects)} project(s) were extracted, limiting technical depth checks.")
        if profile.experience_years in (None, 0):
            weaknesses.append("Experience duration is unclear from the resume evidence.")
        if score_breakdown.project_score < 100:
            weaknesses.append(
                f"Project evidence score is {score_breakdown.project_score}, which means not every required skill is demonstrated inside project descriptions."
            )
        if skill_analysis.secondary_skills:
            weaknesses.append(
                f"{len(skill_analysis.secondary_skills)} extracted skill(s) are secondary to the target role rather than direct matches."
            )
        primary_needing_depth = [skill.name for skill in skill_analysis.primary_skills if skill.depth != "Advanced"]
        if primary_needing_depth:
            weaknesses.append(
                f"These role-matched skills still need depth validation in the interview: {', '.join(primary_needing_depth[:4])}."
            )
        project_text = " ".join(project.summary for project in profile.projects).casefold()
        if profile.projects and not any(token in project_text for token in ("test", "validation", "monitor", "qa", "integration test")):
            weaknesses.append("Project descriptions do not explicitly mention testing or validation practices.")

        risk_flags: list[str] = []
        if validation.warning_flag:
            risk_flags.append("Extraction confidence is below the review threshold of 70.")
        if role_alignment.warning:
            risk_flags.append(role_alignment.warning)
        if not validation.normalized_data.email or not validation.normalized_data.phone:
            risk_flags.append("One or more contact identifiers are missing or incomplete.")
        if not profile.projects:
            risk_flags.append("No project section was extracted, so project-based questions may be weak.")

        strengths = self._fill_unique(
            strengths,
            fallbacks=[
                f"Matched skills: {', '.join(score_breakdown.matched_skills[:3]) or 'None detected yet'}.",
                f"Role alignment score is {role_alignment.alignment_score}, which indicates usable evidence for the target role.",
                "Use the extracted projects as the primary focus during the live interview.",
            ],
            target_size=3,
        )
        weaknesses = self._fill_unique(
            weaknesses,
            fallbacks=[
                f"Extraction confidence is {validation.normalized_data.extraction_confidence}, so manual checks should still confirm the resume evidence.",
                "Some strengths still need live interview verification before a final decision.",
                "Use the project-based interview to confirm technical ownership and trade-off reasoning.",
            ],
            target_size=3,
        )
        risk_flags = self._fill_unique(
            risk_flags,
            fallbacks=[
                "Use manual review before finalizing the recommendation.",
                "Keep the interview focused on project ownership and role-matched skills.",
            ],
            target_size=2,
        )

        return AIInsightsResult(strengths=strengths[:3], weaknesses=weaknesses[:3], risk_flags=risk_flags[:2])

    def generate_questions(
        self,
        *,
        profile: BiasReducedProfile,
        skill_analysis: SkillAnalysisResult,
        job_context: JobContext,
    ) -> list[InterviewQuestion]:
        if not profile.projects:
            return []

        primary_skills = [skill.name for skill in skill_analysis.primary_skills]
        questions: list[InterviewQuestion] = []
        template_index = 0

        for project in profile.projects:
            focus_skill = project.technologies[0] if project.technologies else (primary_skills[0] if primary_skills else "the stack")
            summary_snippet = summarize_text(project.summary, max_words=14)
            templates = [
                (
                    f"In '{project.title}', how did you use {focus_skill} to deliver {summary_snippet}?",
                    "Easy",
                    f"A strong answer should connect {focus_skill} to a specific part of '{project.title}', explain the implementation approach, and link it to the stated outcome.",
                    f"This project is direct evidence for {focus_skill} and is relevant to the {job_context.role} role.",
                ),
                (
                    f"What trade-off did you handle in '{project.title}' when working with {focus_skill}?",
                    "Medium",
                    f"A strong answer should explain the constraint in '{project.title}', why one design choice was picked over another, and what impact it had.",
                    f"This checks whether the project ownership goes beyond listing the technology {focus_skill}.",
                ),
                (
                    f"If '{project.title}' had to scale or handle failure better, what part would you redesign first and why?",
                    "Hard",
                    "A strong answer should point to a real component from the project, describe the failure or scale risk, and propose a concrete redesign.",
                    f"The project summary '{summary_snippet}' suggests real implementation details that can be stress-tested.",
                ),
            ]
            for question, difficulty, expected_answer, why in templates:
                questions.append(
                    InterviewQuestion(
                        question=question,
                        expected_answer=expected_answer,
                        difficulty=difficulty,
                        why_this_question=why,
                        project_name=project.title,
                    )
                )
                template_index += 1
                if template_index >= 5:
                    return questions[:5]

        while len(questions) < 5:
            project = profile.projects[-1]
            summary_snippet = summarize_text(project.summary, max_words=14)
            questions.append(
                InterviewQuestion(
                    question=f"How did you verify that '{project.title}' was meeting its goals around {summary_snippet}?",
                    expected_answer=(
                        f"A strong answer should describe the validation approach in '{project.title}', the metric or test used, and what the result showed."
                    ),
                    difficulty="Medium",
                    why_this_question="This probes delivery discipline using the project evidence already present in the resume.",
                    project_name=project.title,
                )
            )
        return questions[:5]

    def _fill_unique(self, items: list[str], fallbacks: list[str], target_size: int) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for item in items:
            marker = item.casefold()
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(item)
        for fallback in fallbacks:
            if len(unique) >= target_size:
                break
            if fallback.casefold() in seen:
                continue
            seen.add(fallback.casefold())
            unique.append(fallback)
        return unique

"""HR-facing summaries, skill bucketing, and score explanations."""

from __future__ import annotations

from app.models.schemas import (
    AnalysisSummaryCard,
    BiasReducedProfile,
    JobContext,
    RoleAlignmentResult,
    ScoreBreakdown,
    SkillBuckets,
    SkillAnalysisResult,
)
from app.utils.text import normalize_skill


# Generic tools often listed on resumes but rarely role-defining unless required.
_NOISE_SKILL_TOKENS = frozenset(
    {
        "ms word",
        "microsoft word",
        "word",
        "excel",
        "microsoft excel",
        "powerpoint",
        "microsoft powerpoint",
        "canva",
        "google docs",
        "google sheets",
        "slack",
        "notion",
        "trello",
    }
)


def build_skill_buckets(
    *,
    job_context: JobContext,
    profile: BiasReducedProfile,
    skill_analysis: SkillAnalysisResult,
) -> SkillBuckets:
    required = {normalize_skill(s) for s in job_context.required_skills if s.strip()}
    relevant = [normalize_skill(s.name) for s in skill_analysis.primary_skills]
    secondary_names = [normalize_skill(s.name) for s in skill_analysis.secondary_skills]

    other: list[str] = []
    for name in secondary_names:
        if name in relevant:
            continue
        if _is_noise_skill(name, required):
            continue
        other.append(name)

    for skill in profile.skills:
        n = normalize_skill(skill)
        if n in relevant or n in other:
            continue
        if n in required:
            relevant.append(n)
            continue
        if _is_noise_skill(n, required):
            continue
        other.append(n)

    relevant = _dedupe_order(relevant)
    other = _dedupe_order(other)
    return SkillBuckets(relevant_skills=relevant, other_skills=other)


def _is_noise_skill(normalized: str, required: set[str]) -> bool:
    if normalized in required:
        return False
    return normalized.casefold() in _NOISE_SKILL_TOKENS or any(
        noise in normalized.casefold() for noise in ("microsoft office", "office 365")
    )


def _dedupe_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def build_why_this_score(
    *,
    job_context: JobContext,
    profile: BiasReducedProfile,
    score_breakdown: ScoreBreakdown,
    role_alignment: RoleAlignmentResult,
) -> list[str]:
    bullets: list[str] = []
    required = [normalize_skill(s) for s in job_context.required_skills if s.strip()]
    matched = score_breakdown.matched_skills
    missing = score_breakdown.missing_skills

    if required:
        matched_display = ", ".join(matched) if matched else "none"
        missing_display = ", ".join(missing) if missing else "none"
        bullets.append(
            f"Required skills for this role: {len(matched)}/{len(required)} matched "
            f"(matched: {matched_display}; gaps: {missing_display})."
        )
    else:
        bullets.append("No required skills were set for this role, so skill match is not constraining the score.")

    project_focus = _infer_project_track(profile)
    role_track = _infer_role_track(job_context.role)
    if project_focus and role_track and project_focus != role_track:
        bullets.append(
            f"Project work reads more {project_focus}-oriented than the stated role ({role_track}), "
            "which lowers project-to-role alignment."
        )
    elif score_breakdown.project_score < 60:
        bullets.append(
            "Project descriptions do not strongly demonstrate the required stack, so project evidence contributes less."
        )

    if not role_alignment.aligned and role_alignment.warning:
        bullets.append(role_alignment.warning)

    if score_breakdown.experience_score < 40 and job_context.experience_level.value == "Experienced":
        bullets.append("Limited tenure or unclear experience narrative for an experienced-level role.")

    if len(bullets) < 2:
        bullets.append(
            f"Weighted score blends skills ({score_breakdown.skill_score}), projects ({score_breakdown.project_score}), "
            f"and experience ({score_breakdown.experience_score}) using the configured role weights."
        )

    return bullets[:6]


def build_summary_card(
    *,
    final_score: float,
    role_alignment: RoleAlignmentResult,
    recommendation: str,
    confidence_band: str,
    best_role_hint: str | None,
) -> AnalysisSummaryCard:
    if final_score >= 75 and role_alignment.aligned:
        fit = "High"
    elif final_score >= 50:
        fit = "Medium"
    else:
        fit = "Low"

    best_role = best_role_hint or "See role alignment"
    if role_alignment.aligned and final_score >= 60:
        best_role = "Current opening"

    if recommendation == "Reject" or (final_score < 45 and not role_alignment.aligned):
        risk = "High"
    elif recommendation == "Hold" or confidence_band == "Low" or not role_alignment.aligned:
        risk = "Medium"
    else:
        risk = "Low"

    return AnalysisSummaryCard(fit_level=fit, best_role=best_role, hiring_risk=risk)


def infer_alternative_role(
    *,
    job_context: JobContext,
    profile: BiasReducedProfile,
    role_alignment: RoleAlignmentResult,
    score_breakdown: ScoreBreakdown,
) -> str | None:
    track = _infer_project_track(profile)
    role_track = _infer_role_track(job_context.role)
    if track and role_track and track != role_track and not role_alignment.aligned:
        labels = {
            "ml": "ML / data science track",
            "backend": "Backend / API engineering",
            "frontend": "Frontend / UI engineering",
            "mobile": "Mobile development",
            "devops": "DevOps / platform engineering",
            "general": None,
        }
        label = labels.get(track or "")
        if label:
            return label
    if score_breakdown.skill_score < 50 and track:
        return labels.get(track, f"{track.title()} oriented roles")
    return None


def role_mismatch_warning(
    *,
    job_context: JobContext,
    profile: BiasReducedProfile,
    role_alignment: RoleAlignmentResult,
    alternative: str | None,
) -> str | None:
    if role_alignment.aligned and role_alignment.alignment_score >= 55:
        return None
    project_track = _infer_project_track(profile)
    role_track = _infer_role_track(job_context.role)
    if project_track and role_track and project_track != role_track:
        suffix = f" A closer fit may be: {alternative}." if alternative else ""
        body = (
            f"Candidate profile leans more toward {project_track.replace('_', ' ').title()} work than "
            f"the listed {job_context.role.strip()} focus.{suffix}"
        ).replace("  ", " ").strip()
        return f"⚠️ {body}"
    if role_alignment.warning:
        return role_alignment.warning
    return None


def _infer_project_track(profile: BiasReducedProfile) -> str | None:
    blob = " ".join(
        [p.title + " " + p.summary + " " + " ".join(p.technologies) for p in profile.projects]
        + list(profile.skills)
    ).casefold()
    if any(k in blob for k in ("tensorflow", "pytorch", "opencv", "cnn", "deep learning", "neural", "scikit")):
        return "ml"
    if any(k in blob for k in ("react", "vue", "angular", "css", "webpack", "frontend")):
        return "frontend"
    if any(k in blob for k in ("kubernetes", "terraform", "jenkins", "ci/cd", "docker swarm", "ansible")):
        return "devops"
    if any(k in blob for k in ("android", "ios", "swift", "kotlin", "flutter")):
        return "mobile"
    if any(k in blob for k in ("fastapi", "django", "spring", "microservice", "rest api", "graphql")):
        return "backend"
    return None


def _infer_role_track(role: str) -> str | None:
    r = role.casefold()
    if any(k in r for k in ("machine learning", "ml engineer", "data scientist", "computer vision", "nlp")):
        return "ml"
    if "front" in r or "ui" in r or "react" in r:
        return "frontend"
    if "mobile" in r or "ios" in r or "android" in r:
        return "mobile"
    if any(k in r for k in ("devops", "sre", "platform", "cloud engineer")):
        return "devops"
    if any(k in r for k in ("backend", "api", "server", "java developer", "python developer")):
        return "backend"
    return "general"


def questions_from_context(candidate_context: dict) -> list[dict]:
    """Normalize client-provided question payloads for copilot."""
    raw = candidate_context.get("interview_questions") or candidate_context.get("questions") or []
    if not isinstance(raw, list):
        return []
    normalized: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        q = item.get("question") or item.get("text")
        if not q:
            continue
        normalized.append(
            {
                "question": str(q),
                "expected_answer": str(item.get("expected_answer") or item.get("expected_direction") or ""),
                "difficulty": str(item.get("difficulty") or "Medium"),
                "why_this_question": str(item.get("why_this_question") or item.get("why") or ""),
                "project_name": str(item.get("project_name") or item.get("project") or "Project"),
            }
        )
    return normalized

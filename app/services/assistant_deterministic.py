"""HR assistant replies without Ollama — uses only structured analysis + job context."""

from __future__ import annotations

from app.models.schemas import AnalyzeResponse, AssistantChatMessage, AssistantChatResponse, JobContext


def _includes(text: str, needles: list[str]) -> bool:
    t = text.casefold()
    return any(n.casefold() in t for n in needles)


def deterministic_reply(
    *,
    question: str,
    view: str,
    active_tab: str | None,
    job_context: JobContext | None,
    analysis: AnalyzeResponse | None,
    history: list[AssistantChatMessage],
) -> AssistantChatResponse:
    _ = history  # reserved for richer multi-turn replies later
    q = question.strip()
    normalized = q.casefold()

    # Greetings
    if normalized in {"hi", "hello", "hey"} or _includes(
        normalized, ["good morning", "good evening", "good afternoon"]
    ):
        return AssistantChatResponse(
            answer=_welcome(view, job_context, analysis),
            model="context-assistant",
            provider="context",
            warning=None,
        )

    if _includes(normalized, ["what can you do", "help", "assist", "agent"]):
        return AssistantChatResponse(
            answer=_capabilities(analysis),
            model="context-assistant",
            provider="context",
        )

    if _includes(normalized, ["this screen", "this page", "where am i", "current screen"]):
        return AssistantChatResponse(
            answer=_current_screen(view, job_context),
            model="context-assistant",
            provider="context",
        )

    if _includes(normalized, ["next step", "what should i do next", "what now", "how do i continue"]):
        return AssistantChatResponse(answer=_next_step(view, analysis), model="context-assistant", provider="context")

    if _includes(normalized, ["job role", "required skills", "experience level", "hiring criteria", "criteria"]):
        return AssistantChatResponse(answer=_role_help(job_context), model="context-assistant", provider="context")

    if _includes(normalized, ["upload", "resume", "file type", "pdf", "docx", "parser"]):
        return AssistantChatResponse(answer=_upload_help(view), model="context-assistant", provider="context")

    if not analysis and _includes(
        normalized,
        ["score", "candidate", "skill", "strength", "weakness", "project", "interview", "coding"],
    ):
        return AssistantChatResponse(
            answer="I don't have candidate results yet. Complete the hiring criteria and upload a resume first.",
            model="context-assistant",
            provider="context",
        )

    if analysis:
        if _includes(normalized, ["skill", "matched", "missing", "primary", "secondary"]):
            return AssistantChatResponse(answer=_skills_detail(analysis), model="context-assistant", provider="context")
        if _includes(normalized, ["strength", "weakness", "risk", "concern"]):
            return AssistantChatResponse(answer=_insights_detail(analysis, normalized), model="context-assistant", provider="context")
        if "project" in normalized:
            return AssistantChatResponse(answer=_projects_detail(analysis), model="context-assistant", provider="context")
        if _includes(normalized, ["interview", "question", "ask next", "probe"]):
            return AssistantChatResponse(answer=_interview_help(analysis, normalized), model="context-assistant", provider="context")
        if _includes(normalized, ["coding", "code test", "programming"]):
            return AssistantChatResponse(answer=_coding_help(analysis), model="context-assistant", provider="context")
        if _includes(normalized, ["score", "recommendation", "confidence", "hold", "hire", "reject", "why"]):
            return AssistantChatResponse(answer=_score_detail(analysis, normalized), model="context-assistant", provider="context")
        if _includes(normalized, ["summarize", "summary"]):
            return AssistantChatResponse(answer=_summary(analysis, job_context), model="context-assistant", provider="context")

    return AssistantChatResponse(
        answer=_fallback(view, analysis),
        model="context-assistant",
        provider="context",
    )


def _welcome(view: str, job_context: JobContext | None, analysis: AnalyzeResponse | None) -> str:
    base = "Hi, I'm your AI Assistant. "
    base += _current_screen(view, job_context)
    base += " Ask about the score, skills, strengths, projects, interview questions, coding test, or next steps."
    return base


def _capabilities(analysis: AnalyzeResponse | None) -> str:
    parts = [
        "I explain the current screen and guide your next action.",
        "I cover hiring criteria, upload flow, scores, recommendations, skills, risks, projects, interview prompts, and coding tests.",
    ]
    if analysis:
        parts.append("I have this candidate's analysis loaded.")
    return " ".join(parts)


def _current_screen(view: str, job_context: JobContext | None) -> str:
    if view == "criteria":
        role = job_context.role if job_context else ""
        skills = ", ".join(job_context.required_skills) if job_context and job_context.required_skills else ""
        extra = ""
        if role:
            extra += f" Current role: {role}."
        if skills:
            extra += f" Required skills: {skills}."
        return f"You are on the hiring criteria screen. Enter role, experience level, and required skills before uploading a resume.{extra}"

    if view == "upload":
        return "You are on the resume upload screen. Upload a PDF, DOCX, or TXT file, then click Upload and Analyze."

    if view == "interview":
        return "You are on the interview copilot screen: suggestions, strengths and weaknesses, coding prompts, and prepared questions."

    return "You are on the candidate analysis screen: profile, score, recommendation, and tabs for insights, skills, questions, and projects."


def _next_step(view: str, analysis: AnalyzeResponse | None) -> str:
    if view == "criteria":
        return "Enter the target role, experience level, and required skills, then continue to resume upload."
    if view == "upload":
        return "Upload the resume and run analysis. Then review score, skills, and interview questions."
    if view == "interview":
        return "Use prepared questions or the copilot commands; probe missing skills and risks from the analysis."
    if not analysis:
        return "Complete a resume analysis first so I can answer candidate-specific questions."
    return "Review the recommendation and matched vs missing skills, then start the interview to validate depth."


def _role_help(job_context: JobContext | None) -> str:
    if not job_context:
        return "Set the job role, experience level (Fresher or Experienced), and comma-separated required skills."
    skills = ", ".join(job_context.required_skills) if job_context.required_skills else "none yet"
    return (
        f"Current setup: role={job_context.role}, experience={job_context.experience_level.value}, "
        f"required skills={skills}. This drives matching, questions, and the recommendation."
    )


def _upload_help(view: str) -> str:
    if view == "upload":
        return "Supported formats: PDF, DOC, DOCX, TXT. After upload, the system extracts data, scores fit, and builds interview outputs."
    return "Upload accepts PDF and DOCX (and DOC/TXT). The parser extracts structured fields for scoring and interviews."


def _skills_detail(a: AnalyzeResponse) -> str:
    sb = a.score_breakdown
    prim = [s.name for s in (a.skill_analysis.primary_skills or [])]
    sec = [s.name for s in (a.skill_analysis.secondary_skills or [])]
    parts = [
        f"Matched required skills: {', '.join(sb.matched_skills) or 'none'}.",
        f"Missing required skills: {', '.join(sb.missing_skills) or 'none'}.",
        f"Primary (role-aligned) skills: {', '.join(prim) or 'none'}.",
        f"Other skills extracted: {', '.join(sec[:12])}{'…' if len(sec) > 12 else ''}.",
    ]
    buckets = getattr(a, "skill_buckets", None)
    if buckets:
        parts.append(f"Relevant bucket: {', '.join(buckets.relevant_skills[:15])}.")
        parts.append(f"Other bucket: {', '.join(buckets.other_skills[:15])}.")
    return " ".join(parts)


def _insights_detail(a: AnalyzeResponse, normalized: str) -> str:
    ins = a.insights
    risk = list(ins.risk_flags or []) + list(a.warnings or [])
    if "strength" in normalized:
        return "Strengths: " + ("; ".join(ins.strengths) if ins.strengths else "None listed.")
    if "weakness" in normalized:
        return "Weaknesses: " + ("; ".join(ins.weaknesses) if ins.weaknesses else "None listed.")
    return "Risks and notes: " + ("; ".join(risk) if risk else "No extra flags.")


def _projects_detail(a: AnalyzeResponse) -> str:
    projects = a.candidate.projects or []
    if not projects:
        return "No projects were extracted from the resume. Add a Projects section with titles and descriptions."
    lines = []
    for i, p in enumerate(projects, start=1):
        tech = ", ".join(p.technologies[:8]) if p.technologies else "no tech listed"
        snippet = (p.summary[:180] + "…") if len(p.summary) > 180 else p.summary
        lines.append(f"{i}. {p.title} — {snippet} (technologies: {tech})")
    return "Projects extracted (" + str(len(projects)) + "): " + " | ".join(lines)


def _interview_help(a: AnalyzeResponse, normalized: str) -> str:
    qs = a.questions or []
    if not qs:
        return "No interview questions were generated — usually because no project evidence was extracted."
    if _includes(normalized, ["next", "ask next"]):
        q0 = qs[0]
        return f"Example next question: {q0.question}"
    preview = "; ".join(f"Q{i+1}: {x.question[:120]}…" if len(x.question) > 120 else f"Q{i+1}: {x.question}" for i, x in enumerate(qs[:4]))
    return f"Prepared questions ({len(qs)}): {preview}"


def _coding_help(a: AnalyzeResponse) -> str:
    cq = a.coding_assessment.questions or []
    if not cq:
        return "No coding prompts were generated for this profile."
    return "Coding focus: " + " | ".join(f"{c.skill_target}: {c.prompt[:120]}" for c in cq[:3])


def _score_detail(a: AnalyzeResponse, normalized: str) -> str:
    sb = a.score_breakdown
    fd = a.final_decision
    conf = a.confidence
    if "confidence" in normalized:
        pct = conf.confidence_score if conf.confidence_score is not None else conf.score
        label = conf.confidence_label or conf.band
        return f"Confidence is {label} ({pct:.0f}/100). {conf.explanation}"
    weights = sb.weights or {}
    expl = " ".join(sb.score_explanation or [])
    why = " ".join(getattr(a, "why_this_score", None) or [])
    parts = [
        f"Final score: {sb.final_score}/100. Recommendation: {fd.recommendation} ({fd.recommendation_confidence or fd.confidence}).",
        f"Weights: skills {weights.get('skills', 0)}%, projects {weights.get('projects', 0)}%, experience {weights.get('experience', 0)}%.",
        fd.explanation,
    ]
    if why:
        parts.append("Why this score: " + why[:400])
    elif expl:
        parts.append(expl)
    if fd.alternative_role_suggestion:
        parts.append(f"Possible alternate track: {fd.alternative_role_suggestion}.")
    return " ".join(parts)


def _summary(a: AnalyzeResponse, job_context: JobContext | None) -> str:
    c = a.candidate
    sb = a.score_breakdown
    fd = a.final_decision
    role = job_context.role if job_context else (c.role or "the role")
    matched = ", ".join(sb.matched_skills) or "none"
    missing = ", ".join(sb.missing_skills) or "none"
    return (
        f"{c.name or 'Candidate'} — {role}: score {round(sb.final_score)}/100, "
        f"{fd.recommendation}. Matched: {matched}. Missing: {missing}."
    )


def _fallback(view: str, analysis: AnalyzeResponse | None) -> str:
    if not analysis:
        return _current_screen(view, None) + " Ask about criteria, upload, or scoring."
    return (
        "Ask about this candidate's score, recommendation, matched or missing skills, strengths, weaknesses, "
        "projects, interview questions, or coding test. I answer from the loaded analysis only."
    )

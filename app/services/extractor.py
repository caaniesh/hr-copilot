from __future__ import annotations

import re

from app.models.schemas import ExtractedCandidateData, ProjectInfo
from app.utils.text import (
    EMAIL_PATTERN,
    PHONE_PATTERN,
    deduplicate_preserve_order,
    extract_section,
    extract_years_of_experience,
    match_known_skills,
    normalize_whitespace,
    skill_in_text,
    split_skill_tokens,
    summarize_text,
)

PROJECT_SECTION_HEADERS = [
    "projects",
    "project experience",
    "key projects",
    "academic projects",
    "personal projects",
    "notable projects",
    "selected projects",
]


class ResumeExtractionService:
    """Extracts structured candidate data without inventing missing values."""

    def extract(self, raw_text: str) -> ExtractedCandidateData:
        normalized = normalize_whitespace(raw_text)
        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        email = self._extract_email(normalized)
        phone = self._extract_phone(normalized)
        name = self._extract_name(lines, email, phone)
        location = self._extract_location(lines)
        experience_text = self._extract_experience_summary(normalized)
        experience_years = extract_years_of_experience(normalized)
        skills = self._extract_skills(normalized)
        projects = self._extract_projects(normalized, skills)
        extraction_confidence = self._calculate_confidence(
            name=name,
            email=email,
            phone=phone,
            location=location,
            experience_text=experience_text,
            skills=skills,
            projects=projects,
        )

        return ExtractedCandidateData(
            name=name,
            email=email,
            phone=phone,
            location=location,
            experience=experience_text,
            experience_years=experience_years,
            skills=skills,
            projects=projects,
            extraction_confidence=extraction_confidence,
        )

    def _extract_email(self, text: str) -> str | None:
        match = EMAIL_PATTERN.search(text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> str | None:
        match = PHONE_PATTERN.search(text)
        return match.group(0).strip() if match else None

    def _extract_name(self, lines: list[str], email: str | None, phone: str | None) -> str | None:
        blocked_tokens = {
            "resume",
            "curriculum vitae",
            "professional summary",
            "skills",
            "experience",
            "projects",
            "education",
        }
        for line in lines[:8]:
            lowered = line.casefold()
            if email and email.casefold() in lowered:
                continue
            if phone and phone.casefold() in lowered:
                continue
            if any(token in lowered for token in blocked_tokens):
                continue
            cleaned = re.sub(r"[^A-Za-z .'-]", "", line).strip()
            words = [word for word in cleaned.split() if word]
            if 2 <= len(words) <= 4 and all(word[0].isupper() or word.isupper() for word in words):
                return cleaned
            if lowered.startswith("name:"):
                return cleaned.split(":", 1)[-1].strip() or None
        return None

    def _extract_location(self, lines: list[str]) -> str | None:
        for line in lines[:10]:
            lowered = line.casefold()
            if lowered.startswith("location:"):
                return line.split(":", 1)[-1].strip() or None
        for line in lines[:10]:
            if "@" in line or re.search(r"\d{5,}", line):
                continue
            if 1 <= line.count(",") <= 2 and len(line.split()) <= 8:
                return line.strip()
        return None

    def _extract_experience_summary(self, text: str) -> str | None:
        section = extract_section(
            text,
            ["experience", "work experience", "professional experience", "internship"],
        )
        if section:
            return summarize_text(section, max_words=40)
        match = re.search(r".{0,20}\d+(?:\.\d+)?\s*\+?\s*(?:years|yrs).{0,120}", text, re.IGNORECASE)
        if match:
            return normalize_whitespace(match.group(0))
        return None

    def _extract_skills(self, text: str) -> list[str]:
        section = extract_section(text, ["skills", "technical skills", "core skills"])
        section_skills = split_skill_tokens(section) if section else []
        text_matches = match_known_skills(text)
        return deduplicate_preserve_order(section_skills + text_matches)

    def _extract_projects(self, text: str, skills: list[str]) -> list[ProjectInfo]:
        section = extract_section(text, PROJECT_SECTION_HEADERS)
        projects: list[ProjectInfo] = []
        raw_entries: list[str] = []

        if section:
            raw_entries = self._split_project_entries(section)
        else:
            fallback_lines = [
                line.strip()
                for line in text.splitlines()
                if "project" in line.casefold() and len(line.split()) > 5
            ]
            raw_entries = fallback_lines[:15]

        max_projects = 25
        for index, entry in enumerate(raw_entries[:max_projects], start=1):
            lines = [line.strip(" -*") for line in entry.splitlines() if line.strip()]
            content = normalize_whitespace(" ".join(lines))
            if not content:
                continue
            title, summary = self._split_project_title_summary(lines, content, index)
            technologies = [
                skill
                for skill in skills
                if skill_in_text(skill, content) or skill_in_text(skill, title)
            ]
            projects.append(
                ProjectInfo(
                    title=title,
                    summary=summary,
                    technologies=deduplicate_preserve_order(technologies),
                )
            )
        return projects

    def _split_project_entries(self, section: str) -> list[str]:
        """Split the projects section into separate items (paragraphs, bullets, numbered lists, titles)."""
        section = normalize_whitespace(section)
        if not section:
            return []

        # 1) Paragraph breaks (blank lines between projects)
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", section) if p.strip()]
        if len(paragraphs) > 1:
            merged: list[str] = []
            for p in paragraphs:
                merged.extend(self._split_bullet_only_block(p))
            if len(merged) > 1:
                return merged

        # 2) Line-leading bullets or numbered items (same paragraph)
        bullet_split = self._split_by_line_bullets(section)
        if len(bullet_split) > 1:
            return bullet_split

        # 3) Numbered lines "1." "2)" at column 0
        numbered = self._split_by_numbered_lines(section)
        if len(numbered) > 1:
            return numbered

        # 4) Dense CV blocks: isolated title lines before body text
        titled = self._split_by_title_lines(section)
        if len(titled) > 1:
            return titled

        # 5) Legacy fallback: regex split (weak on single blobs)
        legacy = [
            entry.strip(" -*\n")
            for entry in re.split(r"\n\s*\n|^\s*[-*]\s+|^\s*\d+\.\s+", section, flags=re.MULTILINE)
            if entry.strip()
        ]
        return legacy if legacy else [section]

    def _split_bullet_only_block(self, paragraph: str) -> list[str]:
        bs = self._split_by_line_bullets(paragraph)
        return bs if len(bs) > 1 else [paragraph]

    def _split_by_line_bullets(self, section: str) -> list[str]:
        lines = section.splitlines()
        bullet_re = re.compile(r"^\s*(?:[\u2022\-*•◦▪]|\d+[\.)])\s+")
        chunks: list[str] = []
        buf: list[str] = []

        for raw in lines:
            if bullet_re.match(raw):
                if buf:
                    chunks.append(normalize_whitespace("\n".join(buf)))
                stripped = bullet_re.sub("", raw.strip(), count=1).strip()
                buf = [stripped] if stripped else []
            else:
                if raw.strip():
                    buf.append(raw.strip())

        if buf:
            chunks.append(normalize_whitespace("\n".join(buf)))

        return chunks if len(chunks) > 1 else [section]

    def _split_by_numbered_lines(self, section: str) -> list[str]:
        """Split on lines like '1. Title' or '2) Title' at start of line."""
        line_starts_item = re.compile(r"^\s*\d+[\.)]\s+\S")
        lines = section.splitlines()
        chunks: list[str] = []
        buf: list[str] = []

        for raw in lines:
            if line_starts_item.match(raw) and buf:
                chunks.append(normalize_whitespace("\n".join(buf)))
                buf = [raw.strip()]
            elif raw.strip():
                buf.append(raw.strip())

        if buf:
            chunks.append(normalize_whitespace("\n".join(buf)))

        return chunks if len(chunks) > 1 else [section]

    def _split_by_title_lines(self, section: str) -> list[str]:
        """Split when a short standalone line looks like a project title before description."""
        lines = [ln.strip() for ln in section.splitlines() if ln.strip()]
        if len(lines) < 4:
            return [section]

        title_pattern = re.compile(r"^[A-Z][^.!?\n]{4,100}$")
        blocks: list[list[str]] = []
        buf: list[str] = []

        for line in lines:
            if buf and title_pattern.match(line) and len(normalize_whitespace(" ".join(buf))) > 50:
                blocks.append(buf)
                buf = [line]
            else:
                buf.append(line)

        if buf:
            blocks.append(buf)

        entries = [normalize_whitespace("\n".join(b)) for b in blocks]
        cleaned = [e for e in entries if len(e) > 15]
        return cleaned if len(cleaned) > 1 else [section]

    def _split_project_title_summary(
        self,
        lines: list[str],
        content: str,
        index: int,
    ) -> tuple[str, str]:
        first_line = lines[0] if lines else content
        if ":" in first_line:
            title, rest = first_line.split(":", 1)
            summary = normalize_whitespace(" ".join([rest.strip(), *lines[1:]]))
            return title.strip(), summary or content

        if len(first_line.split()) <= 8 and not first_line.endswith(".") and len(lines) > 1:
            return first_line, normalize_whitespace(" ".join(lines[1:]))

        return f"Project {index}", content

    def _calculate_confidence(
        self,
        *,
        name: str | None,
        email: str | None,
        phone: str | None,
        location: str | None,
        experience_text: str | None,
        skills: list[str],
        projects: list[ProjectInfo],
    ) -> float:
        score = 15.0
        score += 10.0 if name else 0.0
        score += 15.0 if email else 0.0
        score += 10.0 if phone else 0.0
        score += 10.0 if location else 0.0
        score += 15.0 if experience_text else 0.0
        score += min(15.0, len(skills) * 3.0)
        score += min(15.0, len(projects) * 7.5)
        return round(min(score, 100.0), 2)

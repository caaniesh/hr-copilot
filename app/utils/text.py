from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable


COMMON_SECTION_HEADERS = [
    "summary",
    "professional summary",
    "profile",
    "experience",
    "work experience",
    "professional experience",
    "internship",
    "skills",
    "technical skills",
    "core skills",
    "projects",
    "project experience",
    "education",
    "certifications",
    "achievements",
]

COMMON_TECH_SKILLS = [
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "SQL",
    "FastAPI",
    "Django",
    "Flask",
    "React",
    "Node.js",
    "Express",
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Git",
    "HTML",
    "CSS",
    "PostgreSQL",
    "MySQL",
    "SQLite",
    "MongoDB",
    "Redis",
    "Pandas",
    "NumPy",
    "TensorFlow",
    "PyTorch",
    "Scikit-learn",
    "REST API",
    "Microservices",
    "Linux",
    "CI/CD",
    "Spring Boot",
    "C",
    "C++",
    "C#",
    ".NET",
    "Power BI",
    "Tableau",
    "Excel",
    "ETL",
    "Airflow",
]

SKILL_ALIASES = {
    "node": "Node.js",
    "nodejs": "Node.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "js": "JavaScript",
    "ts": "TypeScript",
    "rest": "REST API",
    "rest api": "REST API",
    "ci/cd": "CI/CD",
    "ml": "Scikit-learn",
}

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(
    r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4,})"
)
EXPERIENCE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)", re.IGNORECASE)
SPECIAL_SKILL_PATTERNS = {
    "Node.js": r"\bnode(?:\.js|js)?\b",
    "REST API": r"\brest(?:ful)?\s+api\b|\brest\s+endpoints?\b",
    "CI/CD": r"\bci\s*/\s*cd\b",
    ".NET": r"(?<![\w+#])\.net(?![\w+#])",
    "C++": r"(?<![\w+#])c\+\+(?![\w+#])",
    "C#": r"(?<![\w+#])c#(?![\w+#])",
    "C": r"(?<![\w+#])c(?![\w+#])",
}


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def deduplicate_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = item.strip()
        if not cleaned:
            continue
        marker = cleaned.casefold()
        if marker in seen:
            continue
        seen.add(marker)
        result.append(cleaned)
    return result


def safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name)
    return cleaned or "resume"


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if not digits:
        return None
    if len(digits) == 10:
        return f"+1{digits}"
    if phone.strip().startswith("+"):
        return f"+{digits}"
    return digits


def normalize_skill(skill: str) -> str:
    cleaned = skill.strip().strip(":-").replace("  ", " ")
    if not cleaned:
        return ""
    alias = SKILL_ALIASES.get(cleaned.casefold())
    if alias:
        return alias
    for candidate in COMMON_TECH_SKILLS:
        if cleaned.casefold() == candidate.casefold():
            return candidate
    return cleaned.title() if cleaned.islower() else cleaned


def split_skill_tokens(text: str) -> list[str]:
    tokens = re.split(r"[,/|;\n]+", text)
    normalized: list[str] = []
    for token in tokens:
        token = re.sub(r"^[\-\u2022*]\s*", "", token.strip())
        if ":" in token:
            _, token = token.split(":", 1)
        for part in re.split(r"\s{2,}", token):
            skill = normalize_skill(part)
            if skill:
                normalized.append(skill)
    return deduplicate_preserve_order(normalized)


def match_known_skills(text: str) -> list[str]:
    matches: list[str] = []
    for skill in COMMON_TECH_SKILLS:
        if skill_in_text(skill, text):
            matches.append(skill)
    return deduplicate_preserve_order(matches)


def skill_in_text(skill: str, text: str) -> bool:
    pattern = SPECIAL_SKILL_PATTERNS.get(skill)
    if pattern:
        return re.search(pattern, text, re.IGNORECASE) is not None
    escaped = re.escape(skill)
    return re.search(rf"(?<![\w+#]){escaped}(?![\w+#])", text, re.IGNORECASE) is not None


def extract_years_of_experience(text: str) -> float | None:
    matches = [float(match.group(1)) for match in EXPERIENCE_PATTERN.finditer(text)]
    if not matches:
        return None
    return max(matches)


def is_header_line(line: str) -> bool:
    cleaned = line.strip().strip(":").casefold()
    return cleaned in {header.casefold() for header in COMMON_SECTION_HEADERS}


def extract_section(text: str, headers: list[str]) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    collecting = False
    collected: list[str] = []
    header_set = {header.casefold() for header in headers}
    for line in lines:
        stripped = line.strip()
        normalized = stripped.strip(":").casefold()
        if normalized in header_set:
            collecting = True
            continue
        if collecting and stripped and is_header_line(stripped):
            break
        if collecting:
            collected.append(line)
    return normalize_whitespace("\n".join(collected))


def summarize_text(text: str, max_words: int = 16) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip() + "..."

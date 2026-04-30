"""Map internal parsing and system messages to HR-friendly review notes."""

from __future__ import annotations

import re


def humanize_parsing_warnings(warnings: list[str]) -> list[str]:
    """Replace technical parser messages with plain-language notes for HR."""
    out: list[str] = []
    for raw in warnings:
        text = raw.strip()
        if not text:
            continue
        lower = text.casefold()
        if "pdfplumber" in lower and "not installed" in lower:
            out.append("Resume parsing used a backup method; accuracy may be slightly affected.")
            continue
        if "pdfplumber failed" in lower:
            out.append("The primary PDF reader had a problem; a backup reader was used.")
            continue
        if "pypdf fallback failed" in lower:
            out.append("A backup PDF reader could not read all pages; please verify the file opens cleanly.")
            continue
        if "ocr fallback failed" in lower:
            out.append("Automatic text recognition could not run; the text may rely on embedded PDF text only.")
            continue
        if "legacy .doc" in lower or ".doc parsing" in lower:
            out.append("Older Word format detected; consider PDF or DOCX for the most reliable read.")
            continue
        if lower.startswith("ocr"):
            out.append("Scanned pages were processed with extra care; spot-check names and dates.")
            continue
        out.append(_strip_technical_jargon(text))
    return _dedupe_preserve_order(out)


def humanize_validation_warnings(warnings: list[str]) -> list[str]:
    """Soften validation wording where it still sounds internal."""
    out: list[str] = []
    for raw in warnings:
        text = raw.strip()
        if not text:
            continue
        lower = text.casefold()
        if "extraction confidence is below 70" in lower:
            out.append("Some resume details were unclear; a quick manual check of the profile is recommended.")
            continue
        if "completeness is low" in lower:
            out.append("The profile looks incomplete; the resume layout or scan quality may be affecting extraction.")
            continue
        out.append(text)
    return _dedupe_preserve_order(out)


def _strip_technical_jargon(text: str) -> str:
    """Remove exception class names and stack-like fragments."""
    cleaned = re.sub(r"\b[A-Za-z_]+Error:\s*", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or text


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique

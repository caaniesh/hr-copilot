from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from app.utils.text import normalize_whitespace


class ResumeParserService:
    """Extracts text from supported resume formats with explicit fallbacks."""

    supported_extensions = {".pdf", ".doc", ".docx", ".txt"}

    def parse_file(self, file_path: Path) -> tuple[str, str, list[str]]:
        extension = file_path.suffix.lower()
        if extension not in self.supported_extensions:
            raise ValueError(f"Unsupported file type: {extension}")

        warnings: list[str] = []
        parser_used = ""

        if extension == ".pdf":
            text, parser_used, warnings = self._parse_pdf(file_path)
        elif extension == ".docx":
            text = self._parse_docx(file_path)
            parser_used = "docx-xml"
        elif extension == ".doc":
            text = self._parse_doc(file_path)
            parser_used = "doc-binary-best-effort"
            warnings.append(
                "Legacy .doc parsing is best-effort only. Convert to PDF or DOCX for higher reliability."
            )
        else:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            parser_used = "plain-text"

        text = normalize_whitespace(text)
        if not text:
            raise ValueError("No readable text could be extracted from the resume.")
        return text, parser_used, warnings

    def _parse_pdf(self, file_path: Path) -> tuple[str, str, list[str]]:
        warnings: list[str] = []
        text = ""
        parser_used = ""

        try:
            import pdfplumber  # type: ignore

            pages: list[str] = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    pages.append(page.extract_text() or "")
            text = "\n".join(pages)
            parser_used = "pdfplumber"
        except ImportError:
            warnings.append("pdfplumber is not installed; using the pypdf fallback.")
        except Exception as exc:  # pragma: no cover - defensive path
            warnings.append(f"pdfplumber failed: {exc}")

        if len(text.split()) >= 30:
            return text, parser_used or "pdfplumber", warnings

        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(str(file_path))
            pages = [(page.extract_text() or "") for page in reader.pages]
            pypdf_text = "\n".join(pages)
            if len(pypdf_text.split()) > len(text.split()):
                text = pypdf_text
                parser_used = "pypdf"
        except Exception as exc:  # pragma: no cover - defensive path
            warnings.append(f"pypdf fallback failed: {exc}")

        if len(text.split()) >= 30:
            return text, parser_used or "pypdf", warnings

        ocr_text = self._ocr_pdf(file_path, warnings)
        if len(ocr_text.split()) > len(text.split()):
            text = ocr_text
            parser_used = "pytesseract-ocr"

        return text, parser_used or "unknown-pdf-parser", warnings

    def _ocr_pdf(self, file_path: Path, warnings: list[str]) -> str:
        try:
            import fitz  # type: ignore
            import pytesseract  # type: ignore
            from PIL import Image

            doc = fitz.open(file_path)
            pages: list[str] = []
            for page in doc:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
                pages.append(pytesseract.image_to_string(image))
            return "\n".join(pages)
        except Exception as exc:
            warnings.append(f"OCR fallback failed: {exc}")
            return ""

    def _parse_docx(self, file_path: Path) -> str:
        try:
            with ZipFile(file_path) as archive:
                xml_bytes = archive.read("word/document.xml")
            root = ET.fromstring(xml_bytes)
            text_nodes = [node.text for node in root.iter() if node.text]
            return "\n".join(text_nodes)
        except Exception as exc:
            raise ValueError(f"Could not parse DOCX file: {exc}") from exc

    def _parse_doc(self, file_path: Path) -> str:
        raw = file_path.read_bytes()
        decoded = raw.decode("utf-8", errors="ignore")
        if len(decoded.split()) < 20:
            decoded = raw.decode("latin-1", errors="ignore")
        chunks = re.findall(r"[A-Za-z][A-Za-z0-9\s,./:+#()_-]{20,}", decoded)
        return "\n".join(chunks)


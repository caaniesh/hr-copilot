from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault(
    "INTERVIEW_COPILOT_DB_PATH",
    str(Path(tempfile.gettempdir()) / "interview_copilot" / "smoke_test.db"),
)

from app.main import app


def main() -> None:
    sample_resume = Path("sample_data/sample_resume.txt")
    if not sample_resume.exists():
        raise SystemExit("Sample resume file is missing.")

    with TestClient(app) as client:
        health = client.get("/health")
        print("health", health.status_code, health.json())

        with sample_resume.open("rb") as handle:
            upload_response = client.post(
                "/upload_resume",
                files={"file": ("sample_resume.txt", handle, "text/plain")},
            )
        print("upload", upload_response.status_code)
        upload_payload = upload_response.json()
        print(upload_payload)
        upload_id = upload_payload["upload_id"]

        analyze_response = client.post(
            "/analyze",
            json={
                "upload_id": upload_id,
                "job_context": {
                    "role": "Backend Engineer",
                    "experience_level": "Experienced",
                    "required_skills": ["Python", "FastAPI", "SQL", "Docker", "REST API"],
                },
                "coding_submissions": [],
            },
        )
        print("analyze", analyze_response.status_code)
        analysis_payload = analyze_response.json()
        print(analysis_payload["final_decision"])

        candidate_id = analysis_payload["candidate"]["candidate_id"]
        version_id = analysis_payload["candidate"]["version_id"]

        questions_response = client.get(f"/questions?candidate_id={candidate_id}&version_id={version_id}")
        print("questions", questions_response.status_code)

        copilot_response = client.post(
            "/copilot",
            json={
                "candidate_id": candidate_id,
                "version_id": version_id,
                "hr_command": "next question",
                "current_question_index": 0,
            },
        )
        print("copilot", copilot_response.status_code, copilot_response.json())

        override_response = client.post(
            "/decision/override",
            json={
                "candidate_id": candidate_id,
                "version_id": version_id,
                "recommendation": "Hold",
                "reason": "Manual review requested after the first interview round.",
            },
        )
        print("override", override_response.status_code, override_response.json())

        export_response = client.get(f"/export?candidate_id={candidate_id}")
        print("export", export_response.status_code, export_response.headers.get("content-disposition"))


if __name__ == "__main__":
    main()

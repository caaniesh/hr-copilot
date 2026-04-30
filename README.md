# AI Technical Interview Copilot for HR

AI Technical Interview Copilot is a full-stack FastAPI application for non-technical HR teams to upload resumes, analyze candidate-role fit, generate project-based interview questions, guide assisted interviews, and export structured Excel reports.

## What it does

- Uploads PDF, DOC, DOCX, or TXT resumes.
- Extracts structured candidate data with explicit confidence scoring.
- Redacts personal identifiers before skill scoring and role-fit analysis.
- Scores candidates deterministically using different fresher and experienced weightings.
- Generates project-based strengths, weaknesses, risk flags, interview questions, and lightweight coding tests.
- Stores candidate records with duplicate prevention by email or phone and versioned analysis history.
- Exports Excel reports for one candidate or the latest version of all candidates.
- Includes a browser dashboard for HR-friendly workflows.

## Architecture

```text
app/
├── main.py
├── database.py
├── routes/
│   ├── analysis.py
│   ├── decision.py
│   ├── export.py
│   ├── interview.py
│   ├── resume.py
│   └── system.py
├── services/
│   ├── ai_engine.py
│   ├── bias.py
│   ├── coding.py
│   ├── copilot.py
│   ├── export.py
│   ├── extractor.py
│   ├── parser.py
│   ├── scoring.py
│   ├── storage.py
│   └── validation.py
├── models/
│   ├── db.py
│   └── schemas.py
├── static/
│   ├── app.js
│   ├── index.html
│   └── styles.css
└── utils/
    ├── config.py
    └── text.py
```

## Requirements

- Python 3.11+
- Tesseract OCR installed and available on `PATH` for OCR fallback
- Optional but recommended dependencies:
  - `pdfplumber` for primary PDF parsing
  - `pandas` for DataFrame-based export
  - `python-docx` or DOCX conversion tools if you want richer Microsoft Word parsing later

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn app.main:app --reload
```

Open the dashboard:

```text
http://127.0.0.1:8000/
```

## Deploy (Render + static UI)

**Backend (Render):** Connect this repo as a **Web Service**. Use `render.yaml` or set manually:

- **Build:** `pip install -r requirements.txt`
- **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health check path:** `/health`
- Create a **PostgreSQL** database on Render and **link** it so `DATABASE_URL` is set on the web service (the app normalizes `postgres://` to `postgresql://` and uses `psycopg2`).
- Optional env: `AI_PROVIDER=mock`, `ASSISTANT_PROVIDER=mock` if you do not run Ollama on the server.

**Frontend (e.g. Vercel static):** Deploy `app/static/` assets (or the whole repo with output to static). In `index.html`, set the API origin:

```html
<meta name="api-base" content="https://YOUR-SERVICE.onrender.com">
```

Leave `content` empty when the UI is served from the same host as the API. You can also set `window.API_BASE` before loading `app.js`.

## API endpoints

- `POST /upload_resume`
- `POST /analyze`
- `POST /assistant/chat`
- `GET /questions`
- `POST /copilot`
- `GET /export`

Additional operational endpoints:

- `GET /health`
- `GET /candidate/{candidate_id}`
- `POST /decision/override`

## Example workflow

1. Upload a resume:

```bash
curl -X POST "http://127.0.0.1:8000/upload_resume" \
  -F "file=@sample_data/sample_resume.txt"
```

2. Analyze the uploaded resume:

```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -H "Content-Type: application/json" \
  -d @sample_data/sample_analyze_request.json
```

3. Fetch generated questions:

```bash
curl "http://127.0.0.1:8000/questions?candidate_id=<candidate_id>&version_id=<version_id>"
```

4. Export the report:

```bash
curl -OJ "http://127.0.0.1:8000/export?candidate_id=<candidate_id>"
```

## Data and storage

- Default SQLite database file: `%TEMP%/interview_copilot/interview_copilot.db`
- Override the database with `INTERVIEW_COPILOT_DB_PATH` for a custom SQLite file or `DATABASE_URL` for PostgreSQL.
- Resume uploads: `app/data/uploads/`
- Generated reports: `app/data/exports/`

## Ollama assistant setup

The floating `AI Assistant` chat widget now uses a local Ollama model for contextual answers.

1. Install and start Ollama.
2. Pull a local chat model, for example:

```bash
ollama pull llama3.2:3b
```

3. Run the app with the Ollama settings:

```bash
$env:ASSISTANT_PROVIDER='ollama'
$env:OLLAMA_MODEL='llama3.2:3b'
uvicorn app.main:app --reload
```

Optional environment variables:

- `OLLAMA_BASE_URL` defaults to `http://localhost:11434`
- `OLLAMA_MODEL` defaults to `llama3.2:3b`
- `OLLAMA_TIMEOUT_SECONDS` defaults to `60`
- `OLLAMA_KEEP_ALIVE` defaults to `10m`

## Notes on explainability and reliability

- Scoring is deterministic and does not depend on external AI calls.
- AI insight generation is deterministic and grounded only in extracted evidence.
- The LLM provider interface in `app/services/ai_engine.py` supports a future AIML integration, but the default system stays explainable by design.
- Bias removal is enforced by using only experience, skills, and projects in downstream analysis.
- Extraction confidence below `70` is flagged for manual review.

## Validation and smoke test

Run the smoke test:

```bash
python scripts/smoke_test.py
```

This script exercises:

- health check
- resume upload
- candidate analysis
- question retrieval
- copilot assistance
- HR override
- Excel export

## Sample data

- Resume sample: `sample_data/sample_resume.txt`
- Job context sample: `sample_data/sample_job_context.json`
- Analyze request template: `sample_data/sample_analyze_request.json`

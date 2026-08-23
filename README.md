# Clinical Intelligence System

| | |
|---|---|
| **Full Name** | Ashish Jain |
| **Uplevel Email** | ashish.jain25@gmail.com |
| **Problem Statement** | Clinical Intelligence System |
| **Submission Date** | August 24, 2026 |

---

A standalone FastAPI application implementing the **AI-Driven Multi-Role
Clinical Intelligence System**: a 5-agent chained pipeline (Data Extraction → Clinical Analysis → Risk
Detection → Insight Generation → Patient Communication) that processes
diagnostic reports and serves three role-based dashboards — Patient, Doctor,
Radiologist/Lab Technician.


## Features

### 5-agent AI pipeline
Every uploaded report runs through a chained pipeline
(`backend/agents/pipeline.py`), each stage persisted and shown to
doctors as a structured audit trail (`AgentAuditTrail.tsx`) rather than
raw JSON:

1. **Data Extraction** — parses DOCX/PDF/pasted text, regex-extracts lab
   values/entities, flags low-confidence extraction (e.g. a scanned PDF
   with no text layer) for review instead of hallucinating values.
2. **Clinical Analysis** — interprets extracted values against reference
   ranges and the medical knowledge graph, flags clinical inconsistencies.
3. **Risk Detection** — flags critical values, auto-creates alerts and a
   naive next-business-day escalation appointment for CRITICAL findings.
4. **Insight Generation** — produces the clinician-facing insight that a
   doctor validates/modifies/finalizes (designed and built from scratch).
5. **Patient Communication** — produces the plain-language patient summary,
   held back until a doctor approves it (designed and built from scratch).

### Patient dashboard
- Upload a report (file upload or pasted text) with a fixed category
  dropdown (Lab/Radiology/Physician note/Discharge/Other…).
- Report list + detail view with live processing status.
- Compare two reports side by side — only within the same category,
  enforced client- and server-side.
- Plain-language AI summary, hidden until a doctor finalizes/approves it
  (`patient_summaries.clinician_approved`, enforced at the DB layer).
- Doctor review history visible once a summary is released.
- Self-reported allergy and medical history tracking.
- Critical-value alerts feed.
- Appointment booking against a doctor's real free/busy slots (10:00
  AM-1:00 PM / 4:00-7:00 PM grid, 15-minute slots) and self-cancellation.
- "AI Health Assistant" — RAG chat scoped to the patient's own records,
  with persisted chat history.

### Doctor dashboard
- Patients list, plus a radiologists directory for messaging.
- Per-patient report list, detail, and history.
- Full 5-agent audit trail per report; Validate/Modify/Finalize action on
  each AI insight, with reviewer/action/comment recorded and surfaced in a
  Review history section on both doctor and patient views.
- Alerts panel (critical values), acknowledgeable, click-through to the
  triggering patient.
- Appointments panel (upcoming, across all patients).
- In-app messaging with radiologists (recipient picked from a name
  directory, not a raw user ID).
- "AI Clinical Assistant" — RAG chat over clinical data.

### Radiologist / lab technician dashboard
- Upload a new report for any patient (file or pasted text), triggering
  the pipeline in the background.
- Edit report metadata and update report status.
- In-app messaging with doctors.

### Platform / cross-cutting
- **Auth & RBAC**: pbkdf2 password hashing, signed session cookie,
  role-based access enforced per-endpoint and per-row (a patient can only
  ever read their own data).
- **Medical knowledge graph**: NetworkX ontology of lab tests, symptoms,
  and allergen cross-reactivity, used by the Clinical Analysis agent.
- **Vector store / RAG**: ChromaDB embeddings power both chat assistants
  and are scoped per patient/role at query time.
- **Observability**: dependency-injected `ObservabilityPort` — a no-op
  tracer by default (fully offline) or Langfuse v4 tracing when
  `LANGFUSE_*` keys are set.
- **Negative-scenario handling**: every agent's failure modes (low
  confidence, clinical inconsistency, escalation, review-required,
  clinician-oversight gate) are enforced deterministically in code, not
  just trusted from the LLM's own output — see Design decisions below.

## Architecture

See [`app/docs/architecture.pdf`](app/docs/architecture.pdf) for diagrams of
the system components, the 5-agent pipeline, how the three roles share data,
8 request-level sequence diagrams (login, upload → pipeline,
critical-alert escalation, doctor review → patient reveal, appointment
booking/cancellation, AI chat, and doctor↔radiologist messaging), and a
closing deployment section. Sources in
`app/docs/architecture-diagrams/*.mmd`, regenerate from `app/` with
`mmdc -i <file>.mmd -o <file>.png -b white -c docs/architecture-diagrams/mermaid-config.json`
— the config file bumps in-diagram font sizes; the PDF itself is A4
landscape for legibility.

For the AWS deployment specifically — the deployment diagram, why this
shape, first-time setup, CI/CD, and this live deployment's actual details —
see [`app/docs/deployment-architecture.pdf`](app/docs/deployment-architecture.pdf).

```
app/
  backend/
    agents/          5-agent pipeline (schemas.py, one file per agent, pipeline.py orchestrator)
    db/               SQLite schema + repositories (source of truth for all structured data)
    documents/        DOCX/PDF parsing + regex entity extraction
    vectorstore/      ChromaDB wrapper (embeddings/RAG only — never relational data)
    knowledge_graph.py NetworkX medical ontology (lab tests, symptoms, allergen cross-reactivity)
    observability/    NoOp (default, fully offline) / Langfuse v4 tracing adapters
    llm/              Injectable OpenAI client (embeddings + chat)
    auth/             pbkdf2 password hashing + role-based access control
    services/         Upload/report/compare/chat/alert/appointment business logic
    api/              FastAPI routers (SPA shell + per-role JSON APIs)
    main.py           App entrypoint, builds the DI object graph on startup

  frontend/           React + TypeScript SPA (Vite, Tailwind, React Router, TanStack Query) —
                      talks to the backend purely through the /api/* JSON API. `frontend/dist`
                      (the production build) is what `backend/api/routes_pages.py` serves.
                      Three role dashboards (patient/doctor/radiologist) built from shared
                      components: report upload/list/compare/detail, the 5-agent audit trail,
                      doctor review + review-history, RAG chat, in-app messaging (name-dropdown
                      directories, not raw user IDs), and appointment booking/cancellation.
  scripts/            reset_db.py, seed_data.py (seeds from the real ../Datasets/ folder)
  tests/              87 tests: repositories, document/entity parsing, vector store, knowledge
                      graph, observability, mocked-LLM agent/pipeline negative-scenario tests,
                      and an end-to-end API smoke test
```

## Setup

Use a dedicated virtual environment for this project rather than installing
into a shared/global Python — this project pins specific `chromadb`/
`pydantic`/`pydantic-settings` versions that can conflict with other
projects' pinned versions on the same interpreter (this bit us once during
development against a machine that also had `crewai` installed globally).

```bash
cd app

# Windows, with multiple Pythons installed: pin the version explicitly via
# the launcher — plain `python -m venv .venv` silently picked up the wrong
# interpreter here (a Python 3.14 install ahead of 3.13 on PATH), which then
# fails at import time with `ModuleNotFoundError: No module named
# 'pydantic_core._pydantic_core'` because the compiled extension pip
# installs won't match a mismatched interpreter. `py -0p` lists every
# version the launcher knows about; use whichever one you intend.
py -3.13 -m venv .venv
.venv\Scripts\activate

# macOS/Linux:
# python3 -m venv .venv
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Edit .env and set OPENAI_API_KEY (required for the AI pipeline/chat).
# LANGFUSE_* keys are optional — without them the app runs fully offline
# with a no-op tracer; everything except AI-calling endpoints still works.

python scripts/reset_db.py
python scripts/seed_data.py   # seeds 5 patients / 2 doctors / 2 radiologists from ../Datasets/

# Build the React frontend (needs Node.js 20+). Only needs re-running when
# frontend/src changes — backend/api/routes_pages.py serves frontend/dist as
# static files, so it must exist before uvicorn starts.
npm --prefix frontend install
npm --prefix frontend run build

uvicorn backend.main:app --reload
```

Every Python command above (`pip`, `python`, `uvicorn`) must be run with the
venv active — if `uvicorn` fails with `ModuleNotFoundError` for a package
that's clearly in `requirements.txt` (especially `pydantic_core._pydantic_core`),
check `.venv\pyvenv.cfg`'s `home =` line. If it doesn't point at the Python
version you intended, the venv was created against the wrong interpreter
(re-run `python -m venv .venv` on a machine with multiple Pythons on `PATH`
and it can silently happen again) — delete `.venv` and recreate it with an
explicit version pin as above. Also double check with `where uvicorn`
(Windows) / `which uvicorn` (macOS/Linux) that it resolves inside `.venv`.

### Frontend dev mode (hot reload)

For UI work, run the backend and the Vite dev server side by side instead of
rebuilding on every change:

```bash
# terminal 1, from app/, venv active
uvicorn backend.main:app --reload

# terminal 2
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173` — Vite proxies `/api/*` to the backend on
`:8000` (see `frontend/vite.config.ts`), so the session cookie and all API
calls work the same as in production. `:8000` itself still serves whatever
was last built to `frontend/dist`.

Then open `http://127.0.0.1:8000/login` (or `:5173` in dev mode above). Seeded accounts (password
`password123` for all — printed again at the end of `seed_data.py`):

| Role | Email |
|---|---|
| Doctor | sharma@cis.com, verma@cis.com |
| Radiologist | singh@cis.com, iyer@cis.com |
| Patient | aisha.khan@cis.com, ravi.verma@cis.com, meena.patel@cis.com, john.fernandes@cis.com, priya.nair@cis.com |

`priya.nair@cis.com`'s CBC report is deliberately the one real scanned-image
PDF in the dataset (no OCR text layer) — it demonstrates the Data Extraction
agent's "low-confidence extraction flagged for review" negative scenario.

## Golden path to demo

1. Log in as a patient → book an appointment with a doctor (Book appointment
   panel: pick doctor, date, a 15-minute slot within 10:00 AM-1:00 PM or
   4:00-7:00 PM — only slots the backend confirms are free are offered, and
   the appointment can be cancelled again from the same panel's Upcoming
   list).
2. Log in as a radiologist → upload a new report for any patient (file or
   pasted text; Category is a fixed dropdown grouped by Lab/Radiology/
   Physician note/Discharge, plus "Other…" for anything not listed).
3. Log in as that patient → see the report flip from "processing" to
   "processed"; the plain-language summary stays hidden ("pending doctor
   review") until a doctor approves it — this is enforced at the database
   level (`patient_summaries.clinician_approved`), not just trusted from the
   agent's own output.
4. Log in as a doctor → open the patient (via the Patients list, the
   Upcoming appointments panel, or by clicking one of their alerts — all
   three select the same patient), expand the AI audit trail (all 5 agents,
   rendered as structured findings per agent rather than raw JSON),
   Validate/Modify/Finalize the insight. The review (reviewer name, action,
   comments) is then visible in a Review history section on both the
   doctor's and the patient's report detail view.
5. Log back in as the patient → the plain-language summary now appears,
   alongside the doctor's review history.
6. Any critical lab value (e.g. a seeded CRITICAL_LOW/HIGH parameter) creates
   an alert automatically — visible (and clickable, to jump straight to that
   patient) on the doctor dashboard's Alerts panel. No real calendar/EHR
   system is ever contacted; this is simulated in-app by design (see
   Constraints below).
7. Doctor ↔ radiologist messaging (recipient picked from a name dropdown,
   not a raw user ID) and the RAG chatbots ("AI Health Assistant" for
   patients, "AI Clinical Assistant" for doctors) are demonstrable from
   their respective dashboards. Compare Reports only allows comparing two
   reports of the same investigation type (category) — enforced both in the
   UI and as a 400 from the API.

## Design decisions worth knowing

- **Frontend**: FastAPI backend + a React/TypeScript SPA (Vite, Tailwind,
  React Router, TanStack Query) — not Gradio, despite the PDF's "indicative"
  tech stack — three separate role dashboards modeled on the PDF's mockup
  panels. The SPA only talks to the backend via `/api/*` JSON; FastAPI's job
  on the page-serving side is just handing back `frontend/dist/index.html`
  for client-side routing (`backend/api/routes_pages.py`).
- **Persistence**: SQLite is the source of truth for everything relational
  (patients, reports, agent outputs, alerts, messages); ChromaDB holds only
  embeddings. The PDF's tech stack table names only ChromaDB as "Database,"
  which isn't suited to relational data at this scale.
- **Simulated integrations**: appointment scheduling and doctor↔radiologist
  messaging are local SQLite records, never a real external system — this
  matches the PDF's own listed constraints (EHR/EMR integration, regulatory
  setup are prerequisites/constraints, not deliverables). Two things create
  `appointments` rows: the Risk Detection agent's escalation path (a naive
  next-business-day placeholder, no doctor assigned —
  `appointment_service.suggest_appointment`), and patients self-booking a
  specific doctor/date/15-minute-slot (`appointment_service.book_appointment`,
  validated server-side against a fixed 10:00 AM-1:00 PM / 4:00-7:00 PM grid
  and checked for conflicts) — the latter's slots can also be cancelled by
  the patient again.
- **Negative-scenario handling** (PDF's agent decision-point table) is
  enforced deterministically in code as a safety net on top of each LLM
  call, not just trusted from the model's self-report — see
  `backend/agents/*.py` docstrings for exactly which check maps to which
  PDF row (low-confidence extraction, Clinical Inconsistency, escalate for
  clinician validation, Review Required, clinician-oversight gate before a
  patient ever sees a summary).
- **Observability**: `ObservabilityPort` is dependency-injected everywhere;
  `NoOpObservability` is the default so the whole app — including the AI
  pipeline once `OPENAI_API_KEY` is set — runs without needing a Langfuse
  account. `LangfuseObservability` targets the current Langfuse v4 SDK
  (OTel-based `start_observation`/`.update()`/`.end()`), which is a
  materially different API from Langfuse's legacy v2-style
  `.trace()/.generation()` calls.

## Tests

```bash
python -m pytest tests/ -q
```

87 tests, no network/API key required (all LLM calls are mocked or skipped).
Covers: repository CRUD + row-level RBAC, real-file document parsing
(including the scanned-PDF edge case), entity extraction, vector store
chunking/scoped-query behavior, the knowledge graph, both observability
adapters, every agent's negative-scenario branch plus one full mocked
pipeline run, and an end-to-end FastAPI `TestClient` smoke test (login for
all 3 roles, RBAC 403s, graceful 503 when `OPENAI_API_KEY` is absent, page
shells render).

## Deploying

**Live**: http://ec2-63-185-251-88.eu-central-1.compute.amazonaws.com
(AWS eu-central-1 — plain HTTP for now, no custom domain yet; seeded demo
accounts, password `password123` for all — see Setup above).

The app is Dockerized (`Dockerfile`, `docker-compose.yml`) and there's a
Terraform stack under `deploy/terraform/` for a single EC2 instance +
persistent EBS volume + ECR + SSM-managed secrets on AWS — see
[`app/deploy/DEPLOYMENT.md`](app/deploy/DEPLOYMENT.md) for the full walkthrough
(why this shape given SQLite's single-writer constraint, first-time setup,
subsequent deploys via `.github/workflows/deploy.yml`, HTTPS, backups), or
[`app/docs/deployment-architecture.pdf`](app/docs/deployment-architecture.pdf)
for the same material as a diagrammed reference document, including this
specific deployment's live details.

Local Docker smoke test: `docker compose up --build` from `app/`, then open
`http://localhost:8000`.

## Known limitations (by design, not oversights)

- No OCR — a scanned-image report with no text layer correctly produces a
  flagged low-confidence extraction rather than a hallucinated one (see the
  PDF's own "Data quality issues & OCR limitations" constraint).
- Auth is demo-grade (pbkdf2 + signed session cookie) — no HIPAA-grade
  compliance controls, matching the PDF's "Data privacy & compliance setup"
  prerequisite being explicitly out of scope.
- No real hospital system (EHR/EMR) integration; the AI-escalation
  appointment path is a naive next-business-day placeholder record (patient
  self-booking, added later, is a real fixed-slot grid — see Design
  decisions — but still never touches a real calendar).

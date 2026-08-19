-- Clinical Intelligence System — SQLite schema.
-- SQLite is the source of truth for all structured/relational data.
-- ChromaDB (separate) holds only embeddings for semantic search.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('patient','doctor','radiologist')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
    mrn TEXT NOT NULL UNIQUE,
    dob TEXT,
    sex TEXT,
    blood_group TEXT,
    known_conditions TEXT,
    primary_doctor_id INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS allergies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    allergen TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('Food','Medication','Environmental','Skin')),
    severity TEXT CHECK(severity IN ('MILD','MODERATE','SEVERE','CRITICAL')),
    reaction_notes TEXT,
    source TEXT NOT NULL DEFAULT 'self_reported' CHECK(source IN ('self_reported','ai_derived')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS medical_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    entry_type TEXT NOT NULL CHECK(entry_type IN ('past_treatment','condition','medication','symptom')),
    description TEXT NOT NULL,
    entry_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    uploaded_by_user_id INTEGER NOT NULL REFERENCES users(id),
    report_type TEXT NOT NULL CHECK(report_type IN ('lab','radiology','physician_note','discharge_summary')),
    category TEXT NOT NULL,
    original_filename TEXT,
    file_path TEXT,
    file_format TEXT CHECK(file_format IN ('docx','pdf','txt')),
    raw_text TEXT NOT NULL,
    table_text TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending_pipeline'
        CHECK(status IN ('pending_pipeline','processing','processed','error')),
    uploader_notes TEXT,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS report_extractions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id),
    parameter_name TEXT NOT NULL,
    value TEXT NOT NULL,
    unit TEXT,
    reference_range TEXT,
    status TEXT NOT NULL DEFAULT 'UNKNOWN'
        CHECK(status IN ('NORMAL','LOW','HIGH','CRITICAL_LOW','CRITICAL_HIGH','UNKNOWN')),
    confidence REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES reports(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running' CHECK(status IN ('running','completed','failed')),
    overall_confidence REAL,
    escalation_flag INTEGER NOT NULL DEFAULT 0,
    escalation_reason TEXT
);

CREATE TABLE IF NOT EXISTS agent_outputs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id INTEGER NOT NULL REFERENCES pipeline_runs(id),
    agent_name TEXT NOT NULL CHECK(agent_name IN
        ('data_extraction','clinical_analysis','risk_detection','insight_generation','patient_communication')),
    output_json TEXT NOT NULL,
    confidence REAL,
    flagged INTEGER NOT NULL DEFAULT 0,
    flag_reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_run_id INTEGER NOT NULL REFERENCES pipeline_runs(id),
    report_id INTEGER NOT NULL REFERENCES reports(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    summary TEXT,
    key_findings_json TEXT NOT NULL DEFAULT '[]',
    risk_indicators_json TEXT NOT NULL DEFAULT '[]',
    recommendations_json TEXT NOT NULL DEFAULT '[]',
    risk_level TEXT CHECK(risk_level IN ('routine','urgent','stat','emergency')),
    requires_review INTEGER NOT NULL DEFAULT 0,
    clinical_inconsistency INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ai_generated'
        CHECK(status IN ('ai_generated','review_required','doctor_reviewed','finalized')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS patient_summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_id INTEGER NOT NULL UNIQUE REFERENCES insights(id),
    pipeline_run_id INTEGER NOT NULL REFERENCES pipeline_runs(id),
    plain_language_summary TEXT NOT NULL,
    what_this_means_json TEXT NOT NULL DEFAULT '[]',
    what_you_should_do_json TEXT NOT NULL DEFAULT '[]',
    disclaimer TEXT NOT NULL DEFAULT '',
    diagnostic_language_flag INTEGER NOT NULL DEFAULT 0,
    clinician_approved INTEGER NOT NULL DEFAULT 0,
    approved_by_user_id INTEGER REFERENCES users(id),
    approved_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS doctor_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_id INTEGER NOT NULL REFERENCES insights(id),
    doctor_user_id INTEGER NOT NULL REFERENCES users(id),
    action TEXT NOT NULL CHECK(action IN ('validated','modified','rejected','finalized')),
    modified_findings_json TEXT,
    comments TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    report_id INTEGER REFERENCES reports(id),
    pipeline_run_id INTEGER REFERENCES pipeline_runs(id),
    alert_type TEXT NOT NULL CHECK(alert_type IN
        ('critical_lab','critical_radiology','allergy_risk','clinical_inconsistency')),
    severity TEXT NOT NULL CHECK(severity IN ('urgent','stat','emergency')),
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','acknowledged','resolved')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    acknowledged_by_user_id INTEGER REFERENCES users(id),
    acknowledged_at TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    doctor_user_id INTEGER REFERENCES users(id),
    alert_id INTEGER REFERENCES alerts(id),
    suggested_reason TEXT NOT NULL,
    proposed_datetime TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'suggested' CHECK(status IN ('suggested','confirmed','cancelled')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    sender_user_id INTEGER NOT NULL REFERENCES users(id),
    recipient_user_id INTEGER NOT NULL REFERENCES users(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    report_id INTEGER REFERENCES reports(id),
    body TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    read_at TEXT
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    role TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_session_id INTEGER NOT NULL REFERENCES chat_sessions(id),
    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content TEXT NOT NULL,
    retrieved_chunk_ids_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_patient ON reports(patient_id);
CREATE INDEX IF NOT EXISTS idx_report_extractions_report ON report_extractions(report_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_report ON pipeline_runs(report_id);
CREATE INDEX IF NOT EXISTS idx_agent_outputs_run ON agent_outputs(pipeline_run_id);
CREATE INDEX IF NOT EXISTS idx_insights_patient ON insights(patient_id);
CREATE INDEX IF NOT EXISTS idx_alerts_patient ON alerts(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_patient ON messages(patient_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(chat_session_id);

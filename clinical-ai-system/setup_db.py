from db import get_db

db = get_db()
cur = db.cursor()

cur.executescript("""


CREATE TABLE doctors (
    doctor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT
);

CREATE TABLE patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    assigned_doctor INTEGER,
    FOREIGN KEY (assigned_doctor) REFERENCES doctors(doctor_id)
);

CREATE TABLE clinical_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    short_summary TEXT,
    ai_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE email_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER,
    session_id INTEGER,
    email_body TEXT,
    recipient_type TEXT,
    anxiety INTEGER,
    burnout_risk INTEGER,
    depression_risk INTEGER,
    self_harm_risk INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

db.commit()
db.close()
print("Fresh clinic.db created with AI JSON support.")

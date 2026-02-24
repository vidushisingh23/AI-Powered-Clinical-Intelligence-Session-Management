from flask import Flask, request, jsonify, render_template, session, redirect
from flask_socketio import SocketIO, emit
from ai_engine import analyze_session
from rag_engine import query_rag
from aws_mailer import send_email
from crypto_utils import encrypt_text
from db import get_db
import json
from webhooks.webhook_dispatcher import dispatch_event
from webhooks.webhook_events import (
    SESSION_CREATED,
    AI_INSIGHT_GENERATED,
    FOLLOWUP_SENT
)
import hmac
import hashlib
import whisper
import tempfile
import os

app = Flask(__name__, template_folder="templates")
socketio = SocketIO(app, cors_allowed_origins="*")
app.secret_key = "clinical_admin_secret"
API_KEY = "hopequre_test_token_2026"
# Load Whisper Model Once at Startup
whisper_model = whisper.load_model("base")


@app.route("/")
def home():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "hopequre123":
            session["admin"] = True
            return redirect("/dashboard")
        return render_template("login.html", error="Invalid Credentials")
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/login")
    return render_template("dashboard.html")


@app.route("/add-session")
def add_session_page():
    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    # ✅ Fetch all patients for dropdown
    cur.execute("SELECT patient_id, name, email FROM patients")
    patients = cur.fetchall()

    db.close()

    return render_template("add_session.html", patients=patients)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -------- NORMALIZE AI VALUES TO 0-10 SCALE --------
def normalize(value):
    try:
        v = float(value)

        if v > 10:
            v = v / 10

        return max(0, min(10, round(v, 2)))
    except:
        return 0

def verify_api_key(req):
    api_key = req.headers.get("x-api-key")
    return api_key == API_KEY

# ---------------- DASHBOARD METRICS API ----------------

@app.route("/api/dashboard-metrics")
def dashboard_metrics():

    if not (session.get("admin") or verify_api_key(request)):
        return jsonify({"error": "Unauthorized"}), 403

    db = get_db()
    cur = db.cursor()

    # ----- GET QUERY PARAMS -----
    limit = request.args.get("limit", "all")
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    # ----- BASE QUERY (FIXED: SESSION-BASED NOT LOG-BASED) -----
    query = """
    SELECT 
        e.anxiety,
        e.burnout_risk,
        e.depression_risk,
        e.self_harm_risk,
        e.recipient_type,
        e.created_at
    FROM email_logs e
    JOIN clinical_sessions c ON e.session_id = c.session_id
    """

    conditions = []
    params = []

    # ----- DATE RANGE FILTER -----
    if from_date and to_date:
        conditions.append("date(e.created_at) BETWEEN ? AND ?")
        params.extend([from_date, to_date])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # ----- ORDER BY SESSION (NOT LOG) -----
    query += " ORDER BY c.session_id DESC"

    # ----- SESSION LIMIT FILTER -----
    if limit != "all":
        try:
            query += " LIMIT ?"
            params.append(int(limit))
        except:
            pass

    cur.execute(query, params)
    rows = cur.fetchall()

    anxiety = []
    burnout = []
    depression = []
    selfharm = []
    risks = []

    for r in rows:
        anxiety.append(normalize(r[0]))
        burnout.append(normalize(r[1]))
        depression.append(normalize(r[2]))
        selfharm.append(normalize(r[3]))
        risks.append(r[4])

    risk_dist = [
        risks.count("LOW"),
        risks.count("MEDIUM"),
        risks.count("HIGH")
    ]

    # KPI calculations
    total_sessions = len(rows)
    high_risk = risks.count("HIGH")

    avg_anxiety = round(sum(anxiety) / len(anxiety), 2) if anxiety else 0
    avg_burnout = round(sum(burnout) / len(burnout), 2) if burnout else 0

    db.close()

    return jsonify({
        "total_sessions": total_sessions,
        "high_risk": high_risk,
        "avg_anxiety": avg_anxiety,
        "avg_burnout": avg_burnout,
        "anxiety_trend": anxiety[::-1],   # reverse for chart order
        "risk_dist": risk_dist
    })


# ---------------- ADMIN SEARCH (RAG) ----------------

@app.route("/api/admin-search", methods=["POST"])
def admin_search():
    if not (session.get("admin") or verify_api_key(request)):
        return jsonify({"answer": "Unauthorized"}), 403

    q = request.json["query"]
    return jsonify({"answer": query_rag(q)})


# ---------------- ANALYZE SESSION ROUTE ----------------

@app.route("/analyze-session", methods=["POST"])
def analyze():

    # 🔐 API KEY CHECK
    if not verify_api_key(request):
        return jsonify({"error": "Invalid API key"}), 401

    data = request.get_json()
    if not data or "summary" not in data:
        return jsonify({"error": "Missing summary"}), 400

    summary = data["summary"]
    res = analyze_session(summary)
    dispatch_event(
        AI_INSIGHT_GENERATED,
        {
        "risk": res["risk"],
        "signals": list(res.keys()),
        "engine": "clinical_ai_v1"
        }
    )


    db = get_db()
    cur = db.cursor()

    # Get patient and doctor info
        # ✅ Patient selected from dropdown
    pid = data.get("patient_id")

    if not pid:
        return jsonify({"error": "Missing patient_id"}), 400

    # Get patient + doctor info for selected patient
    cur.execute("""
        SELECT patient_id, email, assigned_doctor 
        FROM patients 
        WHERE patient_id = ?
    """, (pid,))
    pid, pemail, did = cur.fetchone()


    cur.execute("SELECT email FROM doctors WHERE doctor_id=?", (did,))
    demail = cur.fetchone()[0]

    recipient = demail if res["risk"] == "HIGH" else pemail

    # Send email
    send_email(recipient, "HopeQure Follow-up", res["email_text"])
    dispatch_event(
        FOLLOWUP_SENT,
        {
        "to": recipient,
        "risk": res["risk"],
        "session_context": "clinical_followup"
        }
    )


    # Store session WITH ai_json
    cur.execute("""
        INSERT INTO clinical_sessions(patient_id, short_summary, ai_json)
        VALUES (?, ?, ?)
    """, (
        pid,
        encrypt_text(summary),
        json.dumps(res)
    ))

    sid = cur.lastrowid

    # Store structured metrics in email_logs
    cur.execute("""
        INSERT INTO email_logs
        (patient_id, session_id, email_body, recipient_type,
         anxiety, burnout_risk, depression_risk, self_harm_risk)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        pid,
        sid,
        encrypt_text(res["email_text"]),
        res["risk"],

        normalize(res["anxiety"]),
        normalize(res["burnout_risk"]),
        normalize(res["depression_risk"]),
        normalize(res["self_harm_risk"])
    ))

    db.commit()
    db.close()
    from rag_builder import build_rag_index
    build_rag_index()
    dispatch_event(
        SESSION_CREATED,
        {
        "session_id": sid,
        "patient_id": pid
        }
    )

    return jsonify({
        "recipient": recipient,
        "risk": res["risk"]
    })


# ---------------- VIEW DETAILED REPORT ----------------

@app.route("/report/<int:session_id>")
def view_report(session_id):

    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    # 1️⃣ Fetch report data
    cur.execute("""
    SELECT 
        c.ai_json,
        c.short_summary,
        c.created_at,
        p.name
    FROM clinical_sessions c
    JOIN patients p ON c.patient_id = p.patient_id
    WHERE c.session_id = ?
""", (session_id,))
    row = cur.fetchone()
    patient_name = row["name"]

    if not row:
        db.close()
        return "Report Not Found"

    # 2️⃣ Calculate SAFE session number (display-only)
    cur.execute("""
        SELECT COUNT(*) AS session_number
        FROM clinical_sessions
        WHERE created_at <= ?
    """, (row["created_at"],))
    session_number = cur.fetchone()["session_number"]

    db.close()

    # 3️⃣ Parse AI report JSON safely
    try:
        report = json.loads(row["ai_json"])
    except Exception:
        report = {}

    # 4️⃣ Render WITHOUT exposing session_id
    return render_template(
    "report.html",
    report=report,
    session_number=session_number,
    date=row["created_at"],
    patient_name=patient_name
)
# ---------------- REPORT API (JSON) ----------------
@app.route("/api/report/<int:session_id>")
def api_report(session_id):

    # 🔐 API KEY CHECK
    if not verify_api_key(request):
        return jsonify({"error": "Invalid API key"}), 401

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT 
            c.ai_json,
            c.created_at,
            e.recipient_type,
            e.anxiety,
            e.burnout_risk,
            e.depression_risk,
            e.self_harm_risk
        FROM clinical_sessions c
        JOIN email_logs e ON c.session_id = e.session_id
        WHERE c.session_id = ?
    """, (session_id,))

    row = cur.fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Report not found"}), 404

    ai_json, created_at, risk, anxiety, burnout, depression, self_harm = row

    # Display-only session number
    cur.execute("""
        SELECT COUNT(*) 
        FROM clinical_sessions 
        WHERE created_at <= ?
    """, (created_at,))
    session_number = cur.fetchone()[0]

    db.close()

    report = json.loads(ai_json)

    return jsonify({
        "session_number": session_number,
        "date": created_at,
        "risk": risk,
        "scores": {
            "anxiety": anxiety,
            "burnout": burnout,
            "depression": depression,
            "self_harm": self_harm
        },
        "email_text": report.get("email_text"),
        "signals": list(report.keys())
    })

@app.route("/patients/new", methods=["GET"])
def patient_page():

    if not session.get("admin"):
        return redirect("/login")

    db = get_db()
    cur = db.cursor()

    # ✅ Fetch doctors for dropdown
    cur.execute("SELECT doctor_id, name, email FROM doctors")
    doctors = cur.fetchall()

    db.close()

    return render_template("add_patient.html", doctors=doctors)

@app.route("/patients/new", methods=["POST"])
def add_patient():

    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    name = data.get("name")
    email = data.get("email")
    doctor_id = data.get("doctor_id")

    # ✅ Basic validation
    if not name or not email:
        return jsonify({"error": "Missing patient details"}), 400

    db = get_db()
    cur = db.cursor()

    # doctor_id optional
    if doctor_id == "":
        doctor_id = None

    cur.execute("""
        INSERT INTO patients (name, email, assigned_doctor)
        VALUES (?, ?, ?)
    """, (name, email, doctor_id))

    db.commit()
    db.close()
    from rag_builder import build_rag_index
    build_rag_index()


    return jsonify({"status": "success"})


# ---------------- REPORT LIST FOR TABLE ----------------
@app.route("/report-list")
def report_list():

    if not (session.get("admin") or verify_api_key(request)):
        return jsonify([])

    db = get_db()
    cur = db.cursor()

    cur.execute("""
    SELECT 
        c.session_id,
        c.created_at,
        e.recipient_type AS risk,
        e.anxiety,
        e.burnout_risk,
        e.depression_risk,
        e.self_harm_risk,
        p.name AS patient_name
    FROM clinical_sessions c
    JOIN email_logs e ON c.session_id = e.session_id
    JOIN patients p ON c.patient_id = p.patient_id
    ORDER BY c.session_id DESC
    LIMIT 15
""")


    rows = cur.fetchall()
    db.close()

    return jsonify([
{
    "session_id": encrypt_text(str(r[0])),
    "raw_id": r[0],
    "date": r[1],
    "risk": r[2],
    "anxiety": r[3],
    "burnout": r[4],
    "depression": r[5],
    "self_harm": r[6],
    "patient_name": r[7]
}
for r in rows
])


WEBHOOK_SECRET = "ngrok-test"  # MUST MATCH DB


@app.route("/webhook-test", methods=["POST"])
def webhook_test():
    signature = request.headers.get("X-HopeQure-Signature")
    raw_body = request.get_data(as_text=True)

    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        raw_body.encode(),
        hashlib.sha256
    ).hexdigest()

    if not signature or not hmac.compare_digest(signature, expected_signature):
        print("❌ Invalid webhook signature")
        return {"error": "Invalid signature"}, 401

    print("🔔 WEBHOOK VERIFIED & RECEIVED")
    print(request.json)

    return {"status": "ok"}, 200

# ---------------- WHISPER AUDIO TRANSCRIPTION ----------------

@app.route("/transcribe-audio", methods=["POST"])
def transcribe_audio():

    if not verify_api_key(request):
        return jsonify({"error": "Invalid API key"}), 401

    if "audio" not in request.files:
        return jsonify({"error": "No audio file uploaded"}), 400

    audio_file = request.files["audio"]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp:
        audio_file.save(temp.name)
        temp_path = temp.name

    try:
        result = whisper_model.transcribe(
            temp_path,
            language="en",
            fp16=False
        )

        transcript = result.get("text", "").strip()

        return jsonify({"text": transcript})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            os.remove(temp_path)
        except:
            pass

        
@socketio.on("connect")
def handle_connect():
    print("CLIENT CONNECTED SOCKET")
@app.route("/doctors/new", methods=["GET"])
def doctor_page():
    if not session.get("admin"):
        return redirect("/login")
    return render_template("add_doctor.html")


@app.route("/doctors/new", methods=["POST"])
def add_doctor():

    if not session.get("admin"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    name = data.get("name")
    email = data.get("email")

    if not name or not email:
        return jsonify({"error": "Missing doctor details"}), 400

    db = get_db()
    cur = db.cursor()

    cur.execute("""
        INSERT INTO doctors (name, email)
        VALUES (?, ?)
    """, (name, email))

    db.commit()
    db.close()

    return jsonify({"status": "success"})





if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=9000, debug=True)


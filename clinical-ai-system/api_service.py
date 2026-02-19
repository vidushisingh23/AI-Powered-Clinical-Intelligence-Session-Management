from flask import Flask, jsonify, request, make_response
from db import get_db
from crypto_utils import decrypt_text

app = Flask(__name__)

API_KEY = "hopequre_test_token_2026"

# -------------------- AUTH --------------------
def require_token():
    token = request.headers.get("X-API-KEY")
    return token == API_KEY

@app.before_request
def authenticate():
    # CORS preflight must NOT require token
    if request.method == "OPTIONS":
        response = make_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        return response
    if request.path == "/api/health":
        return  # allow unauthenticated health checks
    if request.path.startswith("/api/"):
        if not require_token():
            return jsonify({"error": "Unauthorized"}), 401

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    return response


# -------------------- HEALTH --------------------
@app.route("/api/health")
def health():
    return jsonify({"status": "HopeQure Clinical API running"})


# -------------------- PATIENTS --------------------
@app.route("/api/patients")
def patients():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT patient_id,name,email,assigned_doctor FROM patients")
    rows = cur.fetchall()
    db.close()

    return jsonify([
        {"patient_id":r[0],"name":r[1],"email":r[2],"assigned_doctor":r[3]}
        for r in rows
    ])


# -------------------- DOCTORS --------------------
@app.route("/api/doctors")
def doctors():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT doctor_id,name,email FROM doctors")
    rows = cur.fetchall()
    db.close()

    return jsonify([
        {"doctor_id":r[0],"name":r[1],"email":r[2]}
        for r in rows
    ])


# -------------------- SESSIONS --------------------
@app.route("/api/patients/<int:pid>/sessions")
def sessions(pid):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT session_id,short_summary FROM clinical_sessions WHERE patient_id=?", (pid,))
    rows = cur.fetchall()
    db.close()

    return jsonify([
        {"session_id":r[0],"short_summary":r[1]} for r in rows
    ])


# -------------------- EMAIL LOGS --------------------
@app.route("/api/email-logs")
def email_logs():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT log_id,patient_id,session_id,email_body,recipient_type,
               anxiety,burnout_risk,depression_risk,self_harm_risk
        FROM email_logs ORDER BY log_id DESC
    """)
    rows = cur.fetchall()
    db.close()

    return jsonify([
        {
            "log_id":r[0],
            "patient_id":r[1],
            "session_id":r[2],
            "email_body":decrypt_text(r[3]),
            "recipient_type":r[4],
            "anxiety":r[5],
            "burnout_risk":r[6],
            "depression_risk":r[7],
            "self_harm_risk":r[8]
        } for r in rows
    ])


# -------------------- DASHBOARD METRICS --------------------
@app.route("/api/dashboard-metrics")
def dashboard_metrics():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM clinical_sessions")
    total_sessions = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM email_logs WHERE recipient_type='HIGH'")
    high_risk = cur.fetchone()[0]

    cur.execute("SELECT AVG(anxiety),AVG(burnout_risk) FROM email_logs")
    avg_anxiety, avg_burnout = cur.fetchone()

    cur.execute("""
        SELECT 
        SUM(CASE WHEN recipient_type='LOW' THEN 1 ELSE 0 END),
        SUM(CASE WHEN recipient_type='MEDIUM' THEN 1 ELSE 0 END),
        SUM(CASE WHEN recipient_type='HIGH' THEN 1 ELSE 0 END)
        FROM email_logs
    """)
    low, medium, high = cur.fetchone()

    cur.execute("SELECT anxiety FROM email_logs ORDER BY log_id DESC LIMIT 7")
    anxiety_trend = [r[0] for r in cur.fetchall()][::-1]

    db.close()

    return jsonify({
        "total_sessions": total_sessions,
        "high_risk": high_risk,
        "avg_anxiety": round(avg_anxiety or 0,2),
        "avg_burnout": round(avg_burnout or 0,2),
        "risk_dist": [low or 0, medium or 0, high or 0],
        "anxiety_trend": anxiety_trend
    })


if __name__ == "__main__":
    app.run(port=9000, debug=True)

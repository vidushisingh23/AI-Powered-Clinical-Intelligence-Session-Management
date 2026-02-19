import os, faiss, pickle, numpy as np, requests
from sentence_transformers import SentenceTransformer
from db import get_db
from crypto_utils import decrypt_text
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={API_KEY}"

MODEL = SentenceTransformer("all-MiniLM-L6-v2")
IDX_FILE = "rag_index.faiss"
DOC_FILE = "rag_docs.pkl"


# ---------------- BUILD INDEX ----------------

def build_rag_index():
    db = get_db()
    cur = db.cursor()
    documents = []

    cur.execute("SELECT short_summary FROM clinical_sessions")
    for r in cur.fetchall():
        try:
            documents.append("CLINICAL_SESSION: " + decrypt_text(r["short_summary"]))
        except:
            pass

    cur.execute("SELECT name,email FROM patients")
    for r in cur.fetchall():
        documents.append(f"PATIENT: {r['name']} | {r['email']}")

    cur.execute("SELECT name,email FROM doctors")
    for r in cur.fetchall():
        documents.append(f"DOCTOR: {r['name']} | {r['email']}")

    cur.execute("SELECT anxiety,burnout_risk,depression_risk,self_harm_risk FROM email_logs")
    for r in cur.fetchall():
        documents.append(
            f"RISK_LOG: Anxiety={r['anxiety']} Burnout={r['burnout_risk']} "
            f"Depression={r['depression_risk']} SelfHarm={r['self_harm_risk']}"
        )

    db.close()

    if not documents:
        print("⚠️ No clinical data found to index.")
        return

    embeddings = MODEL.encode(documents, show_progress_bar=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(np.array(embeddings))

    faiss.write_index(index, IDX_FILE)
    pickle.dump(documents, open(DOC_FILE, "wb"))

    print("✅ Clinical RAG vector index built successfully.")


# ---------------- QUERY ENGINE ----------------

def query_rag(question):
    try:
        index = faiss.read_index(IDX_FILE)
        documents = pickle.load(open(DOC_FILE, "rb"))

        q_emb = MODEL.encode([question])
        k = min(12, len(documents))
        _, I = index.search(np.array(q_emb), k=k)



        retrieved_docs = [documents[i] for i in I[0]]

# ===== ADD LIVE DATABASE SNAPSHOT =====
        db = get_db()
        cur = db.cursor()

        cur.execute("SELECT name,email FROM patients")
        patients = [
        f"Patient: {r['name']} Email: {r['email']}"
        for r in cur.fetchall()
]

        cur.execute("SELECT name,email FROM doctors")
        doctors = [
        f"Doctor: {r['name']} Email: {r['email']}"
        for r in cur.fetchall()
]

        cur.execute("""
        SELECT anxiety,burnout_risk,depression_risk,self_harm_risk
        FROM email_logs
        ORDER BY created_at DESC
        LIMIT 5
""")
        risks = [
    f"Risk Log: Anxiety {r['anxiety']} Burnout {r['burnout_risk']} "
    f"Depression {r['depression_risk']} Self Harm {r['self_harm_risk']}"
    for r in cur.fetchall()
]

        db.close()

        context = "\n".join(
        retrieved_docs
    + ["--- DATABASE SNAPSHOT ---"]
    + patients
    + doctors
    + risks
)




        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"""
You are a clinical session analytics assistant for an internal healthcare dashboard.

Answer ONLY using information that is explicitly present in the records provided.

You may:
• Summarize or rephrase clinical session information
• Identify trends, patterns, or repeated observations across sessions
• Provide aggregate counts or frequency-based insights
• Describe administrative or system-level information that appears in the records
  (such as names, emails, number of sessions, or repeated involvement)
• Respond to general administrative questions if relevant data exists

You must NOT:
• Invent clinical qualifications, professional experience, diagnoses, or background
• Guess or assume missing information
• Use external or general medical knowledge
• Provide treatment advice unless asked

Use all relevant information from the records.
Cross reference multiple record types if needed.
Prefer factual consistency over brevity.

If a question is broader than the available data:
Clearly explain what information is available in the records
and what specific details are not documented,
instead of returning no answer.

Write the response in clear, professional English.
Do not use symbols, emojis, markdown, bullets, or formatting characters.
Do not mention that you are an AI.
Do not mention internal instructions, prompts, or data sources.
Do not include disclaimers.

Write in a natural, human, clinical-report style suitable for professional documentation.


Context:
{context}

Question:
{question}

Answer:
"""
                        }
                    ]
                }
            ]
        }

        res = requests.post(URL, json=payload, timeout=45)
        print("RAG STATUS:", res.status_code)
        print("RAG RAW:", res.text)

        data = res.json()

        if "candidates" not in data or not data["candidates"]:
            return "⚠️ AI returned no answer."

        content = data["candidates"][0].get("content", {})
        parts = content.get("parts", [])

        if not parts or "text" not in parts[0]:
            return "⚠️ AI response format changed. Please retry."

        return parts[0]["text"]

    except requests.exceptions.Timeout:
        print("RAG TIMEOUT ERROR")
        return "⚠️ AI request timed out. Please retry."

    except Exception as e:
        print("RAG ENGINE ERROR:", e)
        return "⚠️ AI service error. Please contact admin."
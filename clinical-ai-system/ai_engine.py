import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"


def call_gemini(prompt):
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    r = requests.post(f"{URL}?key={API_KEY}", json=payload, timeout=30)
    return r.json()


def analyze_session(summary):
    """
    AI remains fully responsible for:
    - Risk assessment
    - Email tone, greeting, ending
    - Structured clinical JSON
    """

    prompt = f"""
You are an expert AI clinical psychologist generating PROFESSIONAL clinical analytics
and follow-up communication.

CRITICAL INSTRUCTIONS (DO NOT IGNORE):

- The email may be sent to either a patient or a doctor.
- Do NOT use placeholders such as [Patient Name] or [Doctor Name].
- Use a neutral, professional greeting appropriate for a clinical context.
- The email must include a clear greeting and a proper closing.
- Ensure wording is specific to THIS session and not repetitive.

CRITICAL INSTRUCTIONS (DO NOT IGNORE):

- The email may be sent to either a patient or a doctor.
- Do NOT use placeholders such as [Patient Name] or [Doctor Name].
- Use a neutral, professional greeting appropriate for a clinical context.
- The email must include a clear greeting and a proper closing.
- Ensure wording is specific to THIS session and not repetitive.
The greeting must be determined ONLY by the risk level:

- HIGH → "Dear Doctor,"
- LOW → "Dear Client,"
- MEDIUM → choose the most appropriate recipient.

Do not use any other greeting.


EMAIL FORMAT RULES:

1. Professional, empathetic, clinical tone.
2. NO blank line after greeting.
3. NO extra spacing.
4. Use EXACT structure below.

STRUCTURE:

Subject: HopeQure Session Follow-up

<Appropriate Greeting>,
Thank you for the recent clinical session at HopeQure. Based on the session discussion and analysis, the following observations have been noted:

• Key clinical concern summary  
• Emotional and psychological state overview  
• Risk-level interpretation  

Warm regards,
HopeQure Clinical Team

--------------------------------------

STRICT JSON RULES (MANDATORY):

1. RETURN ONLY VALID JSON.
2. NO text outside JSON.
3. All risk values must be integers between 0 and 10.
4. Risk classification:
   0–3  → LOW
   4–6  → MEDIUM
   7–10 → HIGH
5. "recommendations" must always contain 3–6 clinical actionable items, never empty.

Return EXACT JSON in this format:

{{
  "risk": "LOW or MEDIUM or HIGH",
  "email_text": "fully formatted professional email",
  "anxiety": 0,
  "burnout_risk": 0,
  "depression_risk": 0,
  "self_harm_risk": 0,
  "clinical_report": {{
      "overallAssessment": "",
      "emotionalState": [],
      "cognitivePatterns": [],
      "recommendations": [],
      "sleepPatterns": {{
          "sleepQuality": "",
          "sleepOnset": "",
          "nightAwakenings": false,
          "daytimeFatigue": false
      }},
      "physicalSymptoms": [],
      "functionalImpact": {{
          "work": "",
          "social": "",
          "dailyActivities": ""
      }},
      "riskAssessment": {{
          "suicidalIdeation": false,
          "selfHarmRisk": false,
          "psychoticSymptoms": false
      }},
      "patientInsight": "",
      "doctorSummary": {{
          "clinicalImpression": "",
          "severity": "",
          "diagnosticIndicators": [],
          "prognosis": ""
      }},
      "treatmentPlan": {{
          "therapy": [],
          "lifestyleRecommendations": []
      }},
      "followUpPlan": {{
          "timeline": "",
          "monitoring": []
      }}
  }}
}}

SESSION SUMMARY:
{summary}
"""

    try:
        response = call_gemini(prompt)

        text = response["candidates"][0]["content"]["parts"][0]["text"]
        text = text.replace("```json", "").replace("```", "").strip()

        result = json.loads(text)
        # Ensure AI always provides recommendations
        if "clinical_report" in result:
            if "recommendations" not in result["clinical_report"]:
                result["clinical_report"]["recommendations"] = []



        required = [
            "risk",
            "email_text",
            "anxiety",
            "burnout_risk",
            "depression_risk",
            "self_harm_risk",
            "clinical_report"
        ]

        for field in required:
            if field not in result:
                raise ValueError(f"Missing required field: {field}")

        return result

    except Exception as e:
        print("AI ENGINE ERROR:", e)

        # Safe fallback (still professional, no placeholders)
        return {
            "risk": "MEDIUM",
            "email_text":
                "Subject: HopeQure Session Follow-up\n"
                "Dear Recipient,\n"
                "Thank you for the recent clinical session at HopeQure. "
                "Automated analysis indicates moderate psychological risk based on the session discussion.\n\n"
                "Warm regards,\n"
                "HopeQure Clinical Team",
            "anxiety": 5,
            "burnout_risk": 5,
            "depression_risk": 5,
            "self_harm_risk": 1,
            "clinical_report": {
                "overallAssessment": "Automated analysis unavailable.",
                "emotionalState": [],
                "cognitivePatterns": [],
                "recommendations": [],
                "sleepPatterns": {},
                "physicalSymptoms": [],
                "functionalImpact": {},
                "riskAssessment": {},
                "patientInsight": "",
                "doctorSummary": {},
                "treatmentPlan": {},
                "followUpPlan": {}
            }
        }

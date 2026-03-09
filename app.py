import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """You are a freight coordinator. Extract load details from emails. Return ONLY valid JSON, no markdown.

JSON structure: {"origin_city":"","origin_state":"","destination_city":"","destination_state":"","ready_to_ship_date":"","pickup_date":"","requested_delivery_date":"","delivery_date":"","commodity":"","weight":"","pieces":"","length_ft":"","width_ft":"","height_ft":"","total_linear_feet":"","equipment_type":"","stackable":"","hazmat":"","temperature_requirements":"","special_requirements":"","customer_name":"","contact_info":"","reference_number":"","notes":"","follow_up_questions":[]}

Use NOT SPECIFIED for missing fields. Dates in MM/DD/YYYY. Equipment: Dry Van/Flatbed/Reefer/LTL/Step Deck/RGN/Tanker. follow_up_questions: [{question,reason,critical}]. Ask about ready_to_ship_date, requested_delivery_date, dimensions if missing. Equipment-specific questions for Flatbed/Reefer/Hazmat/LTL/Food/Steel. 3-10 questions total."""

@app.route("/")
def index():
    return send_from_directory(".", "ui.html")

@app.route("/api/extract", methods=["POST"])
def extract():
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not set"}), 500
    data = request.get_json()
    email_text = data.get("email", "").strip()
    if not email_text:
        return jsonify({"error": "No email provided"}), 400
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 1500, "system": SYSTEM_PROMPT, "messages": [{"role": "user", "content": email_text}]},
        timeout=30)
    if not r.ok:
        return jsonify({"error": r.text}), r.status_code
    raw = "".join(c.get("text","") for c in r.json().get("content",[]))
    clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        return jsonify(json.loads(clean))
    except Exception as e:
        return jsonify({"error": str(e), "raw": raw}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

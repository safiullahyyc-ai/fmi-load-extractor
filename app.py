import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """You are an expert freight coordinator assistant. Extract load details from customer emails and return ONLY a valid JSON object — no markdown, no backticks, no explanation.

Return this exact JSON structure:
{
  "origin_city": "",
  "origin_state": "",
  "destination_city": "",
  "destination_state": "",
  "ready_to_ship_date": "",
  "pickup_date": "",
  "requested_delivery_date": "",
  "delivery_date": "",
  "commodity": "",
  "weight": "",
  "pieces": "",
  "length_ft": "",
  "width_ft": "",
  "height_ft": "",
  "total_linear_feet": "",
  "equipment_type": "",
  "stackable": "",
  "hazmat": "",
  "temperature_requirements": "",
  "special_requirements": "",
  "customer_name": "",
  "contact_info": "",
  "reference_number": "",
  "notes": "",
  "follow_up_questions": []
}

EXTRACTION RULES:
- Use "NOT SPECIFIED" for any missing or unclear field
- Dates: MM/DD/YYYY if clear, otherwise quote exact text
- ready_to_ship_date: when freight is available at origin
- requested_delivery_date: the customer's hard deadline
- Equipment type: infer from context (Dry Van, Flatbed, Reefer, LTL, Step Deck, RGN, Tanker) or NOT SPECIFIED
- Weight: include units
- length_ft/width_ft/height_ft: individual dimensions in feet
- stackable: Yes/No/NOT SPECIFIED
- hazmat: Yes/No/NOT SPECIFIED

FOLLOW-UP QUESTIONS — generate array of: { "question": "...", "reason": "...", "critical": true/false }
critical:true blocks quoting. critical:false is important but non-blocking.

ALWAYS ASK if not in email:
1. If ready_to_ship_date missing: "When is the freight ready to ship / available at origin?"
2. If requested_delivery_date missing: "What is the requested or required delivery date?"
3. If all dimensions missing: "What are the shipment dimensions (L x W x H in feet)?"

EQUIPMENT-SPECIFIC:
- FLATBED: tarps needed (type/count), chains vs straps, oversize/overweight permits, loading equipment, bracing/dunnage
- REEFER: exact temp range, pre-cool required, continuous monitoring, product sensitivity
- STEP DECK/RGN: exact dimensions, permits, pilot car
- LTL: NMFC class, pallet size, liftgate needed
- HAZMAT: UN number, class, emergency contact
- ELECTRONICS/HIGH VALUE: declared value, security requirements
- FOOD/BEVERAGE: food-grade trailer, wash-out certificate
- STEEL/COILS/PIPE: crane/forklift at origin and dest, bracing requirements

Always ask about missing accessorials: liftgate, inside delivery, appointment required, detention expectations.
Generate 3-10 questions total."""


@app.route("/")
def index():
    # Try static/ folder first, then root
    if os.path.exists(os.path.join(app.root_path, "static", "index.html")):
        return send_from_directory(os.path.join(app.root_path, "static"), "index.html")
    # Fall back to any html file in root
    for name in ["index.html", "index (5).html"]:
        if os.path.exists(os.path.join(app.root_path, name)):
            return send_from_directory(app.root_path, name)
    return "App is running but index.html not found", 200


@app.route("/api/extract", methods=["POST"])
def extract():
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured on server"}), 500

    data = request.get_json()
    email_text = data.get("email", "").strip()
    if not email_text:
        return jsonify({"error": "No email text provided"}), 400

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 1500,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": email_text}],
        },
        timeout=30,
    )

    if not response.ok:
        return jsonify({"error": response.text}), response.status_code

    result = response.json()
    raw = "".join(c.get("text", "") for c in result.get("content", []))
    clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        parsed = json.loads(clean)
        return jsonify(parsed)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Could not parse Claude response: {e}", "raw": raw}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

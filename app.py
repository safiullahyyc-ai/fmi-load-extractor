import os, json, requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)
KEY = os.environ.get("ANTHROPIC_API_KEY", "")
PROMPT = open("prompt.txt").read()

@app.route("/")
def index():
    return send_from_directory(".", "ui.html")

@app.route("/api/extract", methods=["POST"])
def extract():
    if not KEY: return jsonify({"error": "No API key"}), 500
    email = request.get_json().get("email", "").strip()
    if not email: return jsonify({"error": "No email"}), 400
    r = requests.post("https://api.anthropic.com/v1/messages",
        headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 1500, "system": PROMPT, "messages": [{"role": "user", "content": email}]},
        timeout=30)
    if not r.ok: return jsonify({"error": r.text}), r.status_code
    raw = "".join(c.get("text","") for c in r.json().get("content",[]))
    clean = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try: return jsonify(json.loads(clean))
    except Exception as e: return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

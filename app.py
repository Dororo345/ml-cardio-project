"""Educational heart-disease-classification demo: not a clinical risk calculator."""
from pathlib import Path
import json
from uuid import uuid4

import joblib
import pandas as pd
from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException
from xai import HeartExplainer
from validation import ValidationError, validate_payload

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # small JSON with 13 measurements

# joblib uses pickle: load ONLY this project's trusted local artifact.
model = joblib.load(BASE_DIR / "models" / "heart_model.joblib")
with (BASE_DIR / "models" / "model_info.json").open(encoding="utf-8") as file:
    model_info = json.load(file)
FEATURES = model_info["input_features"]
xai_explainer = HeartExplainer(model, model_info, BASE_DIR)


@app.before_request
def assign_request_id():
    g.request_id = uuid4().hex


@app.after_request
def add_response_headers(response):
    response.headers["X-Request-ID"] = g.get("request_id", "")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def error_response(code, message, status, *, fields=None):
    payload = {"code": code, "error": message, "request_id": g.get("request_id", "")}
    if fields:
        payload["fields"] = fields
    return jsonify(payload), status


@app.errorhandler(HTTPException)
def on_http_error(error):
    if request.path == "/predict":
        code = "PAYLOAD_TOO_LARGE" if error.code == 413 else "HTTP_ERROR"
        return error_response(code, error.description, error.code)
    return error


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/predict")
def predict():
    data = request.get_json(silent=True)
    try:
        values = validate_payload(data, FEATURES)
    except ValidationError as err:
        return error_response(err.code, str(err), 400, fields=err.fields)

    input_df = pd.DataFrame([values], columns=FEATURES)
    try:
        probability = float(model.predict_proba(input_df)[0, 1])
        factors = xai_explainer.explain(input_df)
    except Exception:
        # Never log the submitted medical input or reveal traceback to the client.
        app.logger.exception("Prediction failed: request_id=%s", g.get("request_id", ""))
        return error_response("PREDICTION_ERROR", "Ошибка расчёта", 500)

    return jsonify({
        "probability": round(probability, 4),
        "probability_percent": round(probability * 100, 2),
        "predicted_class": int(probability >= 0.5),
        "factors": factors,
        "warning": "Учебная классификация, не медицинский диагноз и не прогноз будущего риска",
        "request_id": g.get("request_id", ""),
    })


if __name__ == "__main__":
    # Debugger must not be exposed, especially if used on a LAN / server.
    app.run(host="127.0.0.1", port=5000, debug=False)

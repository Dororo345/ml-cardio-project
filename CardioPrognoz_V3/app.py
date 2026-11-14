
from pathlib import Path
import os
import json

import joblib
import pandas as pd
from flask import Flask, g, jsonify, render_template, request, send_from_directory
from xai import HeartExplainer
from accounts import login_required, register_accounts, require_csrf
from validation import check_anomalies
from feature_contract import InputError, normalize_values
import integration

app = Flask(__name__)
register_accounts(app)

BASE_DIR = Path(__file__).resolve().parent

model = joblib.load(BASE_DIR / "models" / "heart_model.joblib")

with open(BASE_DIR / "models" / "model_info.json", encoding="utf-8") as f:
    model_info = json.load(f)

FEATURES = model_info["input_features"]

xai_explainer = HeartExplainer(model, model_info, BASE_DIR)

@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    if g.current_user is None:
        return jsonify({"error": "Для расчёта необходимо войти в систему."}), 401

    data = request.get_json(silent=True)
    try:
        values = normalize_values(data, FEATURES)
    except InputError as exc:
        return jsonify({"error": str(exc), "fields": exc.fields}), 400

    input_df = pd.DataFrame([values], columns=FEATURES)

    probability = float(model.predict_proba(input_df)[0, 1])

    factors = xai_explainer.explain(input_df)

    
    return jsonify({
        "probability": round(probability, 4),
        "probability_percent": round(probability * 100, 2),
        "predicted_class": int(probability >= 0.5),
        "factors": factors,
        "warnings": check_anomalies(values),
        "warning": "Учебный прогноз, не медицинский диагноз"
    })


def score_synthetic_values(values):
    """Score validated synthetic values, without explanation or persistence."""
    input_df = pd.DataFrame([values], columns=FEATURES)
    probability = float(model.predict_proba(input_df)[0, 1])
    if not 0 <= probability <= 1:
        raise ValueError("Модель вернула недопустимую вероятность")
    return {
        "percent": round(probability * 100, 2),
        "predicted_class": int(probability >= 0.5),
        "warnings": check_anomalies(values),
    }


@app.route("/integration", methods=["GET"])
@login_required
def integration_page():
    return render_template("integration.html", results=None, fetched=None, error=None, mode=None)


@app.route("/integration/mock", methods=["POST"])
@login_required
def integration_mock():
    require_csrf()
    record_id = request.form.get("record_id", "").strip()
    try:
        values = normalize_values(integration.fetch_mock_record(record_id), FEATURES)
        fetched = {"record_id": record_id, "data": values, "score": score_synthetic_values(values)}
        return render_template("integration.html", results=None, fetched=fetched, error=None, mode="mock")
    except (integration.IntegrationError, InputError) as exc:
        return render_template("integration.html", results=None, fetched=None, error=str(exc), mode="mock"), 400


@app.route("/integration/import", methods=["POST"])
@login_required
def integration_import():
    require_csrf()
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename.lower().endswith(".csv"):
        return render_template("integration.html", results=None, fetched=None,
                               error="Выберите CSV-файл в формате UTF-8.", mode="csv"), 400
    try:
        raw = uploaded.stream.read(integration.MAX_UPLOAD_BYTES + 1)
        parsed = integration.read_csv_bytes(raw)
    except integration.IntegrationError as exc:
        return render_template("integration.html", results=None, fetched=None,
                               error=str(exc), mode="csv"), 400
    results = []
    for line_number, data, error in parsed:
        if error is None:
            try:
                score = score_synthetic_values(normalize_values(data, FEATURES))
                results.append({"line": line_number, "ok": True, "score": score})
            except (InputError, ValueError) as exc:
                results.append({"line": line_number, "ok": False, "error": str(exc)})
        else:
            results.append({"line": line_number, "ok": False, "error": error})
    return render_template("integration.html", results=results, fetched=None, error=None, mode="csv")


@app.route("/integration/sample.csv", methods=["GET"])
@login_required
def integration_sample():
    return send_from_directory(BASE_DIR / "samples", "synthetic_measurements.csv", as_attachment=True)

if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=os.environ.get("CARDIO_DEBUG") == "1")

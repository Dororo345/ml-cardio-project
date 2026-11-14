"""Local read-only fake medical system. ONLY synthetic, hard-coded demo records."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SAMPLE = {
    "age_years": 59, "sex_code": 1, "chest_pain_code": 4,
    "resting_bp": 138, "cholesterol": 271, "fasting_sugar_flag": 0,
    "rest_ecg_code": 2, "max_heart_rate": 182, "exercise_angina_flag": 0,
    "st_depression": 0.0, "st_slope_code": 1, "vessels_code": 0, "thal_code": 3,
}
RECORDS = {
    "SYN-001": SAMPLE,
    "SYN-002": {**SAMPLE, "age_years": 42, "resting_bp": 126, "cholesterol": 205},
    "SYN-003": {**SAMPLE, "age_years": 67, "resting_bp": 160, "cholesterol": 300},
}

# Twenty deterministic, distinct synthetic examples; retain the original three.
for index in range(4, 21):
    RECORDS[f"SYN-{index:03}"] = {
        **SAMPLE, "age_years": 35 + index,
        "resting_bp": 110 + 2 * index, "cholesterol": 170 + 3 * index,
    }


class MockHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        prefix = "/api/v1/records/"
        record_id = self.path[len(prefix):] if self.path.startswith(prefix) else ""
        if record_id in RECORDS:
            status = 200
            body = {"record_id": record_id, "measurements": RECORDS[record_id]}
        else:
            status = 404
            body = {"error": "Synthetic record not found"}
        output = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(output)))
        self.end_headers()
        self.wfile.write(output)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5001), MockHandler)
    print("Synthetic medical mock available at http://127.0.0.1:5001 (Ctrl+C to stop)")
    server.serve_forever()

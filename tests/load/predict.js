// LZ11-NFR-02: proposed target, p95 prediction under 1500 ms at 5 VUs.
// The account is temporary and contains no real user information.
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const USER = __ENV.K6_USER || 'synthetic_qa';
const PASSWORD = __ENV.K6_PASSWORD;
if (!PASSWORD) {
  throw new Error('K6_PASSWORD is required for the isolated test account');
}

const predictionDuration = new Trend('prediction_duration', true);
let authenticated = false;

export const options = {
  vus: 5,
  duration: '45s',
  // By default k6 clears a VU's cookies after each iteration. We log in
  // once per VU, so the session cookie must persist for subsequent calls.
  noCookiesReset: true,
  thresholds: {
    prediction_duration: ['p(95)<1500'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.99'],
  },
};

const sample = {
  age: 59, sex: 1, cp: 4, trestbps: 138, chol: 271,
  fbs: 0, restecg: 2, thalach: 182, exang: 0,
  oldpeak: 0, slope: 1, ca: 0, thal: 3,
};

function login() {
  const page = http.get(`${BASE_URL}/login`);
  const matched = page.body.match(/name="csrf_token" value="([^"]+)"/);
  if (!matched) {
    check(page, { 'login page has CSRF token': () => false });
    return false;
  }
  const response = http.post(`${BASE_URL}/login`, {
    csrf_token: matched[1], username: USER, password: PASSWORD,
  }, { redirects: 0 });
  return check(response, {
    'synthetic QA user authenticated': (r) =>
      r.status === 302 && r.headers.Location === '/',
  });
}

export default function () {
  if (!authenticated) authenticated = login();
  if (!authenticated) return;

  const response = http.post(`${BASE_URL}/predict`, JSON.stringify(sample), {
    headers: { 'Content-Type': 'application/json' },
  });
  predictionDuration.add(response.timings.duration);
  check(response, {
    'prediction succeeds': (r) => r.status === 200,
    'probability is present': (r) => {
      if (r.status !== 200) return false;
      try {
        const p = r.json('probability');
        return typeof p === 'number' && p >= 0 && p <= 1;
      } catch (error) { return false; }
    },
  });
  sleep(1);
}

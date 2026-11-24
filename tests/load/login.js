// LZ11-NFR-01: proposed target, p95 GET /login under 1000 ms at 30 VUs.
// Run only against a local synthetic-data test instance.
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8000';

export const options = {
  vus: 30,
  duration: '1m',
  thresholds: {
    http_req_duration: ['p(95)<1000'],
    http_req_failed: ['rate<0.01'],
    checks: ['rate>0.99'],
  },
};

export default function () {
  const result = http.get(`${BASE_URL}/login`);
  check(result, {
    'login page responds 200': (r) => r.status === 200,
    'login form rendered': (r) => r.body.includes('name="csrf_token"'),
  });
  sleep(1);
}

// k6 load test — Forge Platform baseline
//
// Usage:
//   k6 run platform/scripts/loadtest.js                     # default 1m ramp
//   k6 run -e BASE=http://localhost:8000 -e VUS=50 -e DURATION=5m loadtest.js
//
// What this measures:
//   - p95 latency of /health (liveness) — sanity
//   - p95 latency of /ready (readiness, includes DB round-trip)
//   - p95 latency of /api/v1/projects/{slug}/status (auth + DB query)
//   - 5xx rate under sustained load
//
// What this does NOT yet cover (separate load tests, follow-ups):
//   - Orchestrate end-to-end (SLO-3: <120s p95 for simple feature task).
//     Needs fixture project + test Anthropic key + workspace infra ready.
//   - Ingest with large files (SLO-TBD).
//   - Concurrent orchestrate runs on same project (DB lock contention).
//
// Install k6: https://k6.io/docs/get-started/installation/
// No Python deps; k6 is a standalone binary.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ---------- Config via env ----------
const BASE = __ENV.BASE || 'http://localhost:8000';
const VUS = parseInt(__ENV.VUS || '20');
const DURATION = __ENV.DURATION || '1m';
const PROJECT_SLUG = __ENV.PROJECT_SLUG || '';  // optional: set to hit /status

// ---------- Custom metrics ----------
const errorRate = new Rate('errors');
const readyLatency = new Trend('ready_latency_ms', true);

// ---------- Stage plan ----------
export const options = {
  scenarios: {
    ramp_up: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '15s', target: VUS },     // ramp up
        { duration: DURATION, target: VUS },  // sustained
        { duration: '15s', target: 0 },       // ramp down
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    // SLO-1/2 adjacent guardrails — tune after measuring real baseline.
    'http_req_duration{route:health}': ['p(95)<100'],   // trivial endpoint
    'http_req_duration{route:ready}':  ['p(95)<300'],   // DB round-trip
    'errors': ['rate<0.01'],                            // <1% errors
    'http_req_failed': ['rate<0.02'],
  },
};

// ---------- Test flow ----------
export default function () {
  // 1. Liveness probe — must be effectively zero cost
  const r1 = http.get(`${BASE}/health`, { tags: { route: 'health' } });
  check(r1, {
    'health 200': (r) => r.status === 200,
    'health status ok': (r) => r.json('status') === 'ok',
  }) || errorRate.add(1);

  // 2. Readiness probe — includes DB + (optionally) Redis
  const r2 = http.get(`${BASE}/ready`, { tags: { route: 'ready' } });
  readyLatency.add(r2.timings.duration);
  check(r2, {
    'ready 200 or 503': (r) => r.status === 200 || r.status === 503,
    'ready has checks dict': (r) => r.json('checks') !== undefined,
  }) || errorRate.add(1);

  // 3. Optional: project status endpoint (measures auth + DB query path)
  if (PROJECT_SLUG) {
    const r3 = http.get(`${BASE}/api/v1/projects/${PROJECT_SLUG}/status`,
                        { tags: { route: 'project-status' } });
    check(r3, {
      'status 200 or 401/403': (r) => [200, 401, 403].includes(r.status),
    }) || errorRate.add(1);
  }

  sleep(1);
}

// ---------- Summary ----------
export function handleSummary(data) {
  // Minimal stdout summary; k6 writes the full JSON to stdout/file too.
  const metrics = data.metrics;
  const line = (name, m) => {
    if (!m) return '';
    const p95 = m.values && (m.values['p(95)'] || m.values.p95);
    const avg = m.values && m.values.avg;
    return `  ${name.padEnd(30)} avg=${(avg || 0).toFixed(1)}ms p95=${(p95 || 0).toFixed(1)}ms\n`;
  };
  let out = '\n--- Forge k6 load test summary ---\n';
  out += line('http_req_duration', metrics.http_req_duration);
  out += line('ready_latency_ms', metrics.ready_latency_ms);
  out += `\nTotal requests: ${metrics.http_reqs && metrics.http_reqs.values.count}\n`;
  out += `Failed requests: ${metrics.http_req_failed && (metrics.http_req_failed.values.rate * 100).toFixed(2)}%\n`;
  out += `Custom error rate: ${metrics.errors && (metrics.errors.values.rate * 100).toFixed(2)}%\n`;
  return {
    stdout: out,
    'loadtest-summary.json': JSON.stringify(data, null, 2),
  };
}

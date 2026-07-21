/**
 * Chỉ chạy phase cold-start burst (sau prepare-cold-start.sh)
 *   k6 run loadtest-cold.js
 */
import { Trend } from 'k6/metrics';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';
import { loadImage, postPredict, SUMMARY_TREND_STATS } from './lib/common.js';

const img = loadImage();
const coldVus = parseInt(__ENV.COLD_VUS || '10', 10);
const coldStartLatency = new Trend('cold_start_latency_ms', true);

export const options = {
  summaryTrendStats: SUMMARY_TREND_STATS,
  scenarios: {
    cold_start_burst: {
      executor: 'per-vu-iterations',
      vus: coldVus,
      iterations: 1,
      maxDuration: '5m',
      tags: { phase: 'cold_start' },
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.20'],
    'http_req_duration{phase:cold_start}': ['p(99)<120000'],
    cold_start_latency_ms: ['p(99)<120000'],
  },
};

export default function () {
  const res = postPredict(img, { phase: 'cold_start' });
  coldStartLatency.add(res.timings.duration);
}

export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const tag = __ENV.OUTPUT_TAG || 'cold';
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    [`results/k6-cold-${tag}-${timestamp}.json`]: JSON.stringify(data, null, 2),
    [`results/k6-cold-${tag}-latest.json`]: JSON.stringify(data, null, 2),
  };
}

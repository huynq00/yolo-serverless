/**
 * Smoke test nhanh — 1 VU, 1 phút (tương thích bản cũ)
 *   k6 run loadtest-smoke.js
 */
import { sleep } from 'k6';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';
import { loadImage, postPredict, SUMMARY_TREND_STATS } from './lib/common.js';

const img = loadImage();

export const options = {
  summaryTrendStats: SUMMARY_TREND_STATS,
  vus: 1,
  duration: '1m',
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(99)<120000'],
  },
};

export default function () {
  postPredict(img);
  sleep(1);
}

export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    [`results/k6-smoke-${timestamp}.json`]: JSON.stringify(data, null, 2),
    'results/k6-smoke-latest.json': JSON.stringify(data, null, 2),
  };
}

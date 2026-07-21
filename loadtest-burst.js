/**
 * Chỉ chạy phase burst traffic (pod đã warm)
 *   k6 run loadtest-burst.js
 */
import { sleep } from 'k6';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';
import { loadImage, postPredict, SUMMARY_TREND_STATS } from './lib/common.js';

const img = loadImage();
const burstTarget = parseInt(__ENV.BURST_VUS || '15', 10);

export const options = {
  summaryTrendStats: SUMMARY_TREND_STATS,
  scenarios: {
    traffic_burst: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '15s', target: burstTarget },
        { duration: '60s', target: burstTarget },
        { duration: '15s', target: 0 },
      ],
      tags: { phase: 'burst' },
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.10'],
    'http_req_duration{phase:burst}': ['p(99)<60000'],
  },
};

export default function () {
  postPredict(img, { phase: 'burst' });
  sleep(0.5);
}

export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
    [`results/k6-burst-${timestamp}.json`]: JSON.stringify(data, null, 2),
    'results/k6-burst-latest.json': JSON.stringify(data, null, 2),
  };
}

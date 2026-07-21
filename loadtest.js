/**
 * Benchmark đầy đủ: cold-start burst → traffic burst → warm steady
 *
 *   ./scripts/run-benchmark.sh
 *   k6 run loadtest.js
 */
import { sleep } from 'k6';
import { Trend } from 'k6/metrics';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';
import { loadImage, postPredict, SUMMARY_TREND_STATS } from './lib/common.js';

const img = loadImage();

const coldVus = parseInt(__ENV.COLD_VUS || '10', 10);
const burstTarget = parseInt(__ENV.BURST_VUS || '15', 10);
const warmVus = parseInt(__ENV.WARM_VUS || '5', 10);

const coldStartLatency = new Trend('cold_start_latency_ms', true);
const warmLatency = new Trend('warm_latency_ms', true);

export const options = {
  summaryTrendStats: SUMMARY_TREND_STATS,
  scenarios: {
    cold_start_burst: {
      executor: 'per-vu-iterations',
      vus: coldVus,
      iterations: 1,
      maxDuration: '5m',
      tags: { phase: 'cold_start' },
      exec: 'coldStartRequest',
    },
    traffic_burst: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '15s', target: burstTarget },
        { duration: '60s', target: burstTarget },
        { duration: '15s', target: 0 },
      ],
      startTime: '60s',
      tags: { phase: 'burst' },
      exec: 'burstRequest',
    },
    warm_steady: {
      executor: 'constant-vus',
      vus: warmVus,
      duration: '1m',
      startTime: '2m45s',
      tags: { phase: 'warm' },
      exec: 'warmRequest',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.10'],
    'http_req_duration{phase:cold_start}': ['p(99)<120000'],
    'http_req_duration{phase:burst}': ['p(99)<60000'],
    'http_req_duration{phase:warm}': ['p(99)<15000'],
    cold_start_latency_ms: ['p(99)<120000'],
    warm_latency_ms: ['p(99)<15000'],
  },
};

export function coldStartRequest() {
  const res = postPredict(img, { phase: 'cold_start' });
  coldStartLatency.add(res.timings.duration);
}

export function burstRequest() {
  postPredict(img, { phase: 'burst' });
  sleep(0.5);
}

export function warmRequest() {
  const res = postPredict(img, { phase: 'warm' });
  warmLatency.add(res.timings.duration);
  sleep(1);
}

export function handleSummary(data) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const report = buildPhaseReport(data);

  return {
    stdout: textSummary(data, { indent: ' ', enableColors: true }) + '\n\n' + report,
    [`results/k6-full-${timestamp}.json`]: JSON.stringify(data, null, 2),
    'results/k6-full-latest.json': JSON.stringify(data, null, 2),
    [`results/k6-full-${timestamp}.txt`]: report,
    'results/k6-full-latest.txt': report,
  };
}

function buildPhaseReport(data) {
  const lines = [
    '══════════════════════════════════════════════════',
    '  BÁO CÁO PHÂN TÍCH COLD-START / BURST / WARM',
    '══════════════════════════════════════════════════',
    '',
  ];

  for (const phase of ['cold_start', 'burst', 'warm']) {
    lines.push(formatPhaseMetrics(data, phase));
    lines.push('');
  }

  lines.push(formatNamedTrend(data, 'cold_start_latency_ms', 'COLD_START_LATENCY_MS'));
  lines.push(formatNamedTrend(data, 'warm_latency_ms', 'WARM_LATENCY_MS'));

  return lines.join('\n');
}

function formatPhaseMetrics(data, phase) {
  const durationKey = `http_req_duration{phase:${phase}}`;
  const metric = data.metrics[durationKey] || data.metrics.http_req_duration;
  const reqKey = Object.keys(data.metrics).find(
    (k) => k.startsWith('http_reqs') && k.includes(`phase:${phase}`),
  );
  const reqMetric = reqKey ? data.metrics[reqKey] : null;

  if (!metric || !metric.values) {
    return `[${phase}] Không có dữ liệu metric "${durationKey}"`;
  }

  const v = metric.values;
  const count =
    v.count ??
    reqMetric?.values?.count ??
    data.metrics.http_reqs?.values?.count ??
    'N/A';

  return [
    `── ${phase.toUpperCase()} ──`,
    `  count : ${count}`,
    `  avg   : ${fmtMs(v.avg)}`,
    `  med   : ${fmtMs(v.med)}`,
    `  p90   : ${fmtMs(v['p(90)'])}`,
    `  p95   : ${fmtMs(v['p(95)'])}`,
    `  p99   : ${fmtMs(v['p(99)'])}`,
    `  max   : ${fmtMs(v.max)}`,
  ].join('\n');
}

function formatNamedTrend(data, metricName, label) {
  const metric = data.metrics[metricName];
  if (!metric || !metric.values) {
    return `[${label}] Không có dữ liệu`;
  }
  const v = metric.values;
  return [
    `── ${label} ──`,
    `  count : ${v.count ?? 'N/A'}`,
    `  avg   : ${fmtMs(v.avg)}`,
    `  med   : ${fmtMs(v.med)}`,
    `  p90   : ${fmtMs(v['p(90)'])}`,
    `  p95   : ${fmtMs(v['p(95)'])}`,
    `  p99   : ${fmtMs(v['p(99)'])}`,
    `  max   : ${fmtMs(v.max)}`,
  ].join('\n');
}

function fmtMs(val) {
  if (val === undefined || val === null) return 'N/A';
  return `${(val / 1000).toFixed(2)}s`;
}

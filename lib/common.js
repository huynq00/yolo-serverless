import http from 'k6/http';
import { check } from 'k6';

export const BASE_URL =
  __ENV.BASE_URL ||
  'http://yolo-inference.default.127.0.0.1.sslip.io:8080/predict';

export const REQUEST_TIMEOUT = __ENV.TIMEOUT || '180s';

export const SUMMARY_TREND_STATS = [
  'avg',
  'min',
  'med',
  'max',
  'p(90)',
  'p(95)',
  'p(99)',
  'count',
];

export function loadImage() {
  return open('./test.jpg', 'b');
}

/**
 * POST /predict. extraTags được merge với scenario tags (vd. phase).
 */
export function postPredict(imageBytes, extraTags = {}) {
  const params = {
    timeout: REQUEST_TIMEOUT,
    tags: { name: 'predict', ...extraTags },
  };

  const res = http.post(BASE_URL, payload(imageBytes), params);

  if (res.status !== 200) {
    console.log(
      `[LỖI ${res.status}] url=${BASE_URL} body=${String(res.body || '').slice(0, 200)}`,
    );
  }

  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  return res;
}

function payload(imageBytes) {
  return {
    file: http.file(imageBytes, 'test.jpg', 'image/jpeg'),
  };
}

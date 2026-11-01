# API contracts · v1

Base URL in host development: `http://127.0.0.1:8001`. Browser uses `/api` Nginx prefix. API key: `X-API-Key` header when `API_TOKEN` is set. OpenAPI at `/docs` only in development.

All returned confidence values are raw softmax, not externally calibrated. No user text is returned or logged.

## `GET /health/live`
Response: `{"status":"alive"}`. Does not imply models are available.

## `GET /health/ready`
Returns 200 after **both** models are loaded and warmed; otherwise 503. Response 200: `{"status":"ready","tasks":["sentiment","topics"],"runtime":"onnxruntime-cpu"}`.

## `GET /v1/models`
Returns `{ "models": { "sentiment": {"model": "...", "revision":"<40 sha>", "labels":[...], "max_tokens":256, "runtime":"onnxruntime-cpu"}, "topics": {...} } }`.

## `POST /v1/sentiment`

Request:
```json
{"text":"ارسال محصول سریع بود و کیفیت خوبی داشت.","request_id":"optional-client-correlation-id"}
```
Response shape:
```json
{
  "task":"sentiment", "label":"positive", "label_fa":"مثبت", "confidence":0.88,
  "scores":[{"id":0,"label":"Negative","score":0.03},{"id":1,"label":"Neutral","score":0.09},{"id":2,"label":"Positive","score":0.88}],
  "model":"m3hrdadfi/albert-fa-base-v2-sentiment-multi", "revision":"<immutable SHA>",
  "runtime":"onnxruntime-cpu", "confidence_calibrated":false, "inference_ms":12.3,
  "request_id":"optional-client-correlation-id"
}
```
The values above are **illustrative**, not measured model output.

## `POST /v1/topics`
Uses the same request shape. The response has the same structure, with `task="topics"`, `label` (English slug), `label_fa` (original Persian model label), and 8 scores. `/v1/classify` is a compatibility alias, hidden from OpenAPI.

## `POST /v1/analyze`
Uses the same text request and returns `{request_id, sentiment: <prediction>, topics: <prediction>}`.

## `POST /v1/batch`
Request:
```json
{"task":"sentiment", "texts":["خیلی خوب بود", "دوست نداشتم"], "request_id":"batch-123"}
```
Response: `{request_id,task,count,results:[<prediction>,...]}`. `task` is `sentiment` or `topics`. Default maximum batch size 16, with per-text character and total-body limits.

## `GET /metrics`
Prometheus output. Requires API key when configured. Metrics exclude raw text.

## Errors

- 400 malformed `Content-Length`
- 401 missing/invalid API key
- 413 request body/text/batch exceeds configured limit
- 415 unsupported content type (handled by FastAPI)
- 422 invalid JSON/schema/empty text/invalid value
- 503 inference queue timeout, `Retry-After: 3`
- 500 internal inference failure, with no model internals or user input in the response

For upstream load balancing, send traffic only to services passing `/health/ready`; surface 503 to clients as retryable. There is no arbitrary model-upload endpoint or remote inference URL.

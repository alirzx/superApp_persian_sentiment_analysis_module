# SuperApp · Persian Sentiment Analysis & Topic Classification

Two independent Persian ALBERT classification models exposed through **one CPU-only FastAPI backend** and a separate **Persian RTL React/Nginx frontend**. Only **two long-running containers** (`api`, `ui`). The `model-setup` service is a **one-shot exporter/downloader**, not a long-running process. Normal `docker compose up --build -d` now requires it to finish successfully and verify both cached models before the API starts. Existing verified model artifacts are reused.

## Inference capabilities

| Task | Model | Original labels | Routes |
|---|---|---|---|
| Sentiment | [m3hrdadfi/albert-fa-base-v2-sentiment-multi](https://huggingface.co/m3hrdadfi/albert-fa-base-v2-sentiment-multi) | Negative, Neutral, Positive | `/v1/sentiment` |
| Topic classification | [m3hrdadfi/albert-fa-base-v2-clf-persiannews](https://huggingface.co/m3hrdadfi/albert-fa-base-v2-clf-persiannews) | 8 Persian news topics | `/v1/topics`, alias `/v1/classify` |

Additional endpoints: `/v1/analyze` runs both tasks, `/v1/batch` runs one task on a bounded list, `/v1/models` reports real cached revisions/labels, `/health/live`, `/health/ready`, `/metrics` (auth), and `/docs` in development.

**Scope:** These are pretrained news/review classifiers, not universal sentiment or document ontologies. Scores are raw softmax, **not calibrated probabilities**. The service does not claim reliable sarcasm, neutral text, mixed sentiment, or out-of-domain accuracy until tested on a Persian benchmark corpus.

## Quickstart (Docker Engine + Compose v2)

```bash
cp .env.example .env
make doctor
make build         # API, UI and one-shot setup image
make model         # downloads two pinned HF snapshots, exports ONNX, validates parity & hashes
make model-verify  # verifies existing cached artifacts offline
make up            # ONLY api + ui
make ps
make health
```

- Local UI (`.env.example`): `http://127.0.0.1:8082`
- Local API (`.env.example`): `http://127.0.0.1:8001`
- Development OpenAPI: `http://127.0.0.1:8001/docs`
- Production host ports (`.env.production.example`): `127.0.0.1:8002` (API), `127.0.0.1:8083` (UI). These are loopback endpoints, not public URLs.
- API inside Compose network: `http://api:8000`
- HTTP API is bound to loopback by default. Do not open ports on the public Internet without authenticated TLS ingress and rate limits.
- No inference runtime network access. Artifacts live on persistent Docker volume `superapp-persian-nlp_model_cache` and survive `docker compose down`; **do not use `down -v`** unless deliberately deleting the models.

### Example requests

```bash
curl -fsS http://127.0.0.1:8001/health/ready
curl -fsS http://127.0.0.1:8001/v1/models -H "X-API-Key: $API_TOKEN"
curl -fsS http://127.0.0.1:8001/v1/sentiment -H "X-API-Key: $API_TOKEN" \
  -H 'Content-Type: application/json' -d '{"text":"این کتاب عالی بود."}'
curl -fsS http://127.0.0.1:8001/v1/topics -H "X-API-Key: $API_TOKEN" \
  -H 'Content-Type: application/json' -d '{"text":"پژوهشگران دستاورد جدیدی در فناوری معرفی کردند."}'
curl -fsS http://127.0.0.1:8001/v1/analyze -H "X-API-Key: $API_TOKEN" \
  -H 'Content-Type: application/json' -d '{"text":"این مقاله علمی مفید است."}'
```

The UI proxies `/api/` to FastAPI and adds `X-API-Key` inside Nginx; **this does not authenticate human users**. Use OIDC/SSO or equivalent at the perimeter before exposing UI externally.

## Architecture

```text
Browser -- Persian RTL React --> Nginx :8080 ------------------------+
                                   | /api/ + private X-API-Key       |
                                   v                                 |
                              FastAPI :8000                          |
                                   |                                 |
                         admission/validation                        |
                                   |                                 |
                         Persian normalization                      |
                                   |                                 |
                    +--------------+--------------+                  |
                    |                             |                  |
              Sentiment ALBERT               Topic ALBERT             |
                 CPU ONNX                      CPU ONNX               |
                    |                             |                  |
                    +--------- softmax + labels --+                  |
                                   |                                 |
                              JSON response <------------------------+
model-setup (one-shot): HF snapshot -> original PyTorch -> ONNX FP32
                         -> parity test -> SHA256 manifest -> Docker volume
```

The API never downloads weights, loads untrusted remote Python code, or initializes a PyTorch model. The one-shot setup container is isolated from the long-running services. Its PyTorch weight-loading step still has a supply-chain trust boundary because upstream provides `.bin`/pickle weights; see [model provenance](docs/MODEL_PROVENANCE.md).

## One-time model preparation & reproducibility

- The project configuration is [`models.json`](models.json).
- `revision: main` is accepted for the **first** development download only. The setup script resolves the Hub revision to a **40-character immutable commit** and stores that exact revision and SHA256 file hashes in `/models/{task}/manifest.json`. Subsequent `make model` calls **do not refetch/update** a valid cached model.
- For deployments, copy the two immutable SHA values from the manifests into `.env` as `MODEL_SENTIMENT_REVISION` and `MODEL_TOPICS_REVISION`, and preserve the volume or distribute audited artifacts. Runtime refuses a different revision or tampered artifact.
- `make model-refresh` is an **explicit** opt-in to update a model when a floating revision is used. Benchmark the updated artifact and compare the labels/quality before deploying.
- ONNX FP32 is the baseline. INT8 is deliberately **not** shipped until calibration and accuracy tests exist.

## Production caveats

This source has been validated with unit tests using a fake inference engine. **Real model download, ONNX conversion and CPU performance have not been validated in this artifact environment.** Server hardware, memory, networking, model permission, and actual HF availability must be checked before approval.

- Set `APP_ENV=production` and a 32+ character random `API_TOKEN` (recommended `openssl rand -hex 32`). The token must contain alphanumeric, underscore, or hyphen characters so it can be inserted safely into Nginx config.
- Apply authenticated TLS ingress, user-specific rate limits, upload/body limits, monitoring, secrets distribution, and host-level firewalling.
- `.gitlab-ci.yml` follows Module 01's shell-runner tags (`linux`, `bina`, `shell`), SSH variable names, and `master` manual deployment branch. `RUN_SERVICES=0` by default so builds **do not** automatically start models without server memory testing.
- Build and run model-setup first, then start only API and UI. Start with one worker, 2 CPU threads, 1 simultaneous inference, 1.2 GB API memory cap (UNVERIFIED capacity starting point), then benchmark P50/P95 and peak RSS.
- Model licenses on Hugging Face say Apache-2.0; commercial release requires review of weights, training data, and third-party licenses.

See [`docs/ENV_CONFIGURATION.md`](docs/ENV_CONFIGURATION.md), [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), [`docs/API.md`](docs/API.md), [`docs/MODEL_PROVENANCE.md`](docs/MODEL_PROVENANCE.md), [`docs/SECURITY.md`](docs/SECURITY.md), and [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md).


### Build mirrors and LAN/VPN service access

Python runtime and setup dependencies use Liara PyPI with Chabokan fallback (configurable pip retries/timeouts); only the CPU-specific torch wheel is downloaded from PyTorch's official CPU index. npm dependencies use Liara's npm registry, and Nginx's Alpine `gettext` uses Liara's Alpine repository. Hugging Face downloads of the original models still need network on first setup.

For a **trusted LAN/VPN-only** deployment, set `UI_BIND_IP=0.0.0.0` and `UI_PORT=8083` in the private GitLab `ENV_FILE`, while leaving `API_BIND_IP=127.0.0.1` / `API_PORT=8002`. This permits connections on both the server LAN and VPN interface addresses (subject to routing/firewall). Restrict TCP 8083 to trusted clients and provide human authentication where needed. The browser uses relative `/api` calls via Nginx; no direct API exposure is needed. See `docs/ENV_CONFIGURATION.md` for the full configuration.

# Environment configuration: development and production

The GitLab commits `dc991bd` and `7221230` changed **Compose fallback** host ports
from `8001/8082` to `8002/8083`. Explicit values in `.env` override these defaults.
The **local** `.env.example` intentionally retains `8001/8082`; the **production**
`.env.production.example` uses the new `8002/8083`. All container-facing ports
remain `8000` for FastAPI and `8080` for Nginx.

## Local development

```bash
cp .env.example .env
# Verify resolved ports: docker compose config --format json
make doctor
make build
make model
make model-verify
make up
```

For local-only development, `APP_ENV=development` and empty `API_TOKEN` are
allowed. Both services bind to 127.0.0.1 by default. On the machine that runs
Docker, browse UI `http://127.0.0.1:8082`, API `http://127.0.0.1:8001`.

## Production on the company server

Copy `.env.production.example` to a private local configuration file. Set
`APP_ENV=production`, replace the **empty** `API_TOKEN` with a unique token
created by `openssl rand -hex 32`, and set file mode `0600`. Use the same
value for the API and UI (Compose injects it into both). Do not commit the
real `.env` or paste it in CI logs. The company default host ports are
`127.0.0.1:8002` for API and `127.0.0.1:8083` for UI. Access through an
authenticated TLS reverse proxy; UI's Nginx proxy injects the shared API key
and **does not itself authenticate users**.

`MODEL_SENTIMENT_REVISION=main` and `MODEL_TOPICS_REVISION=main` are valid
**bootstrap settings**: the first one-shot model setup resolves and records
immutable Hub commit SHAs and hashes. For the final approved release, replace
those `main` values with the exact SHA values from the installed
`manifest.json` files and re-verify. Do not guess either SHA.

## All user-configurable variables

| Variable | Local | Production starting value | Meaning |
|---|---|---|---|
| `APP_ENV` | `development` | `production` | Production requires a nonempty 32+ character API token and disables Swagger |
| `API_TOKEN` | empty | privately generated | Shared `X-API-Key` secret for service-to-service access |
| `API_BIND_IP` | `127.0.0.1` | `127.0.0.1` | API host bind; do not use 0.0.0.0 without secured ingress |
| `API_PORT` | `8001` | `8002` | Host port to internal API :8000 |
| `UI_BIND_IP` | `127.0.0.1` | `127.0.0.1` | UI host bind |
| `UI_PORT` | `8082` | `8083` | Host port to internal Nginx :8080 |
| `PIP_PRIMARY_INDEX_URL` | Liara mirror | Liara mirror | Python package build index |
| `PIP_FALLBACK_INDEX_URL` | Chabokan mirror | Chabokan mirror | Fallback package build index |
| `MODEL_SENTIMENT_REVISION` | `main` initially | exact SHA after model setup | Source revision of sentiment checkpoint |
| `MODEL_TOPICS_REVISION` | `main` initially | exact SHA after model setup | Source revision of topic checkpoint |
| `CPU_THREADS` | `2` | `2` initially | ONNX CPU intra-op threads |
| `MAX_CONCURRENT_INFERENCE` | `1` | `1` initially | CPU admission semaphore |
| `MAX_QUEUE_WAIT_SECONDS` | `10` | `10` | Admission timeout |
| `MAX_TEXT_CHARS` | `5000` | `5000` | Request text limit |
| `MAX_BATCH_ITEMS` | `16` | `16` | Maximum batch item count |
| `MAX_REQUEST_BYTES` | `65536` | `65536` | JSON request-size limit |
| `API_CPUS` | `2.0` | `2.0` initially | API CPU limit |
| `API_MEMORY` | `1200m` | `1200m` initially | API cgroup RAM cap, must benchmark |
| `UI_CPUS` | `0.5` | `0.5` | UI CPU limit |
| `UI_MEMORY` | `256m` | `256m` | UI RAM cap |
| `SETUP_CPUS` | `3.0` | `3.0` | One-shot model exporter CPU limit |
| `SETUP_MEMORY` | `4g` | `4g` initially | One-shot exporter RAM cap, benchmark required |
| `ENABLE_METRICS` | `true` | `true` | Authenticated Prometheus endpoint |

Additional service-internal settings (`MODEL_DIR`, `MODELS_CONFIG`, `HF_HOME`,
thread caps) are fixed in `docker-compose.yml` and need not be duplicated in
the host `.env`. Do not put Markdown-style links (`[url](url)`) or starred
Markdown comments in a real `.env`; values must be plain strings.

## GitLab CI/CD variables (NOT Docker `.env` variables)

| Name | Type | Notes |
|---|---|---|
| `SSH_USER` | CI variable | Dedicated deploy user with access to server checkout |
| `SSH_PORT` | CI variable | Actual SSH port, no assumed default |
| `VM_IPADDRESS` | CI variable | Server host/IP, must be supplied by operator |
| `SSH_PRIVATE_KEY` | **File** CI variable | Private deployment key, masked/protected as supported |
| `SSH_KNOWN_HOSTS` | **File** CI variable | Preverified host fingerprint; do not use ssh-keyscan in pipeline |
| `ENV_FILE` | **File** CI variable | Full production `.env`, including real API_TOKEN, not committed |
| `DEPLOY_DIR` | CI variable (optional) | Defaults to `/opt/apps/ai-service/persian_sentiment_topic_analysis_module`; verify server checkout |
| `RUN_SERVICES` | CI variable (optional) | `0` builds only, `1` prepares weights, verifies, and starts |

The canonical pipeline is `.gitlab-ci.yml`; `.gitlab-ci-prod.yml` includes it
for GitLab projects configured to use a custom CI file path. Only one pipeline
is defined. CI deploy remains **manual** and restricted to `master`. If GitLab
CI uses a deployment path other than the default, override `DEPLOY_DIR`.

## Required checks

```bash
docker compose config --quiet
docker compose config --format json | python3 -c 'import json,sys; s=json.load(sys.stdin)["services"]; [print(k, s[k]["ports"]) for k in ["api","ui"]]'
git status --short
```

Model `main` revisions must be pinned and CPU quality/performance tested before
production approval. The one-shot setup first requires network access to the
PyTorch CPU wheel, dependency indexes, and Hugging Face. The long-running API
needs only the verified offline model volume.

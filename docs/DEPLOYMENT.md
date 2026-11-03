# Operations and deployment

## Local CPU / Ubuntu

```bash
cp .env.example .env
make doctor
make build
make model
make model-verify
make up
make ps
make health
docker compose logs --tail=100 api ui
```

Model setup is **one-shot**. The API container has no `torch` and no Hub dependency. The model-setup dependency now runs before the API on normal Compose startup. `make up` uses `--no-build`, so build the three images before using it; an already valid model cache is reused. The persistent named model volume survives ordinary restarts or `docker compose down`. **Never run `docker compose down -v` on a production instance unless removing all cached models is intended.**

If model preparation fails during ONNX export, the installed artifact is not replaced. The setup image and original checkpoint need network for first setup; API inference requires no network.

## Production server

1. Prepare private GitLab checkout: `/opt/apps/ai-service/persian_sentiment_topic_analysis_module` (`origin/master`), Docker Compose v2, enough disk to build the temporary PyTorch exporter, CPU with supported ONNX instructions, and available RAM. Confirm actual capacity before deployment.
2. Write `.env` using `.env.production.example` **on the server**. Do not use the empty sample token. `APP_ENV=production`, secure `API_TOKEN` (recommended `openssl rand -hex 32`), loopback binds and nonconflicting host ports.
3. Deploy signed/authenticated TLS ingress with OIDC/SSO and user rate limiting before any external access. Nginx's shared token only authenticates the API proxy, not end users.
4. Build images: `docker compose build api ui` and `docker compose --profile setup build model-setup`.
5. Download/export models once: `docker compose --profile setup run --rm --no-deps model-setup`.
6. Verify cached artifacts: `docker compose --profile setup run --rm --no-deps model-setup python -m scripts.prepare_models --verify-only`.
7. Copy immutable 40-character SHAs from `/models/{task}/manifest.json` into `.env` for `MODEL_*_REVISION` and regenerate production deployment configuration. Set values before production restart and re-verify.
8. Start: `docker compose up -d --no-build --wait --wait-timeout 180 api ui`. Check `docker compose ps`, `docker compose logs --tail=100 api ui`, `/health/ready`, and real requests for each model and combined analysis.
9. Record CPU/RAM/P50/P95/RSS and classification accuracy before allowing production traffic. Tune `CPU_THREADS`, `MAX_CONCURRENT_INFERENCE`, `API_MEMORY`, `MAX_BATCH_ITEMS` based on recorded measurements.
10. Back up exact image versions, complete immutable model artifacts and manifests, deployment `.env` held separately, and a rollback plan. Review model license and artifacts before commercial approval.

## GitLab CI/CD

The newly added `.gitlab-ci-prod.yml` is a compatibility entrypoint which includes the **single canonical** `.gitlab-ci.yml` pipeline. This avoids conflicting deploy jobs. Review `docs/ENV_CONFIGURATION.md` for the company server port and CI variable mapping.


`.gitlab-ci.yml` uses runner tags `linux,bina,shell`, `origin/master`, and manual SSH deployment following Module 01. Provision GitLab CI/CD variables `SSH_USER`, `SSH_PORT`, `VM_IPADDRESS` (ordinary), `SSH_PRIVATE_KEY`, `SSH_KNOWN_HOSTS`, `ENV_FILE` (file variables). The manual job copies the env file, fast-forwards the existing server checkout, builds images, and only downloads models/starts services if `RUN_SERVICES=1`. This is a safety gate until runtime performance is confirmed.

The GitLab pipeline includes source validation, Python unit tests, React build, and manually triggered Docker build. Runner must have Python 3.11, Node 22/npm, Docker Compose and network to dependency mirrors for these jobs. Image registry publishing and immutable digest-based rollbacks are recommended next steps, not currently implemented.

## Networking & security

Local `.env.example`: API `127.0.0.1:8001`, UI `127.0.0.1:8082`. Company server `.env.production.example`: API `127.0.0.1:8002`, UI `127.0.0.1:8083`. Compose fallbacks without `.env` are now 8002/8083. Internally api port 8000 and UI port 8080 over private Compose network. Do not bind either service to `0.0.0.0` for a public launch before hardened ingress and access controls are installed.

## Evaluation/release gates

- [ ] Both HF original repository revisions and weight hashes recorded and approved.
- [ ] Explicit model setup exports and validates two ONNX models successfully.
- [ ] Two load-once warmed CPU sessions; no runtime Hub calls.
- [ ] Sentiment three labels and Persian News eight labels map correctly to real logits.
- [ ] Real Persian samples evaluated across domains, sarcasm, negation, ZWNJ, OCR/STT noise and long texts.
- [ ] Peak RAM and P50/P95 measured for concurrency 1,2,4 under realistic host contention.
- [ ] Batch/queue failure and 503 response behavior verified under load.
- [ ] Public UI protected by authenticated TLS ingress, per-user quotas and abuse controls.
- [ ] Signed/offline model artifact retention and rollback strategy approved.

## Incident fix: missing model manifest

If API startup fails with `/models/sentiment/manifest.json` missing, the
shared `model_cache` volume was not successfully populated. An API image
build never downloads the model weights by itself. On the company server,
`docker compose up --build -d` now builds and runs the one-shot
`model-setup` prerequisite before starting API. It verifies and reuses
both existing model artifacts or downloads/exports missing ones.

```bash
# From the server checkout; keep the existing .env and project name.
docker compose config --quiet
docker compose config --format json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["name"]); print({k:d["services"][k].get("volumes") for k in ("api","model-setup")})'
docker compose up --build -d
docker compose ps -a
docker compose logs --tail=150 model-setup api ui
# Verify the two artifacts in the SAME persistent volume:
docker compose run --rm --no-deps model-setup python -m scripts.prepare_models --verify-only
```

Do not create an empty placeholder manifest or delete the cache using
`docker compose down -v`. The initial setup requires Hugging Face access,
CPU PyTorch/ONNX export dependencies, temporary disk space and sufficient RAM.
If setup cannot reach the model Hub, no application startup is attempted.
The original GitLab CI script is deliberately unchanged by this incident fix.

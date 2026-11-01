# Security and privacy boundaries

- API token `X-API-Key` uses constant-time comparison. Token is never embedded in the browser bundle. Production config requires >=32 characters. Nginx startup validates its character set to avoid configuration injection.
- Browser-facing Nginx adds the shared token to all `/api` requests. **No user authentication exists in the UI**. Restrict ingress to authenticated HTTPS + rate limiting and authorize tenants outside this service.
- Default host bindings are loopback. `api` is read-only/unprivileged, with dropped Linux capabilities, tmpfs scratch storage, controlled CPU/PIDs/RAM, one Uvicorn worker, no network-needed inference. Do not mount writable host directories or Docker socket.
- Input JSON is bounded (MAX_REQUEST_BYTES), UTF-8 text is validated (MAX_TEXT_CHARS), batching is bounded (MAX_BATCH_ITEMS), and a CPU semaphore enforces admission. Put stricter body, per-user, and upstream timeout controls on the ingress.
- Raw text content is not stored, returned, or logged by the service; `uvicorn --no-access-log` avoids accidental endpoint metadata logging. Reverse proxies, observability tools, and browser histories have independent policies to audit.
- The model-setup stage downloads source checkpoint files from Hugging Face, including PyTorch pickle `.bin` files. Run this one-shot setup under restricted permissions, review publisher, pin SHA, and avoid sensitive credentials. `trust_remote_code=False` does not eliminate pickle risk. The API loads only verified ONNX + tokenizer/config artifacts.
- Check labels from model's config and fail closed on mismatch. Verify all installed files with SHA256 before loading. Re-running setup does not mutate verified artifacts without explicit `--refresh`.
- No user-provided model IDs, arbitrary task import, unrestricted batch sizes, cloud LLM provider, or model downloads from API endpoints.
- `/docs` is disabled in production. `/metrics` is protected by API token; liveness/readiness are intentionally unauthenticated for the container orchestrator.
- The API is not a multi-tenant product gateway or calibrated high-stakes decision engine. Avoid using predictions for consequential automated decisions without independent evaluation and human review.

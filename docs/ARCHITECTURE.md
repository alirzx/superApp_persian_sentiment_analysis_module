# Architecture and boundaries

## Containers

`api`: Python 3.11-slim, FastAPI, numpy, ONNX Runtime CPU, tokenizers/Transformers (tokenizer only), no PyTorch and no runtime Hub access. One Uvicorn worker so ONNX sessions are not duplicated in memory. Load both models at process startup, verify every installed file, check labels, warm up, then mark ready. `/health/live` and `/health/ready` are intentionally separate. No UI framework on the backend.

`ui`: React 18 + Vite TypeScript browser bundle served by Nginx on internal port 8080. Nginx strips `/api` prefix and inserts a server-side shared token for FastAPI. Browser bundles do not contain the token. Nginx reverse proxy **is not** identity authentication.

`model-setup`: one-shot startup prerequisite of `api` (Compose `service_completed_successfully`); downloads original task-specific checkpoints, exports ONNX with torch in a separate image, validates ONNX against PyTorch numerically, writes immutable SHA manifest, and atomically installs to the named volume. `make model` skips installed verified artifacts. `make model-refresh` updates only when requested.

## Request paths

`/v1/sentiment`, `/v1/topics` and `/v1/analyze` accept `{text,request_id?}`. `/v1/batch` accepts `{task,texts,request_id?}`. No generic arbitrary `task` model loading or user-supplied model repository. Maximum character length, JSON request bytes, and batch item counts are independently controlled.

Normalized text preserves negation, punctuation, emoji, digits, and Persian ZWNJ. Only Arabic/Persian letters and unnecessary whitespace/control formatting are safely adjusted. Token truncation is enforced by the checkpoint-specific SentencePiece tokenizer, with 256-token starting cap. **A truncated text may change the meaning**, particularly for long reviews, so length should be exposed to client before accepting long documents in a future version.

Postprocessing reads the `id2label` ordering from the actual verified upstream config and requires an exact match with `models.json`. It applies softmax, returns per-label scores and `confidence_calibrated=false`. Persian class labels are preserved for topics. No implicit remapping between recommendation labels and sentiment polarity.

## CPU resource management

`CPU_THREADS=2`, `MAX_CONCURRENT_INFERENCE=1`, one worker, 1.2g API memory cap are *starting settings*, not measured target hardware capacities. A bounded single semaphore spans model inference. Queue wait timeout generates 503 with `Retry-After`. The API includes Prometheus histogram timings per task; raw texts and request bodies are not logged. API binds to loopback by default, Compose bridge network is private, tmpfs + read-only runtime are used.

## Shared-runtime strategy

The two task-specific models are independently replaceable. Both share admission controls and the API process, reducing operational overhead while keeping per-task model IDs, revisions, labels, tokenizers, tests, and endpoints. A third model (zero-shot) is intentionally out of scope for MVP due additional RAM/CPU requirements.

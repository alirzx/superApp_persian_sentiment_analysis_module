"""Authenticated CPU inference with bounded admission, no text-body logging."""
from __future__ import annotations
import asyncio
import hmac
import logging
import uuid
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Callable

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from .config import Settings
from .inference import NLPInferenceEngine
from .schemas import TextRequest, BatchRequest

LOG = logging.getLogger("superapp.persian_nlp")
CALLS = Counter("superapp_nlp_requests_total", "NLP inference request count", ["task", "status"])
DURATION = Histogram("superapp_nlp_request_seconds", "NLP request processing seconds", ["task"])


def create_app(*, settings: Settings | None = None, engine_factory: Callable | None = None):
    settings = settings or Settings.from_env()
    settings.validate()
    factory = engine_factory or NLPInferenceEngine

    @asynccontextmanager
    async def lifespan(app):
        app.state.engine = await run_in_threadpool(factory, settings)
        await run_in_threadpool(app.state.engine.warmup)
        app.state.semaphore = asyncio.Semaphore(settings.max_concurrent_inference)
        yield
        app.state.engine = None

    app = FastAPI(title="SuperApp Persian NLP", version="1.0.0",
                  docs_url="/docs" if settings.environment != "production" and settings.enable_docs else None,
                  redoc_url=None, lifespan=lifespan)

    @app.middleware("http")
    async def request_bound(req: Request, call_next):
        if req.method in {"POST", "PUT", "PATCH"}:
            length = req.headers.get("content-length")
            if length is not None:
                try:
                    value = int(length)
                except ValueError:
                    return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
                if value < 0 or value > settings.max_request_bytes:
                    return JSONResponse({"detail": "Request too large"}, status_code=413)
            # ASGI receive wrapper also covers chunked bodies without Content-Length.
            consumed = 0
            original = req._receive
            async def bounded_receive():
                nonlocal consumed
                message = await original()
                consumed += len(message.get("body", b""))
                if consumed > settings.max_request_bytes:
                    raise HTTPException(status_code=413, detail="Request too large")
                return message
            req._receive = bounded_receive
        response = await call_next(req)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def authorize(x_api_key: str | None = Header(default=None)):
        if settings.api_token and not hmac.compare_digest(x_api_key or "", settings.api_token):
            raise HTTPException(401, "Invalid API key")

    def validate_text(text: str):
        if len(text) > settings.max_text_chars:
            raise HTTPException(413, "Text exceeds MAX_TEXT_CHARS")

    async def execute(task: str, texts: list[str]):
        started = perf_counter()
        semaphore = app.state.semaphore
        try:
            await asyncio.wait_for(semaphore.acquire(), timeout=settings.max_queue_wait_seconds)
        except asyncio.TimeoutError as exc:
            CALLS.labels(task, "busy").inc()
            raise HTTPException(status_code=503, detail="Inference capacity exhausted", headers={"Retry-After": "3"}) from exc
        try:
            result = await run_in_threadpool(app.state.engine.predict_many, task, texts)
            CALLS.labels(task, "ok").inc()
            return result
        except ValueError as exc:
            CALLS.labels(task, "invalid").inc()
            raise HTTPException(status_code=422, detail="Invalid text input") from exc
        except Exception as exc:
            CALLS.labels(task, "failed").inc()
            LOG.error("Inference failed for task=%s: %s", task, type(exc).__name__)
            raise HTTPException(status_code=500, detail="Inference failed") from exc
        finally:
            semaphore.release()
            DURATION.labels(task).observe(perf_counter() - started)

    @app.get("/health/live")
    async def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    async def ready():
        if not getattr(getattr(app.state, "engine", None), "warmed_up", False):
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return {"status": "ready", "tasks": ["sentiment", "topics"], "runtime": "onnxruntime-cpu"}

    @app.get("/v1/models", dependencies=[Depends(authorize)])
    async def models():
        return {"models": app.state.engine.metadata()}

    @app.post("/v1/sentiment", dependencies=[Depends(authorize)])
    async def sentiment(data: TextRequest):
        validate_text(data.text)
        result = (await execute("sentiment", [data.text]))[0]
        return {**result, "request_id": data.request_id or str(uuid.uuid4())}

    @app.post("/v1/topics", dependencies=[Depends(authorize)])
    @app.post("/v1/classify", dependencies=[Depends(authorize)], include_in_schema=False)
    async def topics(data: TextRequest):
        validate_text(data.text)
        result = (await execute("topics", [data.text]))[0]
        return {**result, "request_id": data.request_id or str(uuid.uuid4())}

    @app.post("/v1/analyze", dependencies=[Depends(authorize)])
    async def analyze(data: TextRequest):
        validate_text(data.text)
        # One queue admission per task, predictable CPU limits.
        sentiment_res = (await execute("sentiment", [data.text]))[0]
        topic_res = (await execute("topics", [data.text]))[0]
        return {"request_id": data.request_id or str(uuid.uuid4()),
                "sentiment": sentiment_res, "topics": topic_res}

    @app.post("/v1/batch", dependencies=[Depends(authorize)])
    async def batch(data: BatchRequest):
        if len(data.texts) > settings.max_batch_items:
            raise HTTPException(413, "Batch exceeds MAX_BATCH_ITEMS")
        for item in data.texts:
            validate_text(item)
        values = await execute(data.task, data.texts)
        return {"request_id": data.request_id or str(uuid.uuid4()), "task": data.task,
                "count": len(values), "results": values}

    @app.get("/metrics", dependencies=[Depends(authorize)])
    async def metrics():
        if not settings.enable_metrics:
            raise HTTPException(404)
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app

app = create_app()

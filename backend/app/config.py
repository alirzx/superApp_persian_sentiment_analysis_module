"""Config-driven service, no secret or model file embedded in source."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Settings:
    environment: str = "development"
    api_token: str = ""
    model_dir: Path = Path("/models")
    models_config: Path = Path("/app/models.json")
    cpu_threads: int = 2
    max_concurrent_inference: int = 1
    max_queue_wait_seconds: float = 10.0
    max_text_chars: int = 5000
    max_batch_items: int = 16
    max_request_bytes: int = 65536
    enable_metrics: bool = True
    enable_docs: bool = True

    @classmethod
    def from_env(cls):
        def integer(name: str, default: int):
            return int(os.getenv(name, str(default)))
        result = cls(
            environment=os.getenv("APP_ENV", "development").lower(),
            api_token=os.getenv("API_TOKEN", ""),
            model_dir=Path(os.getenv("MODEL_DIR", "/models")),
            models_config=Path(os.getenv("MODELS_CONFIG", "/app/models.json")),
            cpu_threads=integer("CPU_THREADS", 2),
            max_concurrent_inference=integer("MAX_CONCURRENT_INFERENCE", 1),
            max_queue_wait_seconds=float(os.getenv("MAX_QUEUE_WAIT_SECONDS", "10")),
            max_text_chars=integer("MAX_TEXT_CHARS", 5000),
            max_batch_items=integer("MAX_BATCH_ITEMS", 16),
            max_request_bytes=integer("MAX_REQUEST_BYTES", 65536),
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true",
            enable_docs=os.getenv("ENABLE_DOCS", "true").lower() == "true",
        )
        result.validate()
        return result

    def validate(self):
        if self.environment not in {"development", "production", "test"}:
            raise ValueError("APP_ENV must be development, production or test")
        if self.environment == "production" and len(self.api_token) < 32:
            raise ValueError("Production requires API_TOKEN of >=32 characters")
        if not (1 <= self.cpu_threads <= 64 and 1 <= self.max_concurrent_inference <= 32):
            raise ValueError("Invalid CPU/concurrency settings")
        if self.max_queue_wait_seconds <= 0 or not (32 <= self.max_text_chars <= 100000):
            raise ValueError("Invalid queue/text limits")
        if not (1 <= self.max_batch_items <= 128 and 1024 <= self.max_request_bytes <= 5000000):
            raise ValueError("Invalid batch/request limits")

    def models(self) -> dict:
        result = json.loads(self.models_config.read_text(encoding="utf-8"))
        if set(result) != {"sentiment", "topics"}:
            raise ValueError("models.json must define sentiment and topics")
        for task, item in result.items():
            revision_override = os.getenv(f"MODEL_{task.upper()}_REVISION")
            if revision_override:
                item["revision"] = revision_override
            if not item.get("repo") or not item.get("expected_labels") or not (8 <= item.get("max_tokens", 0) <= 512):
                raise ValueError("Invalid model spec")
        return result

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app

class FakeEngine:
    def __init__(self, settings):
        self.warmed_up = False
        self.labels = {"sentiment": ["Negative", "Neutral", "Positive"],
                       "topics": ["اجتماعی", "اقتصادی", "بین الملل", "سیاسی", "علمی فناوری", "فرهنگی هنری", "ورزشی", "پزشکی"]}
    def warmup(self):
        self.warmed_up = True
    def predict_many(self, task, texts):
        from app.preprocessing import normalize_text
        from app.postprocessing import make_prediction
        result = []
        for text in texts:
            normalized = normalize_text(text)
            logits = [0, 0, 4] if task == "sentiment" else [0, 3, 0, 0, 0, 0, 0, 0]
            p = make_prediction(task, logits, self.labels[task], {"repo": f"test/{task}", "revision": "a" * 40})
            result.append({**p, "inference_ms": 1.2, "length_normalized": len(normalized)})
        return result
    def metadata(self):
        return {k: {"model": f"test/{k}", "revision": "a" * 40,
                    "labels": v, "max_tokens": 256, "runtime": "onnxruntime-cpu"}
                for k,v in self.labels.items()}

@pytest.fixture
def client():
    settings = Settings(environment="test", api_token="secret", max_text_chars=1000,
                        max_batch_items=4, max_request_bytes=2048,
                        model_dir=Path("/unused"), models_config=Path("/unused"))
    with TestClient(create_app(settings=settings, engine_factory=FakeEngine)) as c:
        yield c

@pytest.fixture
def headers():
    return {"X-API-Key": "secret"}

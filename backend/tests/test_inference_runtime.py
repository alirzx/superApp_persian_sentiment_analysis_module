"""Network-free classifier inference contract using stub tokenizer and ONNX session.

Actual checkpoint conversion, numerical parity and latency require live integration tests.
"""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from app.inference import Classifier

class FakeTokenizer:
    @classmethod
    def from_pretrained(cls, path, **kwargs):
        assert kwargs["local_files_only"] and not kwargs["trust_remote_code"]
        return cls()
    def __call__(self, texts, *, return_tensors, padding, truncation, max_length):
        assert return_tensors == "np" and padding and truncation and max_length == 256
        return {name: np.ones((len(texts), 4), dtype=np.int64)
                for name in ("input_ids", "attention_mask", "token_type_ids")}

class FakeSession:
    def __init__(self, path, *, sess_options, providers):
        assert Path(path).is_file() and providers == ["CPUExecutionProvider"]
    def get_providers(self):
        return ["CPUExecutionProvider"]
    def get_inputs(self):
        return [SimpleNamespace(name=n) for n in ("input_ids", "attention_mask", "token_type_ids")]
    def get_outputs(self):
        return [SimpleNamespace(name="logits")]
    def run(self, outputs, feed):
        assert feed["input_ids"].dtype == np.int64
        return [np.tile(np.array([[0, 0, 8]], dtype=np.float32),
                        (feed["input_ids"].shape[0], 1))]

def test_predict_and_warmup_cpu_only(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoTokenizer=FakeTokenizer))
    monkeypatch.setitem(sys.modules, "onnxruntime", SimpleNamespace(
        SessionOptions=lambda: SimpleNamespace(),
        ExecutionMode=SimpleNamespace(ORT_SEQUENTIAL=0),
        GraphOptimizationLevel=SimpleNamespace(ORT_ENABLE_ALL=1),
        InferenceSession=FakeSession))
    folder = tmp_path / "sentiment"
    folder.mkdir()
    for name, data in (
        ("model.onnx", b"fake-onnx"),
        ("spiece.model", b"fake-spiece"),
        ("config.json", json.dumps({"id2label": {
            "0":"Negative", "1":"Neutral", "2":"Positive"}}).encode()),
    ):
        (folder / name).write_bytes(data)
    hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in folder.iterdir()}
    spec = {"repo":"test/albert", "revision":"main",
            "expected_labels":["Negative", "Neutral", "Positive"], "max_tokens":256}
    (folder / "manifest.json").write_text(json.dumps({
        "repo":spec["repo"], "revision":"a"*40, "format":"onnx-fp32", "sha256":hashes}))
    model = Classifier(folder, spec, threads=2)
    model.warmup("sentiment")
    assert model.ready
    outputs = model.predict_many("sentiment", ["خیلی خوب", "خبر خوب"])
    assert len(outputs) == 2
    assert all(r["label"] == "positive" and r["label_fa"] == "مثبت" for r in outputs)
    (folder / "model.onnx").write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="verification failed"):
        Classifier(folder, spec, threads=2)

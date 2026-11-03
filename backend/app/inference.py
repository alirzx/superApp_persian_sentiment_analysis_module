"""Two independently verified, offline ONNX Runtime CPU classifiers."""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path

import numpy as np
from .postprocessing import make_prediction
from .preprocessing import normalize_text


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class Classifier:
    def __init__(self, path: Path, spec: dict, threads: int):
        # Diagnose missing model artifacts before importing inference libraries.
        manifest_path = path / "manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError(
                f"Prepared model artifact missing for task '{path.name}' at {manifest_path}. "
                "Run 'docker compose up --build -d' to populate the persistent model "
                "volume via model-setup, or 'docker compose run --rm --no-deps model-setup'."
            )
        import onnxruntime as ort
        from transformers import AutoTokenizer

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        required = {"model.onnx", "config.json", "spiece.model"}
        if not isinstance(manifest.get("sha256"), dict) or not required.issubset(manifest["sha256"]):
            raise RuntimeError(f"Incomplete prepared model for task '{path.name}'; regenerate with model-setup")
        if manifest["repo"] != spec["repo"] or manifest["format"] != "onnx-fp32":
            raise RuntimeError("Wrong model artifact")
        revision = manifest["revision"]
        if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision.lower()):
            raise RuntimeError("Artifact does not contain an immutable revision")
        declared_rev = spec["revision"]
        if declared_rev != "main" and declared_rev != revision:
            raise RuntimeError("Model artifact does not match configured revision")
        for relative, expected in manifest["sha256"].items():
            if Path(relative).is_absolute() or ".." in Path(relative).parts:
                raise RuntimeError("Unsafe manifest path")
            if sha256(path / relative) != expected:
                raise RuntimeError(f"Model file verification failed: {relative}")
        config = json.loads((path / "config.json").read_text(encoding="utf-8"))
        names = [str(config["id2label"][str(i)]) for i in range(len(config["id2label"]))]
        if names != spec["expected_labels"]:
            raise RuntimeError(f"Unexpected label mapping: {names}")
        self.tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True, trust_remote_code=False, use_fast=False)
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads
        opts.inter_op_num_threads = 1
        opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.session = ort.InferenceSession(str(path / "model.onnx"), sess_options=opts, providers=["CPUExecutionProvider"])
        if self.session.get_providers() != ["CPUExecutionProvider"]:
            raise RuntimeError("CPUExecutionProvider required")
        self.inputs = [i.name for i in self.session.get_inputs()]
        if not set(self.inputs).issubset({"input_ids", "attention_mask", "token_type_ids"}):
            raise RuntimeError("Unexpected model input signature")
        if len(self.session.get_outputs()) != 1:
            raise RuntimeError("Unexpected output signature")
        self.labels = names
        self.max_tokens = spec["max_tokens"]
        self.meta = {"repo": spec["repo"], "revision": revision}
        self.ready = False

    def predict_many(self, task: str, texts: list[str]):
        clean = [normalize_text(t) for t in texts]
        tokens = self.tokenizer(clean, return_tensors="np", padding=True, truncation=True, max_length=self.max_tokens)
        feed = {name: np.asarray(tokens[name], dtype=np.int64) for name in self.inputs}
        t0 = time.perf_counter()
        logits = self.session.run(None, feed)[0]
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        if logits.shape != (len(clean), len(self.labels)):
            raise RuntimeError("Unexpected classifier output shape")
        return [dict(make_prediction(task, row, self.labels, self.meta), inference_ms=elapsed) for row in logits]

    def warmup(self, task: str):
        self.predict_many(task, ["این یک متن آزمایشی است."])
        self.ready = True


class NLPInferenceEngine:
    def __init__(self, settings):
        specs = settings.models()
        self.models = {task: Classifier(settings.model_dir / task, spec, settings.cpu_threads) for task, spec in specs.items()}
        self.warmed_up = False

    def warmup(self):
        for task, model in self.models.items():
            model.warmup(task)
        self.warmed_up = True

    def predict_many(self, task: str, texts: list[str]):
        return self.models[task].predict_many(task, texts)

    def metadata(self):
        return {key: {"model": v.meta["repo"], "revision": v.meta["revision"], "labels": v.labels,
                      "max_tokens": v.max_tokens, "runtime": "onnxruntime-cpu"} for key, v in self.models.items()}

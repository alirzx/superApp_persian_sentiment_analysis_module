"""Download immutable HF snapshots, export two ALBERT classifiers to CPU ONNX.

Runs ONLY in the opt-in model-setup container; PyTorch never ships in API image.
Trust boundary: upstream pytorch_model.bin is pickle; review publisher and source.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path

ALLOWED = {"config.json", "pytorch_model.bin", "spiece.model", "spiece.vocab",
           "special_tokens_map.json", "tokenizer_config.json", "added_tokens.json", "tokenizer.json"}
REQUIRED = {"config.json", "pytorch_model.bin", "spiece.model"}
REQUIRED_RUNTIME = {"model.onnx", "config.json", "spiece.model"}


def digest(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def check_installed(folder: Path, spec: dict) -> bool:
    try:
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if manifest["repo"] != spec["repo"] or manifest["format"] != "onnx-fp32":
            return False
        if spec["revision"] != "main" and manifest["revision"] != spec["revision"]:
            return False
        if not (len(manifest["revision"]) == 40 and all(c in "0123456789abcdef" for c in manifest["revision"].lower())):
            return False
        digests = manifest.get("sha256")
        if not isinstance(digests, dict) or not REQUIRED_RUNTIME.issubset(digests):
            return False
        for name, expected in digests.items():
            if (name not in ALLOWED | {"model.onnx"}
                    or not isinstance(expected, str) or len(expected) != 64
                    or any(ch not in "0123456789abcdef" for ch in expected.lower())
                    or not (folder / name).is_file() or digest(folder / name) != expected):
                return False
        cfg = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        labels = [cfg["id2label"][str(i)] for i in range(len(cfg["id2label"]))]
        return labels == spec["expected_labels"]
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError):
        return False


def export_model(folder: Path, max_tokens: int):
    import numpy as np
    import onnxruntime as ort
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    torch.set_num_threads(2)
    model = AutoModelForSequenceClassification.from_pretrained(str(folder), local_files_only=True,
                                                               use_safetensors=False, trust_remote_code=False)
    model.cpu().eval()
    tokenizer = AutoTokenizer.from_pretrained(str(folder), local_files_only=True, use_fast=False,
                                               trust_remote_code=False)
    samples = tokenizer(["این محصول خوب است.", "این خبر درباره اقتصاد است."],
                        return_tensors="pt", padding=True, truncation=True, max_length=max_tokens)
    # Explicit inputs match the ALBERT token-type contract.
    class Wrapper(torch.nn.Module):
        def __init__(self, inner):
            super().__init__()
            self.inner = inner
        def forward(self, input_ids, attention_mask, token_type_ids):
            return self.inner(input_ids=input_ids, attention_mask=attention_mask,
                              token_type_ids=token_type_ids).logits

    wrapped = Wrapper(model)
    inputs = (samples["input_ids"], samples["attention_mask"], samples["token_type_ids"])
    with torch.inference_mode():
        reference = wrapped(*inputs).detach().numpy()
        torch.onnx.export(wrapped, inputs, str(folder / "model.onnx"), opset_version=17,
                          input_names=["input_ids", "attention_mask", "token_type_ids"],
                          output_names=["logits"],
                          dynamic_axes={"input_ids": {0: "batch", 1: "sequence"},
                                        "attention_mask": {0: "batch", 1: "sequence"},
                                        "token_type_ids": {0: "batch", 1: "sequence"},
                                        "logits": {0: "batch"}}, do_constant_folding=True)
    session = ort.InferenceSession(str(folder / "model.onnx"), providers=["CPUExecutionProvider"])
    predicted = session.run(None, {k: v.detach().numpy().astype(np.int64) for k, v in samples.items() if k in
                                   {i.name for i in session.get_inputs()}})[0]
    if not np.allclose(reference, predicted, atol=1e-3, rtol=1e-3):
        raise RuntimeError(f"Export parity validation failed: maximum absolute difference {np.max(abs(reference - predicted))}")
    # Repeat with a shorter sequence to verify dynamic sequence support.
    small = tokenizer(["سلام"], return_tensors="np")
    session.run(None, {k: np.asarray(small[k], dtype=np.int64) for k in
                       [i.name for i in session.get_inputs()]})
    del wrapped, model


def prepare_task(task: str, spec: dict, root: Path, refresh: bool):
    from huggingface_hub import HfApi, snapshot_download
    import fcntl

    target = root / task
    root.mkdir(parents=True, exist_ok=True)
    with (root / f".{task}.lock").open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        if not refresh and check_installed(target, spec):
            print(f"READY {task}: verified cached artifact; download/export skipped")
            return
        print(f"Resolving {task}: {spec['repo']}@{spec['revision']}")
        info = HfApi().model_info(repo_id=spec["repo"], revision=spec["revision"])
        sha = info.sha
        if not sha or len(sha) != 40:
            raise RuntimeError("Model Hub did not return immutable SHA")
        present = {s.rfilename for s in info.siblings}
        if not REQUIRED.issubset(present):
            raise RuntimeError(f"Upstream model missing required files: {REQUIRED - present}")
        stage = root / f".{task}.{uuid.uuid4().hex}.staging"
        stage.mkdir(mode=0o700)
        try:
            files = sorted(ALLOWED.intersection(present))
            snapshot = Path(snapshot_download(repo_id=spec["repo"], revision=sha,
                                              allow_patterns=files, cache_dir=str(root / ".hf-hub")))
            for file in files:
                shutil.copyfile(snapshot / file, stage / file)
            config = json.loads((stage / "config.json").read_text(encoding="utf-8"))
            actual_labels = [config["id2label"][str(i)] for i in range(len(config["id2label"]))]
            if actual_labels != spec["expected_labels"]:
                raise RuntimeError(f"Label contract changed upstream for {task}: {actual_labels}")
            if config.get("model_type") != "albert":
                raise RuntimeError("Expected ALBERT model architecture")
            export_model(stage, spec["max_tokens"])
            (stage / "pytorch_model.bin").unlink()  # setup-only pickle is not shipped to runtime
            kept = sorted({p.name for p in stage.iterdir() if p.is_file()})
            manifest = {"repo": spec["repo"], "revision": sha, "format": "onnx-fp32",
                        "sha256": {name: digest(stage / name) for name in kept}}
            (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            if not check_installed(stage, spec):
                raise RuntimeError("Staged artifact failed verification")
            backup = root / f".{task}.{uuid.uuid4().hex}.previous"
            stage.chmod(0o755)  # root-run setup must leave read access for unprivileged API
            if target.exists():
                target.rename(backup)
            try:
                stage.rename(target)
            except Exception:
                if backup.exists():
                    backup.rename(target)
                raise
            shutil.rmtree(backup, ignore_errors=True)
            print(f"READY {task}: {spec['repo']}@{sha}, checksum verified")
        finally:
            shutil.rmtree(stage, ignore_errors=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--verify-only", action="store_true")
    p.add_argument("--refresh", action="store_true", help="Explicitly resolve a new revision and reinstall")
    args = p.parse_args()
    model_specs = json.loads(Path(os.getenv("MODELS_CONFIG", "/app/models.json")).read_text(encoding="utf-8"))
    root = Path(os.getenv("MODEL_DIR", "/models"))
    for task, spec in model_specs.items():
        env_revision = os.getenv(f"MODEL_{task.upper()}_REVISION")
        if env_revision:
            spec["revision"] = env_revision
        if args.verify_only:
            if not check_installed(root / task, spec):
                raise SystemExit(f"Model artifact missing or corrupt: {task}")
            print(f"VERIFIED {task}")
        else:
            prepare_task(task, spec, root, args.refresh)

if __name__ == "__main__":
    main()

"""Offline model provisioning regression test; no Hugging Face download needed."""
import hashlib
import json
import stat
from pathlib import Path
from types import SimpleNamespace
from scripts import prepare_models

def test_atomic_setup_cache_hit_and_recovery(tmp_path, monkeypatch):
    import huggingface_hub
    source = tmp_path / "upstream"
    source.mkdir()
    labels = ["Negative", "Neutral", "Positive"]
    (source / "config.json").write_text(json.dumps({"model_type":"albert",
        "id2label":{str(i):label for i,label in enumerate(labels)}}))
    (source / "pytorch_model.bin").write_bytes(b"test-weights")
    (source / "spiece.model").write_bytes(b"test-tokenizer")
    calls = {"lookup":0, "export":0}
    class FakeHub:
        def model_info(self, repo_id, revision):
            calls["lookup"] += 1
            return SimpleNamespace(sha="a"*40,
                siblings=[SimpleNamespace(rfilename=p.name) for p in source.iterdir()])
    def fake_export(folder, max_tokens):
        calls["export"] += 1
        (folder / "model.onnx").write_bytes(b"test-onnx")
    monkeypatch.setattr(huggingface_hub, "HfApi", FakeHub)
    monkeypatch.setattr(huggingface_hub, "snapshot_download", lambda **kwargs: str(source))
    monkeypatch.setattr(prepare_models, "export_model", fake_export)
    spec = {"repo":"test/albert", "revision":"main", "expected_labels":labels, "max_tokens":256}
    root = tmp_path / "models"
    prepare_models.prepare_task("sentiment", spec, root, False)
    installed = root / "sentiment"
    assert prepare_models.check_installed(installed, spec)
    assert (installed.stat().st_mode & stat.S_IROTH) and (installed.stat().st_mode & stat.S_IXOTH)
    assert not (installed / "pytorch_model.bin").exists()
    prepare_models.prepare_task("sentiment", spec, root, False)
    assert calls == {"lookup":1, "export":1}
    (installed / "model.onnx").write_bytes(b"broken")
    assert not prepare_models.check_installed(installed, spec)
    prepare_models.prepare_task("sentiment", spec, root, False)
    assert prepare_models.check_installed(installed, spec)
    assert calls == {"lookup":2, "export":2}

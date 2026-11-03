import hashlib
import json
from pathlib import Path
from app.config import Settings
from scripts.prepare_models import check_installed


def test_specs_have_contracts():
    path=Path(__file__).resolve().parents[2] / 'models.json'
    specs=Settings(models_config=path).models()
    assert len(specs['sentiment']['expected_labels']) == 3
    assert len(specs['topics']['expected_labels']) == 8


def test_verified_artifact(tmp_path):
    specs=Settings(models_config=Path(__file__).resolve().parents[2]/'models.json').models()
    folder=tmp_path / 'sentiment'
    folder.mkdir()
    config={'id2label':{str(i): name for i,name in enumerate(specs['sentiment']['expected_labels'])}}
    (folder/'config.json').write_text(json.dumps(config))
    (folder/'model.onnx').write_bytes(b'mocked graph')
    (folder/'spiece.model').write_bytes(b'mocked sentencepiece')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    (folder/'manifest.json').write_text(json.dumps({'repo':specs['sentiment']['repo'],
      'revision':'a'*40,'format':'onnx-fp32','sha256':hashes}))
    assert check_installed(folder,specs['sentiment'])
    (folder/'model.onnx').write_bytes(b'tampered')
    assert not check_installed(folder,specs['sentiment'])


def test_incomplete_cache_is_rejected(tmp_path):
    specs = Settings(models_config=Path(__file__).resolve().parents[2] / 'models.json').models()
    folder = tmp_path / 'sentiment'
    folder.mkdir()
    (folder / 'config.json').write_text(json.dumps({'id2label': {
        str(i): name for i, name in enumerate(specs['sentiment']['expected_labels'])}}))
    (folder / 'model.onnx').write_bytes(b'mock')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    (folder / 'manifest.json').write_text(json.dumps({
        'repo': specs['sentiment']['repo'], 'revision': 'a'*40,
        'format': 'onnx-fp32', 'sha256': hashes
    }))
    assert not check_installed(folder, specs['sentiment'])


def test_missing_manifest_explains_setup_command(tmp_path):
    import pytest
    from app.inference import Classifier
    spec = Settings(models_config=Path(__file__).resolve().parents[2] / 'models.json').models()['sentiment']
    with pytest.raises(RuntimeError, match='model-setup'):
        Classifier(tmp_path / 'sentiment', spec, threads=2)

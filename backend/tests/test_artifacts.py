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
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
    (folder/'manifest.json').write_text(json.dumps({'repo':specs['sentiment']['repo'],
      'revision':'a'*40,'format':'onnx-fp32','sha256':hashes}))
    assert check_installed(folder,specs['sentiment'])
    (folder/'model.onnx').write_bytes(b'tampered')
    assert not check_installed(folder,specs['sentiment'])

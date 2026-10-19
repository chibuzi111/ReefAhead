"""Inference refuses missing or altered local model manifests before deserialization."""
import hashlib
import json
import pytest
from src import predict

@pytest.fixture
def artifact_dir(tmp_path,monkeypatch):
    predict._bundle.cache_clear()
    monkeypatch.setattr(predict,'ARTIFACTS',tmp_path)
    yield tmp_path
    predict._bundle.cache_clear()

def test_integrity_rejects_corruption_before_deserialization(artifact_dir,monkeypatch):
    p=artifact_dir/'model_7d.joblib'
    p.write_bytes(b'original')
    (artifact_dir/'evaluation.json').write_text(json.dumps({'model_artifacts':{'7':{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}}))
    p.write_bytes(b'altered')
    monkeypatch.setattr(predict.joblib,'load',lambda *_: pytest.fail('Corrupt artifact was deserialized'))
    with pytest.raises(ValueError,match='checksum mismatch'): predict._bundle(7)

def test_integrity_requires_manifest(artifact_dir,monkeypatch):
    monkeypatch.setattr(predict.joblib,'load',lambda *_: pytest.fail('Unverified artifact was deserialized'))
    with pytest.raises(ValueError,match='manifest'): predict._bundle(7)

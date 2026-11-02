"""Deployment regression tests for local/production ports and GitLab entrypoint."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _env(path: str) -> dict[str, str]:
    values = {}
    for row in (ROOT / path).read_text(encoding="utf-8").splitlines():
        if not row or row.startswith("#"):
            continue
        assert "=" in row, f"Invalid env line: {row!r}"
        k, v = row.split("=", 1)
        assert k and k.strip() == k, f"Invalid env key: {k!r}"
        values[k] = v
    return values


def test_local_and_server_port_contract():
    local = _env('.env.example')
    prod = _env('.env.production.example')
    assert (local['API_PORT'], local['UI_PORT']) == ('8001', '8082')
    assert (prod['API_PORT'], prod['UI_PORT']) == ('8002', '8083')
    assert local['APP_ENV'] == 'development'
    assert prod['APP_ENV'] == 'production'
    assert prod['API_TOKEN'] == ''  # must fail closed until operator supplies one
    assert (prod['API_BIND_IP'], prod['UI_BIND_IP']) == ('127.0.0.1', '127.0.0.1')


def test_gitlab_deployment_single_source_and_path():
    canonical = (ROOT / '.gitlab-ci.yml').read_text(encoding='utf-8')
    compatibility = (ROOT / '.gitlab-ci-prod.yml').read_text(encoding='utf-8')
    assert 'local: .gitlab-ci.yml' in compatibility
    assert 'deploy:' not in compatibility
    assert '/opt/apps/ai-service/persian_sentiment_topic_analysis_module' in canonical
    assert 'ssh-keyscan' not in canonical
    assert 'RUN_SERVICES: "0"' in canonical


def test_no_untrusted_token_placeholder_in_server_example():
    production = _env('.env.production.example')
    assert production['API_TOKEN'] == ''
    from app.config import Settings
    import pytest
    with pytest.raises(ValueError):
        Settings(environment='production', api_token=production['API_TOKEN']).validate()

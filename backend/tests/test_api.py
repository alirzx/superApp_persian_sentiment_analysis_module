def test_health_and_auth(client, headers):
    assert client.get("/health/live").status_code == 200
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json()["tasks"] == ["sentiment", "topics"]
    assert client.get("/v1/models").status_code == 401
    assert client.get("/v1/models", headers=headers).status_code == 200
    assert client.get("/metrics", headers=headers).status_code == 200


def test_sentiment(client, headers):
    data = client.post("/v1/sentiment", json={"text": "اين محصول خوب است."}, headers=headers)
    assert data.status_code == 200, data.text
    item = data.json()
    assert item["label"] == "positive"
    assert item["label_fa"] == "مثبت"
    assert len(item["scores"]) == 3
    assert item["confidence_calibrated"] is False
    assert item["revision"] == "a" * 40
    assert item["request_id"]


def test_topics_and_alias(client, headers):
    for route in ("/v1/topics", "/v1/classify"):
        res = client.post(route, json={"text": "اقتصاد ایران"}, headers=headers)
        assert res.status_code == 200, res.text
        assert res.json()["label_fa"] == "اقتصادی"
        assert len(res.json()["scores"]) == 8


def test_analyze_and_batch(client, headers):
    both = client.post("/v1/analyze", json={"text": "امروز خبر خوبی بود."}, headers=headers)
    assert both.status_code == 200
    assert set(("sentiment", "topics")).issubset(both.json())
    batch = client.post("/v1/batch", json={"task":"sentiment","texts":["عالی", "بد"]}, headers=headers)
    assert batch.status_code == 200
    assert batch.json()["count"] == 2
    assert len(batch.json()["results"]) == 2


def test_invalid_inputs(client, headers):
    assert client.post("/v1/sentiment", json={"text": " "}, headers=headers).status_code == 422
    assert client.post("/v1/topics", json={"text": "x"*1001}, headers=headers).status_code == 413
    assert client.post("/v1/batch", json={"task":"sentiment", "texts":["x"]*5}, headers=headers).status_code == 413
    assert client.post("/v1/batch", json={"task":"bad", "texts":["x"]}, headers=headers).status_code == 422
    assert client.post("/v1/sentiment", json={"text":"x"*4096}, headers=headers).status_code == 413
    assert client.post("/v1/sentiment", json={"text":"normal"}).status_code == 401


def test_production_token():
    from pytest import raises
    from app.config import Settings
    with raises(ValueError):
        Settings(environment="production", api_token="abc").validate()
    Settings(environment="production", api_token="a" * 32).validate()

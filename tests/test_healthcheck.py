from unittest.mock import patch

import pytest
from django.urls import reverse


@pytest.mark.django_db
@patch("apps.common.web.Redis.from_url")
def test_healthcheck_returns_ok(mock_redis_factory, client):
    mock_redis = mock_redis_factory.return_value
    mock_redis.ping.return_value = True

    response = client.get(reverse("healthz"))

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["checks"] == {"database": "ok", "redis": "ok"}

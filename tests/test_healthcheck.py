import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_healthcheck_returns_ok(client):
    response = client.get(reverse("healthz"))

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["checks"] == {"database": "ok"}

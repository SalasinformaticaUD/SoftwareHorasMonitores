import pytest
from django.urls import reverse

from tests.factories import UserFactory


@pytest.mark.django_db
def test_api_login_and_me_endpoint(api_client):
    user = UserFactory(username="leader.physics", password="ChangeMe123!")

    response = api_client.post(
        reverse("api-login"),
        {"username": "leader.physics", "password": "ChangeMe123!"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["username"] == user.username

    me_response = api_client.get(reverse("api-me"))
    assert me_response.status_code == 200
    assert me_response.data["role"] == user.role


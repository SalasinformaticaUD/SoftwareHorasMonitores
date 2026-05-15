from django.core import mail
from django.urls import reverse

import pytest

from tests.factories import UserFactory


@pytest.mark.django_db
def test_login_shows_password_reset_button(client):
    response = client.get(reverse("login"))

    assert response.status_code == 200
    assert b"Recuperar contrasena" in response.content
    assert reverse("password_reset").encode() in response.content


@pytest.mark.django_db
def test_password_reset_sends_recovery_email(client):
    user = UserFactory(email="lider@example.com", username="lider@example.com")

    response = client.post(reverse("password_reset"), {"email": user.email})

    assert response.status_code == 302
    assert response.url == reverse("password_reset_done")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [user.email]
    assert "Recupera tu contrasena" in mail.outbox[0].subject
    assert "/accounts/reset/" in mail.outbox[0].body

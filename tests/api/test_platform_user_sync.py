import uuid

import pytest
from django.urls import reverse
from django.test import override_settings

from tests.factories import UserFactory


TOKEN = 'integration-test-token'


def sync_payload(**overrides):
    payload = {
        'external_user_id': str(uuid.uuid4()),
        'username': 'lider.central',
        'email': 'lider.central@example.test',
        'full_name': 'Líder Central',
        'role': 'leader',
        'department': 'informatics_labs',
        'is_active': True,
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
@override_settings(MONITORES_SERVICE_TOKEN=TOKEN)
def test_sync_links_unique_local_user_by_username(api_client):
    previous_external_id = uuid.uuid4()
    local = UserFactory(
        username='lider.central',
        email='correo.anterior@example.test',
        usuario_externo_id=previous_external_id,
    )
    payload = sync_payload()

    response = api_client.post(
        reverse('platform-user-sync'),
        payload,
        format='json',
        HTTP_X_MONITORES_SERVICE_TOKEN=TOKEN,
    )

    assert response.status_code == 200, response.data
    local.refresh_from_db()
    assert str(local.usuario_externo_id) != str(previous_external_id)
    assert str(local.usuario_externo_id) == payload['external_user_id']
    assert local.email == payload['email']
    assert local.has_usable_password() is False


@pytest.mark.django_db
@override_settings(MONITORES_SERVICE_TOKEN=TOKEN)
def test_sync_rejects_ambiguous_username_and_email_matches(api_client):
    UserFactory(username='lider.central', email='primero@example.test')
    UserFactory(username='otro.usuario', email='lider.central@example.test')

    response = api_client.post(
        reverse('platform-user-sync'),
        sync_payload(),
        format='json',
        HTTP_X_MONITORES_SERVICE_TOKEN=TOKEN,
    )

    assert response.status_code == 400
    assert 'cuentas locales diferentes' in str(response.data)

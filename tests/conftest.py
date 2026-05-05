from datetime import datetime, time

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from openpyxl import Workbook
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.CELERY_TASK_ALWAYS_EAGER = True
    return settings.MEDIA_ROOT


def build_excel_file(headers, rows, name="croschex.xlsx"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    from io import BytesIO

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return SimpleUploadedFile(
        name=name,
        content=buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@pytest.fixture
def sample_excel_file():
    return build_excel_file(
        headers=["Nombre", "Departamento", "Fecha", "Hora Entrada", "Hora Salida"],
        rows=[
            ["Ana Torres", "Física", datetime(2026, 4, 13), datetime(2026, 4, 13, 8, 0), datetime(2026, 4, 13, 12, 30)],
        ],
    )


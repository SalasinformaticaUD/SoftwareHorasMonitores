from pathlib import Path
from typing import Optional

from celery import shared_task
from django.conf import settings

from apps.attendance.models import AttendanceImportJob
from apps.attendance.services import create_import_job_from_path, import_workbook


@shared_task
def process_import_job(job_id: str) -> str:
    # print(f"process_import_job: {job_id}")
    # print(AttendanceImportJob.objects)
    job = AttendanceImportJob.objects.get(pk=job_id)
    import_workbook(job)
    return str(job.id)


@shared_task
def import_attendance_from_dropzone() -> Optional[str]:
    dropzone_file = Path(settings.CELERY_IMPORT_DROPZONE)
    if not dropzone_file.exists():
        return None
    job = create_import_job_from_path(file_path=str(dropzone_file))
    import_workbook(job)
    return str(job.id)

from pathlib import Path
from typing import Optional

from django.conf import settings

from apps.attendance.models import AttendanceImportJob
from apps.attendance.services import create_import_job_from_path, import_workbook


def process_import_job(job_id: str) -> str:
    job = AttendanceImportJob.objects.get(pk=job_id)
    import_workbook(job)
    return str(job.id)


def import_attendance_from_dropzone() -> Optional[str]:
    dropzone_file = Path(settings.IMPORT_DROPZONE_PATH)
    if not dropzone_file.exists():
        return None
    job = create_import_job_from_path(file_path=str(dropzone_file))
    import_workbook(job)
    return str(job.id)

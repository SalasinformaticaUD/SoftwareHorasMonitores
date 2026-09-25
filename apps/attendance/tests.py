from datetime import date

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.attendance.models import AttendanceImportJob, AttendanceRawRecord
from apps.common.choices import ImportJobStatusChoices, UserRoleChoices

User = get_user_model()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AttendanceHistoryApiTests(APITestCase):
    def test_history_includes_imported_record_even_when_not_pending_reconciliation(self):
        admin = User.objects.create_user(
            username="admin-history",
            email="admin-history@example.test",
            password="ClaveSegura123456",
            role=UserRoleChoices.ADMIN,
            is_staff=True,
        )
        job = AttendanceImportJob.objects.create(
            uploaded_by=admin,
            source_file="attendance/imports/history.xlsx",
            file_name="history.xlsx",
            status=ImportJobStatusChoices.COMPLETED,
        )
        raw = AttendanceRawRecord.objects.create(
            import_job=job,
            row_number=1,
            raw_full_name="Monitor importado",
            raw_department="Física",
            work_day=date(2026, 9, 18),
            reconciliation_status="matched",
        )
        self.client.force_authenticate(admin)
        response = self.client.get("/api/v1/attendance/history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(raw.id))
        self.assertEqual(response.data["results"][0]["reconciliation_status"], "matched")

    def test_history_is_paginated_and_only_exposes_matched_or_rejected_records(self):
        admin = User.objects.create_user(
            username="admin-paginated-history",
            email="admin-paginated-history@example.test",
            password="ClaveSegura123456",
            role=UserRoleChoices.ADMIN,
            is_staff=True,
        )
        job = AttendanceImportJob.objects.create(
            uploaded_by=admin,
            source_file="attendance/imports/paginated-history.xlsx",
            file_name="paginated-history.xlsx",
            status=ImportJobStatusChoices.COMPLETED,
        )
        for row_number in range(1, 11):
            AttendanceRawRecord.objects.create(
                import_job=job,
                row_number=row_number,
                raw_full_name=f"Monitor {row_number}",
                raw_department="Monitores Laboratorios",
                work_day=date(2026, 9, row_number),
                reconciliation_status="matched" if row_number % 2 else "rejected",
            )
        AttendanceRawRecord.objects.create(
            import_job=job,
            row_number=11,
            raw_full_name="Monitor pendiente",
            raw_department="Monitores Laboratorios",
            work_day=date(2026, 9, 11),
            reconciliation_status="manual_review",
        )

        self.client.force_authenticate(admin)
        first_page = self.client.get("/api/v1/attendance/history/")
        second_page = self.client.get("/api/v1/attendance/history/?page=2")

        self.assertEqual(first_page.status_code, status.HTTP_200_OK)
        self.assertEqual(first_page.data["count"], 10)
        self.assertEqual(len(first_page.data["results"]), 8)
        self.assertIsNotNone(first_page.data["next"])
        self.assertEqual(len(second_page.data["results"]), 2)
        self.assertEqual(
            {row["reconciliation_status"] for row in first_page.data["results"]},
            {"matched", "rejected"},
        )

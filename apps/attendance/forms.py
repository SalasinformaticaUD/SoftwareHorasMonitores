from django import forms

from apps.attendance.models import AttendanceRawRecord
from apps.common.choices import DepartmentChoices
from apps.monitors.models import Monitor


class AttendanceUploadForm(forms.Form):
    file = forms.FileField(label="Archivo Excel")


class ManualReconciliationForm(forms.Form):
    raw_record_id = forms.UUIDField(widget=forms.HiddenInput)
    monitor = forms.ModelChoiceField(queryset=Monitor.objects.none(), label="Monitor")

    def __init__(self, *args, **kwargs):
        department = kwargs.pop("department", None)
        super().__init__(*args, **kwargs)
        queryset = Monitor.objects.filter(is_active=True)
        if department:
            queryset = queryset.filter(department=department)
        self.fields["monitor"].queryset = queryset.order_by("full_name")


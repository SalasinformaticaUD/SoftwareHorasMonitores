from django import forms



class PublicMonitorLookupForm(forms.Form):
    codigo_estudiante = forms.CharField(max_length=20, label="Código de estudiante")

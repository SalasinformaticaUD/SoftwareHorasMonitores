from django import forms


class OvertimeReviewForm(forms.Form):
    session_id = forms.UUIDField(widget=forms.HiddenInput)
    decision = forms.ChoiceField(choices=(("approve", "Aprobar"), ("reject", "Rechazar")))
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False, label="Anotación")


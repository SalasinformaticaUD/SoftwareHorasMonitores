from django.contrib.auth.forms import PasswordResetForm


class RecoveryPasswordResetForm(PasswordResetForm):
    def save(self, *args, **kwargs):
        self.user = None
        return super().save(*args, **kwargs)

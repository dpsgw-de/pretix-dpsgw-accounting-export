from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.views.generic import FormView

from pretix.base.models import Organizer
from pretix.base.settings import SettingsSandbox
from pretix.control.views.event import DecoupleMixin
from pretix.control.views.organizer import OrganizerDetailViewMixin

from .forms import AccountingSettingsForm


class AccountingSettingsView(
    DecoupleMixin,
    OrganizerDetailViewMixin,
    FormView,
):
    model = Organizer
    permission = "can_change_organizer_settings"
    form_class = AccountingSettingsForm
    template_name = "pretix_dpsgw_accounting_export/settings.html"

    def get_settings(self):
        return SettingsSandbox(
            "plugin",
            "pretix_dpsgw_accounting_export",
            self.request.organizer,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        settings = self.get_settings()

        kwargs["initial"] = {
            "mandant": settings.get("mandant", ""),
            "belegart": settings.get("belegart", ""),
            "sachkonto": settings.get("sachkonto", ""),
            "kostenstelle": settings.get("kostenstelle", ""),
            "steuerschluessel": settings.get("steuerschluessel", ""),
            "barcodeprefix": settings.get("barcodeprefix", ""),
        }
        return kwargs

    def get_success_url(self):
        return reverse(
            "plugins:pretix_dpsgw_accounting_export:settings",
            kwargs={
                "organizer": self.request.organizer.slug,
            },
        )

    @transaction.atomic
    def form_valid(self, form):
        settings = self.get_settings()

        for name in form.changed_data:
            value = form.cleaned_data[name]

            if value:
                settings.set(name, value)
            else:
                del settings[name]

        messages.success(
            self.request,
            "Die Einstellungen wurden gespeichert.",
        )

        return super().form_valid(form)


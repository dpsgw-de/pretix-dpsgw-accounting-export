from django.urls import path

from .views import AccountingSettingsView

urlpatterns = [
    path(
        "control/organizer/<slug:organizer>/dpsgw-accounting-settings/",
        AccountingSettingsView.as_view(),
        name="settings",
    ),
]

from dataclasses import dataclass
from django.utils.translation import gettext_lazy as _
from pretix.base.services.export import ExportError
from pretix.base.settings import SettingsSandbox


@dataclass(frozen=True)
class ExportSettings:
    mandant: str
    belegart: str
    sachkonto: str
    sachkonto_zusatz: str
    kostenstelle: str
    steuerschluessel: str
    steuerschluessel_zusatz: str
    barcodeprefix: str

    @classmethod
    def from_settings(cls, settings: SettingsSandbox) -> "ExportSettings":
        fields = {
            "mandant": _("Mandant"),
            "belegart": _("Belegart"),
            "sachkonto": _("Sachkonto"),
            "sachkonto_zusatz": _("Sachkonto-Zusatz"),
            "kostenstelle": _("Kostenstelle"),
            "steuerschluessel": _("Steuerschlüssel"),
            "steuerschluessel_zusatz": _("Steuerschlüssel-Zusatz"),
            "barcodeprefix": _("Barcode-Präfix"),
        }

        values = {key: settings.get(key, "") for key in fields}

        missing = [
            str(label)
            for key, label in fields.items()
            if not str(values[key] or "").strip()
        ]

        if missing:
            raise ExportError(
                _(
                    "Die Konfiguration des Buchhaltungsexports ist "
                    "unvollständig. Bitte ergänze folgende Angaben: "
                    "%(fields)s"
                ) % {"fields": ", ".join(missing)}
            )

        return cls(**values)
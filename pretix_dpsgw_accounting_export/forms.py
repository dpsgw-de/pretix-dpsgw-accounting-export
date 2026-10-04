from django import forms
from django.utils.translation import gettext_lazy as _


class AccountingSettingsForm(forms.Form):
    mandant = forms.CharField(
        label=_("Mandantennummer"),
        required=False,
        help_text=_("Mandantennummer für den Buchhaltungsexport."),
    )

    belegart = forms.CharField(
        label=_("Belegart"),
        required=False,
        help_text=_("Belegart für den Buchhaltungsexport."),
    )

    sachkonto = forms.CharField(
        label=_("Sachkonto"),
        required=False,
        help_text=_("Sachkonto für den Buchhaltungsexport."),
    )

    sachkonto_zusatz = forms.CharField(
        label=_("Sachkonto Zusatzprodukte"),
        required=False,
        help_text=_("Sachkonto für Zusatzprodukte (Nicht-Zugangsprodukte)."),
    )

    kostenstelle = forms.CharField(
        label=_("Kostenstelle"),
        required=False,
        help_text=_("Kostenstelle für den Buchhaltungsexport."),
    )

    steuerschluessel = forms.CharField(
        label=_("Steuerschlüssel"),
        required=False,
        help_text=_("Steuerschlüssel für den Buchhaltungsexport."),
    )

    steuerschluessel_zusatz = forms.CharField(
        label=_("Steuerschlüssel Zusatzprodukte"),
        required=False,
        help_text=_("Steuerschlüssel für Zusatzprodukte (Nicht-Zugangsprodukte)."),
    )

    barcodeprefix = forms.CharField(
        label=_("Barcode Präfix"),
        required=False,
        help_text=_("Präfix vor der Rechnungsnummer im Barcode."),
    )

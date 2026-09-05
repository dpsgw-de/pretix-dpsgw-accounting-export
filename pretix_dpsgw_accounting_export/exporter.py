from decimal import Decimal

from django.db.models import F, OuterRef, Subquery, Sum
from django.utils.formats import date_format
from django.utils.translation import gettext

from pretix.base.exporters.invoices import InvoiceDataExporter
from pretix.base.exporters.invoices import chunked_iterable
from pretix.base.models import InvoiceLine
from pretix.base.settings import SettingsSandbox
from pretix_barcode_invoice_renderer.utils import format_date_range


# This implementation is based on InvoiceDataExporter from Pretix

class ExtendedInvoiceDataExporter(InvoiceDataExporter):
    """Invoice data export with an additional full order code column."""

    identifier = "invoicedata_dpsgw_accounting"
    verbose_name = "DPSG Würzburg Buchhaltungs-Export"
    description = "Exportiert die Rechnungsdaten im Format, das für den Buchhaltungsimport genutzt werden kann"

    def iterate_sheet(self, form_data, sheet):
        _ = gettext

        if sheet == "lines":
            yield from super().iterate_sheet(form_data, sheet)
            return

        if sheet != "invoices":
            yield from super().iterate_sheet(form_data, sheet)
            return

        yield [
            "Mandantennummer",
            "Buchungsperiode",
            "Belegdatum",
            "Belegart",
            "Geschäftskennzeichen",
            "interne Belegnummer",
            "externe Belegnummer",
            "Konto 1",
            "Kostenstelle Konto 1",
            "Projekt Konto 1",
            "Kostentraeger Konto 1",
            "Geschäftseinheit Konto 1",
            "Geschäftsfeld Konto 1",
            "StS Konto 1",
            "Steuersatz Konto 1",
            "Buchungsbetrag 1",
            "Buchungstext 1",
            "Währung",
            "Zahlungskondition",
            "Fälligkeit",
            "1. Skontofrist",
            "1. Skontoprozentsatz",
            "2. Skontofrist",
            "2. Skontoprozentsatz",
            "Valuta",
            "Zahlungsart",
            "Kurs",
            "Umrechnungsdatum",
            "Verbandsmitglied",
            "OP - Text",
            "Sofort mahnen",
            "Sofort zahlen",
            "Herkunft / ID",
            "Mahndatum",
            "Mahnausschluss  bis",
            "Zahlungsausschluss bis",
            "REB - Beleg",
            "Konzernbewegungsart",
            "Verbundenes  Unternehmen",
            "abzugrenzende  Perioden",
            "Konzernsachverhalt",
            "Ausschluss  ZentralClearing",
            "Mahnsperrgrund",
            "Zahlsperrgrund",
            "OP - Status",
            "Buchungskommentar 1",
            "Buchungskommentar 2",
            "Buchungskommentar 3",
            "OP - Zusatzfeld 1",
            "OP - Zusatzfeld 2",
            "OP - Zusatzfeld 3",
            "OP - Zusatzfeld 4",
            "OP - Zusatzfeld 5",
            "OP - Zusatzfeld 6",
            "OP - Zusatzfeld 7",
            "OP - Zusatzfeld 8",
            "OP - Zusatzfeld 9",
            "OP - Zusatzfeld 10",
            "Konto 2",
            "Kostenstelle Konto 2",
            "Projekt Konto 2",
            "Kostentraeger Konto 2",
            "Geschäftseinheit Konto 2",
            "Geschäftsfeld Konto 2",
            "StS Konto 2",
            "Steuersatz Konto 2",
            "Buchungsbetrag Konto 2",
            "Buchungstext 2",
            "Konzernbewegungsart Konto 2",
            "Verbundenes  Unternehmen Konto 2",
            "Barcode",

        ]

        settings = SettingsSandbox(
            "plugin",
            "pretix_dpsgw_accounting_export",
            self.organizer,
        )
        settings.get("sachkonto")

        base_qs = self.invoices_queryset(form_data)
        qs = (
            base_qs.select_related("order", "order__event", "refers")
            .prefetch_related("order__payments")
            .annotate(
                total_gross=Subquery(
                    InvoiceLine.objects.filter(
                        invoice=OuterRef("pk")
                    ).order_by().values("invoice").annotate(
                        s=Sum("gross_value")
                    ).values("s")
                ),
                total_net=Subquery(
                    InvoiceLine.objects.filter(
                        invoice=OuterRef("pk")
                    ).order_by().values("invoice").annotate(
                        s=Sum(F("gross_value") - F("tax_value"))
                    ).values("s")
                ),
            )
        )

        all_ids = base_qs.order_by("full_invoice_no").values_list(
            "pk", flat=True
        )
        yield self.ProgressSetTotal(total=len(all_ids))

        for ids in chunked_iterable(all_ids, 1000):
            invs = sorted(
                qs.filter(id__in=ids),
                key=lambda k: ids.index(k.pk),
            )
            for i in invs:
                kn = i.event.meta_data['KN']
                if i.event.date_to is None or i.event.date_from == i.event.date_to:
                    buchungstext_datum = date_format(i.date, "d.m.y")
                else:
                    buchungstext_datum = format_date_range(i.event.date_from, i.event.date_to)
                buchungstext = (f"{i.invoice_to_company or i.invoice_to_name}: TN "
                                f"{i.event.name} {buchungstext_datum}"
                                + (f" KN{kn}" if kn else ""))
                projektnummer = "UNBEKANNT ????"
                if kn and len(kn) >= 5:
                    projektnummer = settings.get("kostenstelle") + kn[0:2] + kn[3:5]

                # Distinguish cancellation/Storno and invoice/Rechnung
                # _("Cancellation") if i.is_cancellation else _("Invoice"),

                yield [
                    settings.get("mandant"),
                    date_format(i.date, "m.Y"),
                    date_format(i.date, "SHORT_DATE_FORMAT"),
                    settings.get("belegart"),
                    "",
                    i.full_invoice_no,
                    i.order.full_code,
                    "DEBITOREN_NUMMER HIER",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    i.total_gross if i.total_gross else Decimal("0.00"),
                    buchungstext,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    settings.get("sachkonto"),
                    settings.get("kostenstelle"),
                    projektnummer,
                    "",
                    "",
                    "",
                    settings.get("steuerschluessel"),
                    "",
                    i.total_gross if i.total_gross else Decimal("0.00"),
                    buchungstext,
                    "",
                    "",
                    settings.get("barcodeprefix") + i.full_invoice_no
                ]

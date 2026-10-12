from decimal import Decimal

from django.db.models import Count, Exists, F, OuterRef, Subquery, Sum
from django.utils.formats import date_format
from django.utils.functional import cached_property
from django.utils.translation import (
    gettext, gettext_lazy as _, )

from pretix.base.exporters.invoices import InvoiceDataExporter
from pretix.base.exporters.invoices import chunked_iterable
from pretix.base.models import Invoice, InvoiceLine
from pretix.base.settings import SettingsSandbox
from pretix_barcode_invoice_renderer.utils import format_date_range


# This implementation is based on InvoiceDataExporter from Pretix


## TODO: Ganzes Repo von ChatGPT bewerten lassen, wenn alles gepushed ist

class ExtendedInvoiceDataExporter(InvoiceDataExporter):
    """Invoice data export with an additional full order code column."""

    identifier = "invoicedata_dpsgw_accounting"
    verbose_name = "DPSG Würzburg Buchhaltungs-Export"
    description = "Exportiert die Rechnungsdaten im Format, das für den Buchhaltungsimport genutzt werden kann"

    @property
    def sheets(self):
        return super().sheets + (
            ('lines_aggregated', _('Invoice lines aggregated')),
        )

    @cached_property
    def settings(self) -> SettingsSandbox:
        return SettingsSandbox(
            "plugin",
            "pretix_dpsgw_accounting_export",
            self.organizer,
        )

    def iterate_sheet(self, form_data, sheet):
        _ = gettext

        if sheet == "invoices":
            yield from self.iterate_invoices(form_data)
            return
        elif sheet == "lines":
            yield from self.iterate_lines(form_data)
            return
        elif sheet == "lines_aggregated":
            yield from self.iterate_lines_aggregated(form_data)
            return
        else:
            yield from super().iterate_sheet(form_data, sheet)
            return

    COLUMN_NAMES = [
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

    def iterate_invoices(self, form_data):
        yield self.COLUMN_NAMES

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
                has_additional_products=Exists(
                    InvoiceLine.objects.filter(
                        invoice=OuterRef("pk"),
                        item__admission=False,
                    )
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
                buchungstext = self.get_buchungstext(i)
                # Distinguish cancellation/Storno and invoice/Rechnung
                # _("Cancellation") if i.is_cancellation else _("Invoice"),

                invoice_data = self.prepare_invoice_data(i, i.total_gross, buchungstext)
                sachkonto = self.settings.get("sachkonto") if not i.has_additional_products else _('TODO CONTAINS ADDITIONAL PRODUCTS'),
                steuerschluessel = self.settings.get("steuerschluessel") if not i.has_additional_products else _('TODO CONTAINS ADDITIONAL PRODUCTS'),
                sachkonto_buchung = self.prepare_sachkonto_buchung(i, sachkonto, steuerschluessel, i.total_gross, buchungstext)
                yield combine_line(invoice_data, sachkonto_buchung)

    def iterate_lines(self, form_data):
        yield self.COLUMN_NAMES

        qs = InvoiceLine.objects.annotate(
            invoice_total_gross=Subquery(
                InvoiceLine.objects.filter(
                    invoice=OuterRef('invoice_id')
                ).order_by().values('invoice').annotate(
                    s=Sum('gross_value')
                ).values('s')
            ),
        ).filter(
            invoice__in=self.invoices_queryset(form_data)
        ).order_by('invoice__full_invoice_no', 'position').select_related(
            'invoice', 'invoice__order', 'invoice__refers'
        )
        yield self.ProgressSetTotal(total=qs.count())

        previous_invoice = None
        for l in qs.iterator():
            i = l.invoice
            # Rechnungsdaten nur bei der ersten Zeile ausgeben
            if previous_invoice != i.pk:
                invoice_data = self.prepare_invoice_data(i, l.invoice_total_gross, self.get_buchungstext(i))
                previous_invoice = i.pk
            else:
                invoice_data = [''] * 17

            # 41 leere Spalten und dahinter Zeileninformationen einfügen
            sachkonto = self.settings.get("sachkonto") if l.item.admission else self.settings.get("sachkonto_zusatz")
            steuerschluessel = self.settings.get("steuerschluessel") if l.item.admission else self.settings.get("steuerschluessel_zusatz")
            sachkonto_buchung = self.prepare_sachkonto_buchung(i, sachkonto, steuerschluessel, l.gross_value,
                                                          l.description.replace("<br />", " - "))
            yield combine_line(invoice_data, sachkonto_buchung)

    def iterate_lines_aggregated(self, form_data):
        yield self.COLUMN_NAMES

        invoices = list(
            self.invoices_queryset(form_data)
            .select_related("order", "order__event", "refers")
            .order_by("full_invoice_no")
        )

        invoice_ids = [i.pk for i in invoices]

        base_qs = InvoiceLine.objects.filter(
            invoice_id__in=invoice_ids
        )
        # Gesamtbetrag je Rechnung
        invoice_totals = {
            row["invoice"]: row["total_gross"]
            for row in (
                base_qs
                .values("invoice")
                .annotate(total_gross=Sum("gross_value"))
            )
        }

        # Alle Teilnahme-Produkte einer Rechnung zu einer Zeile zusammenfassen
        admission_qs = (
            base_qs
            .filter(item__admission=True)
            .values("invoice")
            .annotate(
                quantity=Count("id"),
                total_gross=Sum("gross_value"),
            )
        )

        # Zusatzprodukte pro Produkt und Rechnung zusammenfassen
        additional_qs = (
            base_qs
            .filter(item__admission=False)
            .values(
                "invoice",
                "item",
                "item__name",
            )
            .annotate(
                quantity=Count("id"),
                total_gross=Sum("gross_value"),
            )
            .order_by("invoice", "item__name")
        )

        # Nach Rechnung gruppieren, damit wir die Ausgabe in der gleichen
        # Reihenfolge wie bei iterate_lines erzeugen können.
        admission_by_invoice = {row["invoice"]: row for row in admission_qs}
        admission_count = len(admission_by_invoice)

        additional_by_invoice = {}
        additional_count = 0
        for row in additional_qs:
            additional_by_invoice.setdefault(row["invoice"], []).append(row)
            additional_count += 1

        yield self.ProgressSetTotal(total=admission_count + additional_count)

        for i in invoices:
            invoice_data = self.prepare_invoice_data(
                i,
                invoice_totals.get(i.pk, Decimal("0.00")),
                self.get_buchungstext(i),
            )
            first_line = True

            # ------------------------------------------------------------
            # Teilnahme-Produkte
            # ------------------------------------------------------------
            admission = admission_by_invoice.get(i.pk)

            if admission:
                sachkonto_buchung = self.prepare_sachkonto_buchung(i, self.settings.get("sachkonto"), self.settings.get("steuerschluessel"), admission["total_gross"], self.get_buchungstext(i, admission["quantity"]))
                yield combine_line(invoice_data, sachkonto_buchung)
                first_line = False

            # ------------------------------------------------------------
            # Zusatzprodukte
            # ------------------------------------------------------------
            for additional in additional_by_invoice.get(i.pk, []):
                if first_line:
                    first_line = False
                else:
                    invoice_data = [''] * 17

                quantity = f'{additional["quantity"]} x ' if additional["quantity"] > 1 else ''
                sachkonto_buchung = self.prepare_sachkonto_buchung(i, self.settings.get("sachkonto_zusatz"), self.settings.get("steuerschluessel_zusatz"), additional["total_gross"], f'{i.invoice_to_company or i.invoice_to_name}: {quantity}{additional["item__name"]}')
                yield combine_line(invoice_data, sachkonto_buchung)

    @staticmethod
    def get_buchungstext(i: Invoice, quantity=None) -> str:
        kn = i.event.meta_data['KN']
        if i.event.date_to is None or i.event.date_from == i.event.date_to:
            buchungstext_datum = date_format(i.date, "d.m.y")
        else:
            buchungstext_datum = format_date_range(i.event.date_from, i.event.date_to)
        quantity_str = f'{quantity} x ' if quantity and quantity > 1 else ''
        return (f"{i.invoice_to_company or i.invoice_to_name}: {quantity_str}Teilnahme "
                f"{i.event.name} {buchungstext_datum}"
                + (f" KN{kn}" if kn else ""))

    def get_projektnummer(self, i: Invoice) -> str:
        kn = i.event.meta_data['KN']
        projektnummer = "UNBEKANNT ????"
        if kn and len(kn) >= 5:
            projektnummer = self.settings.get("kostenstelle") + kn[0:2] + kn[3:5]
        return projektnummer

    # Invoice data = left part = Grunddaten + Buchung auf Debitorenkonto
    def prepare_invoice_data(self, i, total_gross, buchungstext):
        return [
            self.settings.get("mandant"),
            date_format(i.date, "m.Y"),
            date_format(i.date, "SHORT_DATE_FORMAT"),
            self.settings.get("belegart"),
            "",
            i.full_invoice_no,
            i.order.full_code,
            "DEBITOREN_NUMMER HIER: " + (i.invoice_to_company or i.invoice_to_name),
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            total_gross or Decimal('0.00'),
            buchungstext,
        ]

    # right part = Buchung auf Sachkonto
    def prepare_sachkonto_buchung(self, i: Invoice, sachkonto: str, steuerschluessel: str, betrag,
                                  buchungstext: str) -> list[str]:
        return [
            sachkonto,
            self.settings.get("kostenstelle"),
            (self.get_projektnummer(i)),
            "",
            "",
            "",
            steuerschluessel,
            "",
            betrag if betrag else Decimal("0.00"),
            buchungstext,
            "",
            "",
            self.settings.get("barcodeprefix") + i.full_invoice_no
        ]

def combine_line(invoice_data: list, sachkonto_buchung: list) -> list[str]:
    return invoice_data + ([''] * 41) + sachkonto_buchung

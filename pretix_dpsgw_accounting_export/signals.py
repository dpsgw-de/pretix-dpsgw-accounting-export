# Register your receivers here
from django.dispatch import receiver
from pretix.base.signals import register_multievent_data_exporters

from .exporter import ExtendedInvoiceDataExporter


@receiver(
    register_multievent_data_exporters,
    dispatch_uid="pretix_extended_invoicedata.multievent_exporter",
)
def register_extended_invoicedata_exporter(sender, **kwargs):
    return ExtendedInvoiceDataExporter
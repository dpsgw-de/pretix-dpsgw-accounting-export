from django.utils.translation import gettext_lazy

from . import __version__

try:
    from pretix.base.plugins import PluginConfig, PLUGIN_LEVEL_ORGANIZER
except ImportError:
    raise RuntimeError("Please use pretix 2.7 or above to run this plugin!")


class PluginApp(PluginConfig):
    default = True
    name = "pretix_dpsgw_accounting_export"
    verbose_name = "DPSGW Accounting Export"

    class PretixPluginMeta:
        name = gettext_lazy("DPSGW Accounting Export")
        author = "DPSG Würzburg"
        description = gettext_lazy("Export Invoice Data for Accounting")
        visible = True
        version = __version__
        category = "CUSTOMIZATION"
        compatibility = "pretix>=2025.7"
        navigation_links = []
        level = PLUGIN_LEVEL_ORGANIZER
        settings_links = [
            (
                ("DPSGW Accounting Export", "Einstellungen"),
                "plugins:pretix_dpsgw_accounting_export:settings",
                {},
            ),
        ]

    def ready(self):
        from . import signals  # NOQA

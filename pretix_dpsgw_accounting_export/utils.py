from django.utils.formats import date_format


def format_date_range(date_from, date_to):
    if not date_from:
        return ""

    if not date_to or date_from == date_to:
        return date_format(date_from, "d.m.Y")

    if (
        date_from.year == date_to.year
        and date_from.month == date_to.month
    ):
        # 12.-14.04.2026
        return (
            f"{date_format(date_from, 'd')}.-"
            f"{date_format(date_to, 'd.m.Y')}"
        )

    if date_from.year == date_to.year:
        # 31.03.-04.04.2026
        return (
            f"{date_format(date_from, 'd.m.')}-"
            f"{date_format(date_to, 'd.m.Y')}"
        )

    # 31.12.2026-02.01.2027
    return (
        f"{date_format(date_from, 'd.m.Y')}-"
        f"{date_format(date_to, 'd.m.Y')}"
    )

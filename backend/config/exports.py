"""Making exported spreadsheets safe to open.

A CSV cell beginning with `=`, `+`, `-`, `@`, tab or carriage return is a
*formula* to Excel, LibreOffice and Google Sheets. The file is inert on disk
and dangerous the moment somebody double-clicks it, which is exactly what an
administrator does with an exported gate log.

That matters here more than in most systems, because a good deal of what ends
up in the export is written by people who are not staff. The public
registration form sets a computer's brand, model, colour and serial with no
login at all, and those flow into `device_label` on every scan. So the payload
can be planted by a stranger on a phone and executed weeks later on an
administrator's machine, which is about as clean a delivery route as this
system has.

The fix is the boring one: prefix the cell with an apostrophe so the
spreadsheet treats it as text. The apostrophe is not shown in the cell, and it
is the mitigation OWASP recommends.
"""

DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value):
    """Return `value` as a cell that no spreadsheet will treat as a formula."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(DANGEROUS_PREFIXES):
        return "'" + text
    return text


def csv_safe_row(values):
    return [csv_safe(value) for value in values]

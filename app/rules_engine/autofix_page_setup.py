"""Page-level setup fixes: title page numbering suppression."""
from __future__ import annotations

import logging
import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

logger = logging.getLogger(__name__)

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_PAGE_FIELD_RE = re.compile(r"instrText[^>]*>[^<]*PAGE", re.IGNORECASE)


def suppress_title_page_number(doc, details: list[str]) -> bool:
    """Hide the page number on the first page (title page).

    Sets ``different_first_page_header_footer = True`` on the first
    section and ensures the first-page footer contains no PAGE field
    (clearing it if necessary so no "1" appears on the title page).
    """
    sections = doc.sections
    if not sections:
        return False

    sect = sections[0]
    changed = False

    if not sect.different_first_page_header_footer:
        sect.different_first_page_header_footer = True
        changed = True

    # Access first-page footer and clear any PAGE field from it.
    try:
        fp_footer = sect.first_page_footer
    except Exception:
        fp_footer = None

    if fp_footer is not None:
        footer_xml = fp_footer._element.xml
        if _PAGE_FIELD_RE.search(footer_xml):
            for child in list(fp_footer._element):
                fp_footer._element.remove(child)
            changed = True

    # Also clear the first-page header if it somehow has PAGE field
    try:
        fp_header = sect.first_page_header
    except Exception:
        fp_header = None

    if fp_header is not None:
        header_xml = fp_header._element.xml
        if _PAGE_FIELD_RE.search(header_xml):
            for child in list(fp_header._element):
                fp_header._element.remove(child)
            changed = True

    if changed:
        details.append("Нумерация: убран номер страницы с титульного листа")
    return changed

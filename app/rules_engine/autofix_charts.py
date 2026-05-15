"""Chart-related autofix passes that operate at the OOXML level.

Word stores embedded charts as separate ``word/charts/chartN.xml`` parts.
Their structure is not exposed by ``python-docx``, so we manipulate the
zipped XML directly inside :func:`fix_chart_titles_in_zip`.

Currently the only supported pass is *suppress empty chart titles*: a
chart that contains a ``<c:title>`` block without any actual ``<a:t>``
text and whose ``<c:autoTitleDeleted>`` flag is ``"0"`` makes Word render
an automatically generated title built from the first series name (e.g.
«Количественные результаты изучения концентрации внимания …»). The
caption is then duplicated as a regular paragraph below the figure
(«Рисунок 1 — …»), which is what reviewers flag as «лишнее название
внутри рисунка». Setting ``<c:autoTitleDeleted val="1"/>`` removes the
auto-generated heading without touching anything else in the chart.
"""
from __future__ import annotations

import logging
import re
import shutil
import zipfile
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)

_NS = {
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
_CHART_PATH_RE = re.compile(r"^word/charts/chart\d+\.xml$", re.IGNORECASE)


_PLACEHOLDER_TITLES = frozenset({
    "название диаграммы",
    "chart title",
    "title",
    "заголовок диаграммы",
})


def _title_has_text(title_el) -> bool:
    """Return True if the chart title carries meaningful (non-placeholder)
    ``<a:t>`` text. Default Word placeholders like "Название диаграммы"
    are treated as empty."""
    fragments: list[str] = []
    for t_el in title_el.iter(f"{{{_NS['a']}}}t"):
        if (t_el.text or "").strip():
            fragments.append((t_el.text or "").strip())
    if not fragments:
        return False
    combined = " ".join(fragments).lower()
    return combined not in _PLACEHOLDER_TITLES


def _suppress_chart_title(xml_bytes: bytes) -> tuple[bytes, bool]:
    """Return updated ``chartN.xml`` bytes and whether anything changed.

    Strategy:
      * If ``<c:title>`` is missing → leave file untouched.
      * If ``<c:title>`` carries explicit meaningful text → leave it alone.
      * Otherwise remove ``<c:title>`` entirely and set
        ``<c:autoTitleDeleted val="1"/>`` so Word neither shows
        the placeholder text nor auto-generates a title from the series.
    """
    try:
        root = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError:
        logger.debug("autofix_charts: chart XML failed to parse, skipping")
        return xml_bytes, False

    chart_tag = f"{{{_NS['c']}}}chart"
    chart_el = root.find(chart_tag)
    if chart_el is None:
        return xml_bytes, False

    title_tag = f"{{{_NS['c']}}}title"
    title_el = chart_el.find(title_tag)
    if title_el is None:
        return xml_bytes, False
    if _title_has_text(title_el):
        return xml_bytes, False

    chart_el.remove(title_el)

    auto_tag = f"{{{_NS['c']}}}autoTitleDeleted"
    auto_el = chart_el.find(auto_tag)
    if auto_el is None:
        auto_el = etree.SubElement(chart_el, auto_tag)
        chart_el.remove(auto_el)
        chart_el.insert(0, auto_el)
    auto_el.set("val", "1")

    return etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True,
    ), True


def fix_chart_titles_in_zip(path: Path, details: list[str]) -> bool:
    """Suppress auto-generated chart titles inside an existing DOCX file.

    Operates on a temporary copy and atomically swaps it back so the
    target file is never left half-written. Returns True if at least one
    chart was modified.
    """
    if not path.exists():
        return False
    try:
        with zipfile.ZipFile(str(path), "r") as zf:
            chart_names = [n for n in zf.namelist() if _CHART_PATH_RE.match(n)]
    except zipfile.BadZipFile:
        logger.warning("autofix_charts: %s is not a valid DOCX zip", path)
        return False

    if not chart_names:
        return False

    tmp = path.with_name(path.stem + ".charts.tmp.docx")
    changed_charts = 0
    try:
        with zipfile.ZipFile(str(path), "r") as src_zf:
            with zipfile.ZipFile(str(tmp), "w", zipfile.ZIP_DEFLATED) as dst_zf:
                for info in src_zf.infolist():
                    data = src_zf.read(info.filename)
                    if info.filename in chart_names:
                        new_data, changed = _suppress_chart_title(data)
                        if changed:
                            changed_charts += 1
                            data = new_data
                    dst_zf.writestr(info, data)
    except Exception:
        logger.exception("autofix_charts: failed while rewriting %s", path)
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        return False

    if changed_charts == 0:
        try:
            tmp.unlink()
        except OSError:
            pass
        return False

    try:
        shutil.move(str(tmp), str(path))
    except OSError:
        logger.exception("autofix_charts: cannot replace %s with %s", path, tmp)
        return False

    details.append(
        f"Диаграммы: автозаголовок убран у {changed_charts} диаграмм(ы)"
    )
    return True

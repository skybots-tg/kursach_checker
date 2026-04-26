"""Распределение вертикальных интервалов на титульном листе (блоки → город/год внизу)."""
from __future__ import annotations

import logging
import re

from docx.shared import Pt

logger = logging.getLogger(__name__)

_PERSONNEL_RE = re.compile(
    r"\bвыполнил[аи]?|\bпроверил",
    re.IGNORECASE,
)
_REFERAT_WORD_RE = re.compile(r"\bреферат\b", re.IGNORECASE)
_BLOCK1_STRONG_HINT = re.compile(
    r"министерство|федеральн|университет|институт|школа\s|департамент|кафедр|"
    r"\bдвфу\b|фгаоу|образовательн(?:ое|ого)\s+учрежден",
    re.IGNORECASE,
)
_YEAR_STRICT = re.compile(r"^\d{4}\s*$")
_CITY_YEAR_ONE = re.compile(
    r"^(?:г\.\s*)?([А-ЯЁа-яЁё][А-ЯЁа-яЁё\-\s\w]*)\s*,\s*(\d{4})\s*$",
    re.IGNORECASE,
)
_PERSONNEL_SATELLITE_RE = re.compile(
    r"\d{4}|«|»|_{3,}|апрел|январ|феврал|март|ма[яй]|июн|июл|август|сентяб|октяб|нояб|декаб",
    re.IGNORECASE,
)


def _collapse(text: str) -> str:
    return re.sub(r"[\n\r\t\xa0]+", " ", (text or "")).strip()


def _mostly_uppercase_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def _is_topic_caps_line(c: str) -> bool:
    if not c or _BLOCK1_STRONG_HINT.search(c):
        return False
    if len(c) < 10 or len(c) > 190:
        return False
    if _REFERAT_WORD_RE.search(c):
        return False
    return _mostly_uppercase_ratio(c) >= 0.78


def _one_line_city_year(collapsed: str) -> bool:
    return _CITY_YEAR_ONE.match(collapsed.strip()) is not None


def _find_footer_city_idx(paras, body_start: int) -> int | None:
    for i in range(body_start - 1, -1, -1):
        raw = (paras[i].text or "").strip()
        if not raw:
            continue
        col = _collapse(paras[i].text or "")
        if _one_line_city_year(col):
            return i
        if _YEAR_STRICT.match(raw):
            j = i - 1
            while j >= 0 and not (paras[j].text or "").strip():
                j -= 1
            if j < 0:
                return None
            return j
    return None


def _find_personnel_range(paras, city_idx: int) -> tuple[int, int] | None:
    """Первый и последний абзацы блока исполнителя (строго выше city_idx)."""
    end = city_idx - 1
    while end >= 0 and not (paras[end].text or "").strip():
        end -= 1
    if end < 0:
        return None
    marker_at: int | None = None
    for u in range(end, -1, -1):
        c = _collapse(paras[u].text or "")
        if _PERSONNEL_RE.search(c):
            marker_at = u
            break
    if marker_at is None:
        return None
    start = marker_at
    while start - 1 >= 0:
        c = _collapse(paras[start - 1].text or "")
        if not c:
            start -= 1
            continue
        if _REFERAT_WORD_RE.search(c):
            break
        if _PERSONNEL_RE.search(c):
            start -= 1
            continue
        if len(c) < 130 and _PERSONNEL_SATELLITE_RE.search(c):
            start -= 1
            continue
        break
    return start, end


def _find_referat_span(paras, personnel_start: int) -> tuple[int, int] | None:
    referat_idx: int | None = None
    for k in range(personnel_start):
        t = (paras[k].text or "").strip()
        if not t:
            continue
        if _REFERAT_WORD_RE.search(_collapse(t)):
            referat_idx = k
            break
    if referat_idx is None:
        return None
    referat_start = referat_idx
    while referat_start - 1 >= 0:
        c = _collapse(paras[referat_start - 1].text or "")
        if not c:
            referat_start -= 1
            continue
        if _PERSONNEL_RE.search(c):
            break
        if _is_topic_caps_line(c):
            break
        if _BLOCK1_STRONG_HINT.search(c) and _mostly_uppercase_ratio(c) < 0.55:
            break
        low = c.lower()
        if any(
            x in low
            for x in (
                "образовательной",
                "направлению",
                "направлен",
                "программ",
                "бакалавр",
                "магистр",
                "специалитет",
            )
        ):
            referat_start -= 1
            continue
        break
    referat_end = referat_idx
    while referat_end + 1 < personnel_start:
        c = _collapse(paras[referat_end + 1].text or "")
        if not c:
            break
        if _PERSONNEL_RE.search(c):
            break
        low = c.lower()
        if any(
            x in low
            for x in (
                "образовательной",
                "направлению",
                "направлен",
                "программ",
                "бакалавр",
                "магистр",
                "специалитет",
            )
        ):
            referat_end += 1
            continue
        break
    if referat_end >= personnel_start or referat_start >= personnel_start:
        return None
    return referat_start, referat_end


def _find_topic_before_referat(paras, referat_start: int) -> int | None:
    t = referat_start - 1
    while t >= 0 and not (paras[t].text or "").strip():
        t -= 1
    if t < 0:
        return None
    c = _collapse(paras[t].text or "")
    if _is_topic_caps_line(c):
        return t
    return None


def _rough_title_content_pt(doc, body_start: int) -> float:
    tot = 0.0
    for i in range(body_start):
        p = doc.paragraphs[i]
        t = (p.text or "").strip()
        pf = p.paragraph_format
        if pf.space_before is not None:
            tot += pf.space_before.pt
        if pf.space_after is not None:
            tot += pf.space_after.pt
        if not t:
            continue
        lines = max(1, len(t.split("\n")))
        fs = 14.0
        for r in p.runs:
            if r.font.size:
                fs = r.font.size.pt
                break
        ls = pf.line_spacing
        if ls is None:
            mult = 1.5
        elif isinstance(ls, float):
            mult = max(1.0, float(ls))
        else:
            mult = 1.5
        tot += lines * fs * mult * 1.06
    return tot


def _usable_page_inner_pt(doc) -> float:
    sec = doc.sections[0]
    return (sec.page_height - sec.top_margin - sec.bottom_margin).pt


def distribute_title_page_vertical_blocks(
    doc, body_start: int, details: list[str],
) -> bool:
    """Задать space_before на границах блоков, чтобы заполнить страницу и опустить город/год."""
    if body_start < 4:
        return False
    paras = doc.paragraphs
    city_idx = _find_footer_city_idx(paras, body_start)
    if city_idx is None:
        return False
    pr = _find_personnel_range(paras, city_idx)
    if pr is None:
        return False
    personnel_start, personnel_end = pr
    if personnel_end >= city_idx:
        return False
    span = _find_referat_span(paras, personnel_start)
    if span is None:
        return False
    referat_start, referat_end = span
    if referat_end >= personnel_start:
        return False
    topic_idx = _find_topic_before_referat(paras, referat_start)

    boundaries: list[int] = []
    if topic_idx is not None:
        boundaries.append(topic_idx)
    boundaries.extend([referat_start, personnel_start, city_idx])

    usable = _usable_page_inner_pt(doc)
    est = _rough_title_content_pt(doc, body_start)
    reserve_pt = 64.0
    slack = usable - est - reserve_pt
    if slack < 72.0:
        logger.info(
            "title layout: slack %.1f pt too small (usable %.1f, est %.1f)",
            slack,
            usable,
            est,
        )
        return False

    n = len(boundaries)
    if n == 4:
        weights = [1.0, 1.0, 1.0, 2.0]
    elif n == 3:
        weights = [1.0, 1.0, 2.0]
    else:
        return False
    wsum = sum(weights[:n])
    raw_gaps = [slack * weights[i] / wsum for i in range(n)]
    max_gap = 220.0
    gaps = [min(g, max_gap) for g in raw_gaps]

    changed = False
    for idx, gap in zip(boundaries, gaps):
        p = paras[idx]
        pf = p.paragraph_format
        cur = pf.space_before.pt if pf.space_before is not None else 0.0
        if abs(cur - gap) > 0.75:
            pf.space_before = Pt(round(gap, 1))
            changed = True
    if changed:
        details.append(
            "Титульный лист: интервалы между блоками (шапка — тема — реферат — исполнитель — город)"
        )
    return changed

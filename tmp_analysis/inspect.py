"""Inspect the docx structure: paragraphs, tables, page breaks."""
import sys
import zipfile
import re

path = sys.argv[1] if len(sys.argv) > 1 else 'tmp_analysis/source.docx'
with zipfile.ZipFile(path) as z:
    with z.open('word/document.xml') as f:
        data = f.read().decode('utf-8')

# Walk top-level body children in order
body_match = re.search(r'<w:body>(.*)</w:body>', data, flags=re.DOTALL)
body_xml = body_match.group(1)

# Parse top-level <w:p> and <w:tbl> in order
items = []
i = 0
while i < len(body_xml):
    # find next opening tag w:p, w:tbl, w:sectPr at top level
    m = re.search(r'<w:(p|tbl|sectPr)\b', body_xml[i:])
    if not m:
        break
    tag = m.group(1)
    abs_start = i + m.start()
    # find closing tag at same depth
    open_re = re.compile(rf'<w:{tag}\b[^>]*?(/?)>')
    close_re = re.compile(rf'</w:{tag}>')
    pos = abs_start
    depth = 0
    end_pos = None
    while True:
        nxt_open = open_re.search(body_xml, pos + 1)
        nxt_close = close_re.search(body_xml, pos + 1)
        # But also handle self-closed open <w:p .../>
        first_match = open_re.search(body_xml, pos)
        if first_match and first_match.start() == pos:
            self_close = first_match.group(1) == '/'
            if self_close:
                end_pos = first_match.end()
                break
            depth += 1
            pos = first_match.end()
            continue
        if nxt_open and (not nxt_close or nxt_open.start() < nxt_close.start()):
            self_close = nxt_open.group(1) == '/'
            if not self_close:
                depth += 1
            pos = nxt_open.end()
        elif nxt_close:
            depth -= 1
            pos = nxt_close.end()
            if depth == 0:
                end_pos = pos
                break
        else:
            break
    if end_pos is None:
        break
    items.append((tag, body_xml[abs_start:end_pos]))
    i = end_pos

# Number paragraphs only (top-level)
p_idx = 0
for kind, blob in items:
    if kind == 'p':
        text_runs = re.findall(r'<w:t[^>]*>([^<]*)</w:t>', blob)
        text = ''.join(text_runs).strip()
        has_pb_before = '<w:pageBreakBefore' in blob
        has_brk_page = re.search(r'<w:br\s+w:type="page"', blob) is not None
        pstyle = re.search(r'<w:pStyle\s+w:val="([^"]+)"', blob)
        sty = pstyle.group(1) if pstyle else ''
        ind = re.search(r'<w:ind\b([^/>]*)/?>', blob)
        ind_attrs = ind.group(1) if ind else ''
        first_line = re.search(r'w:firstLine="([^"]+)"', ind_attrs)
        left = re.search(r'w:left="([^"]+)"', ind_attrs)
        spacing = re.search(r'<w:spacing\b([^/>]*)/?>', blob)
        sp_after = ''
        sp_before = ''
        if spacing:
            sa = re.search(r'w:after="([^"]+)"', spacing.group(1))
            sb = re.search(r'w:before="([^"]+)"', spacing.group(1))
            if sa:
                sp_after = sa.group(1)
            if sb:
                sp_before = sb.group(1)
        flag = ''
        if has_pb_before:
            flag += ' pgBrkBfr'
        if has_brk_page:
            flag += ' br=page'
        fl_str = first_line.group(1) if first_line else ''
        lf_str = left.group(1) if left else ''
        ind_str = ''
        if fl_str or lf_str:
            ind_str = f'fl={fl_str},left={lf_str}'
        sp_str = ''
        if sp_after or sp_before:
            sp_str = f'a={sp_after},b={sp_before}'
        print(f'{p_idx:3} P [{sty:10}]{flag:18} ind=[{ind_str:18}] sp=[{sp_str:18}] | {text[:80]!r}')
        p_idx += 1
    elif kind == 'tbl':
        # Show table caption row if any
        first_text = re.search(r'<w:t[^>]*>([^<]*)</w:t>', blob)
        ft = first_text.group(1) if first_text else ''
        rows = len(re.findall(r'<w:tr\b', blob))
        # tblPr block
        tblpr = re.search(r'<w:tblPr>(.*?)</w:tblPr>', blob, flags=re.DOTALL)
        tblpr_summary = tblpr.group(1)[:120] if tblpr else ''
        print(f'    TBL rows={rows} firstcell={ft[:40]!r}  tblPr={tblpr_summary}')
    elif kind == 'sectPr':
        print(f'    SECT')

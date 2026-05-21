"""
Convert and improve Notion/Pandoc tables for PDF output.

Pandoc emits longtable environments with p{} columns, minipages, and LTR
wrappers. This module rebuilds them as compact table/tabularx + booktabs.
"""

import re

MINIPAGE_RE = re.compile(
    r"\\begin\{minipage\}\[t\]\{\\linewidth\}\\raggedright\s*"
    r"(.*?)\\end\{minipage\}",
    re.DOTALL,
)


def _read_braced_argument(text, start):
    if start >= len(text) or text[start] != "{":
        return None, start
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : i], i + 1
        i += 1
    return None, start


def _find_environment(text, name, start=0):
    begin = f"\\begin{{{name}}}"
    end = f"\\end{{{name}}}"
    i = text.find(begin, start)
    if i == -1:
        return None
    j = text.find(end, i)
    if j == -1:
        return None
    pos = i + len(begin)
    if pos < len(text) and text[pos] == "[":
        depth = 1
        pos += 1
        while pos < len(text) and depth:
            if text[pos] == "[":
                depth += 1
            elif text[pos] == "]":
                depth -= 1
            pos += 1
    if pos < len(text) and text[pos] == "{":
        _, pos = _read_braced_argument(text, pos)
    return {
        "start": i,
        "end": j + len(end),
        "preamble": text[i:pos],
        "body": text[pos:j],
    }


def _count_columns_from_preamble(preamble):
    m = re.search(
        r"\\begin\{longtable\}(?:\[[^\]]*\])?\{(@\{\})?(.*?)(@\{\})?\}\s*$",
        preamble,
        re.DOTALL,
    )
    if not m:
        return 0
    spec = m.group(2) or ""
    if re.fullmatch(r"[lcr\s]+", spec.replace("@", "").strip()):
        return len(spec.replace("@", "").strip())
    cols = len(re.findall(r"\\real\{", spec))
    if cols:
        return cols
    return max(1, spec.count("p{") + spec.count("X") + spec.count("l") + spec.count("c"))


def _split_row(line):
    """Split table cells on & while respecting nested braces."""
    cells = []
    buf = []
    depth = 0
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "{":
            depth += 1
            buf.append(ch)
        elif ch == "}":
            depth = max(0, depth - 1)
            buf.append(ch)
        elif ch == "&" and depth == 0:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf).strip())
    return cells


def _clean_minipage_text(text):
    text = text.strip()
    text = re.sub(r"\\strut\s*$", "", text)
    text = re.sub(r"\\\\\s*\n\s*", r" \\\\ ", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    return text.strip()


def _clean_cell(cell):
    cell = cell.strip()
    cell = re.sub(r"^\{\}", "", cell)
    cell = re.sub(r"\\strut\s*$", "", cell)
    cell = MINIPAGE_RE.sub(
        lambda m: rf"\shortstack[l]{{{_clean_minipage_text(m.group(1))}}}",
        cell,
    )
    cell = re.sub(r"\n{2,}", " ", cell)
    return cell


def _normalize_body(body):
    """Replace minipages before splitting rows on \\."""
    return MINIPAGE_RE.sub(
        lambda m: rf"\shortstack[l]{{{_clean_minipage_text(m.group(1))}}}",
        body,
    )


def _extract_data_rows(body):
    """Extract data rows after stripping booktabs header repetition."""
    body = re.sub(
        r"\\caption\{[^}]*\}\\label\{[^}]+\}\s*\\tabularnewline",
        "",
        body,
    )
    body = re.sub(r"\\label\{[^}]+\}\\tabularnewline", "", body)
    body = re.sub(r"\\endfirsthead.*?\\endhead", "", body, flags=re.DOTALL)
    body = re.sub(r"\\toprule\\noalign\{\}", "", body)
    body = re.sub(r"\\midrule\\noalign\{\}", "", body)
    body = re.sub(r"\\bottomrule\\noalign\{\}", "", body)
    body = re.sub(r"\\endlastfoot", "", body)
    body = re.sub(r"\\endhead\s*", "", body)
    body = _normalize_body(body)

    rows = []
    for chunk in re.split(r"(?<!\\)\\\\\s*\n", body):
        chunk = chunk.strip()
        if not chunk:
            continue
        if chunk.startswith("\\") and "&" not in chunk:
            continue
        if "&" not in chunk:
            continue
        rows.append([_clean_cell(c) for c in _split_row(chunk)])
    return rows


def _column_spec(n_cols, rows):
    """Use X columns for multiline text; plain l columns for compact math tables."""
    use_x = False
    for row in rows:
        for cell in row:
            if (
                r"\shortstack" in cell
                or len(cell) > 48
                or re.search(r"\\textbf", cell)
                or re.search(r"[àèéìòù]", cell, re.I)
            ):
                use_x = True
                break
        if use_x:
            break
    if use_x:
        col = " ".join([r">{\raggedright\arraybackslash}X"] * n_cols)
        return rf"@{{}}{col}@{{}}", True
    return "@{}" + "l" * n_cols + "@{}", False


def _rebuild_table(rows):
    if not rows:
        return None
    n = max(len(r) for r in rows)
    rows = [r + [""] * (n - len(r)) for r in rows]
    spec, use_tabularx = _column_spec(n, rows)
    if use_tabularx:
        env_begin = rf"\begin{{tabularx}}{{\linewidth}}{{{spec}}}"
        env_end = r"\end{tabularx}"
    else:
        env_begin = rf"\begin{{tabular}}{{{spec}}}"
        env_end = r"\end{tabular}"
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\small",
        env_begin,
        r"\toprule",
    ]
    if len(rows) >= 2:
        hdr = []
        for c in rows[0]:
            hdr.append("{" + c + "}" if r"\shortstack" in c else c)
        lines.append(" & ".join(hdr) + r" \\")
        lines.append(r"\midrule")
        body_rows = rows[1:]
    else:
        body_rows = rows
    for row in body_rows:
        cells = []
        for c in row:
            if r"\shortstack" in c:
                cells.append("{" + c + "}")
            else:
                cells.append(c)
        lines.append(" & ".join(cells) + r" \\")
    lines.extend([r"\bottomrule", env_end, r"\end{table}"])
    return "\n".join(lines)


def _strip_label_prefix(cell):
    """Remove empty {} left by Pandoc after Notion property icons were removed."""
    return re.sub(r"^\{\}", "", cell.strip())


def _is_key_value_table(rows):
    """Notion cover properties: every row is label | value (no header row)."""
    if not rows or not all(len(r) == 2 for r in rows):
        return False
    labels = [_strip_label_prefix(r[0]) for r in rows]
    if not labels or any(not lb for lb in labels):
        return False
    if any(len(lb) > 120 for lb in labels):
        return False
    return True


def _rebuild_key_value_table(rows):
    """Two-column property table: all rows are data (not header + body)."""
    if not rows:
        return None
    spec = (
        r"@{} >{\raggedright\arraybackslash}p{0.34\linewidth} "
        r">{\raggedright\arraybackslash}p{0.62\linewidth} @{}"
    )
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\small",
        rf"\begin{{tabular}}{{{spec}}}",
        r"\toprule",
    ]
    for row in rows:
        label = _strip_label_prefix(row[0])
        value = row[1].strip()
        if r"\shortstack" in value:
            value = "{" + value + "}"
        label_tex = r"\textbf{" + label + "}" if label else ""
        lines.append(f"{label_tex} & {value} \\\\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def improve_longtable_block(block):
    env = _find_environment(block, "longtable")
    if not env:
        return block, False
    rows = _extract_data_rows(env["body"])
    if len(rows) < 1:
        return block, False
    if _is_key_value_table(rows):
        rebuilt = _rebuild_key_value_table(rows)
    else:
        rebuilt = _rebuild_table(rows)
    if not rebuilt:
        return block, False
    return rebuilt, True


def improve_tables_in_document(text):
    """Replace Pandoc longtables with table+tabular/tabularx; strip LTR wrappers."""
    if r"\usepackage{tabularx}" not in text:
        text = text.replace(
            r"\usepackage{longtable,booktabs,array}",
            "\\usepackage{longtable,booktabs,array}\n\\usepackage{tabularx}",
            1,
        )
    text = text.replace(
        "\\usepackage{longtable,booktabs,array}\\n\\usepackage{tabularx}\\n\\usepackage{makecell}",
        "\\usepackage{longtable,booktabs,array}\n\\usepackage{tabularx}",
    )

    text = re.sub(
        r"\\begin\{LTR\}\s*\n(\\begin\{longtable\})",
        r"\1",
        text,
    )
    text = re.sub(
        r"(\\end\{longtable\})\s*\n\\end\{LTR\}",
        r"\1",
        text,
    )

    count = 0
    pos = 0
    out = []
    while True:
        idx = text.find(r"\begin{longtable}", pos)
        if idx == -1:
            out.append(text[pos:])
            break
        out.append(text[pos:idx])
        env = _find_environment(text, "longtable", idx)
        if not env:
            out.append(text[idx:])
            break
        chunk = text[env["start"] : env["end"]]
        new_chunk, ok = improve_longtable_block(chunk)
        if ok:
            count += 1
            out.append(new_chunk)
        else:
            out.append(chunk)
        pos = env["end"]

    return "".join(out), count

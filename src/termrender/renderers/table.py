"""Table renderer for termrender."""

from __future__ import annotations

from termrender.blocks import Block
from termrender.style import style, visual_len, visual_ljust, visual_center, render_spans, wrap_text


def _align_cell(text: str, width: int, align: str | None) -> str:
    if align == "center":
        return visual_center(text, width)
    elif align == "right":
        vl = visual_len(text)
        if vl < width:
            return " " * (width - vl) + text
        return text
    else:
        return visual_ljust(text, width)


def render(block: Block, color: bool) -> list[str]:
    headers: list[list] = block.attrs.get("headers", [])
    rows: list[list[list]] = block.attrs.get("rows", [])
    aligns: list[str | None] = block.attrs.get("aligns", [])
    w = block.width or 80

    n_cols = max(len(headers), max((len(r) for r in rows), default=0))
    if n_cols == 0:
        return []

    # Render all cells to plain text for width calculation
    rendered_headers = [render_spans(headers[i], False) if i < len(headers) else "" for i in range(n_cols)]
    rendered_rows = [
        [render_spans(row[i], False) if i < len(row) else "" for i in range(n_cols)]
        for row in rows
    ]

    # Calculate natural column widths (minimum 3)
    col_widths = [
        max(3, visual_len(rendered_headers[i]), *(visual_len(r[i]) for r in rendered_rows))
        for i in range(n_cols)
    ]

    # Total width: borders + padding (each cell has 1 space padding on each side)
    # Layout: │ cell │ cell │  => n_cols + 1 borders + n_cols * 2 padding
    total = sum(col_widths) + n_cols * 2 + (n_cols + 1)

    # Distribute proportionally if overflow
    if total > w:
        available = w - n_cols * 2 - (n_cols + 1)
        available = max(available, n_cols * 3)
        total_natural = sum(col_widths)
        if total_natural > 0:
            col_widths = [
                max(3, round(cw / total_natural * available))
                for cw in col_widths
            ]

    # Wrap cell content to column widths
    wrapped_headers = [wrap_text(rendered_headers[i], col_widths[i]) for i in range(n_cols)]
    wrapped_rows = [
        [wrap_text(row[i], col_widths[i]) for i in range(n_cols)]
        for row in rendered_rows
    ]

    def render_multiline_row(wrapped_cells: list[list[str]], bold: bool) -> list[str]:
        row_height = max((len(c) for c in wrapped_cells), default=1)
        out: list[str] = []
        for line_idx in range(row_height):
            parts: list[str] = []
            for i, cell_lines in enumerate(wrapped_cells):
                text = cell_lines[line_idx] if line_idx < len(cell_lines) else ""
                align = aligns[i] if i < len(aligns) else None
                padded = _align_cell(text, col_widths[i], align)
                if bold and color:
                    padded = style(padded, bold=True)
                parts.append(" " + padded + " ")
            line = "│" + "│".join(parts) + "│"
            out.append(visual_ljust(line, w))
        return out

    def separator(left: str, mid: str, right: str) -> str:
        segs = ["─" * (col_widths[i] + 2) for i in range(n_cols)]
        line = left + mid.join(segs) + right
        return visual_ljust(line, w)

    lines: list[str] = []
    lines.append(separator("┌", "┬", "┐"))
    lines.extend(render_multiline_row(wrapped_headers, bold=True))
    lines.append(separator("├", "┼", "┤"))
    for wr in wrapped_rows:
        lines.extend(render_multiline_row(wr, bold=False))
    lines.append(separator("└", "┴", "┘"))

    return lines

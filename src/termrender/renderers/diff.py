"""Unified diff renderer for termrender."""

from __future__ import annotations

from termrender.blocks import Block
from termrender.renderers.borders import render_box
from termrender.style import style, visual_ljust, visual_len


def _classify(line: str) -> tuple[str, str | None]:
    """Return (gutter_char, color) for a diff line."""
    if not line:
        return (" ", None)
    first = line[0]
    if first == "+":
        return ("+", "green")
    if first == "-":
        return ("-", "red")
    if first == "@":
        return ("@", "magenta")
    return (" ", None)


def render(block: Block, color: bool, render_child=None) -> list[str]:
    """Render a diff block with colored +/- gutters inside a box."""
    source = block.attrs.get("source", "")
    title = block.attrs.get("title")
    raw_lines = source.split("\n") if source else [""]
    if raw_lines and raw_lines[-1] == "":
        raw_lines = raw_lines[:-1]
    if not raw_lines:
        raw_lines = [""]

    # content_w accounts for borders + 1-space padding each side
    content_w = max((block.width or 0) - 2 * visual_len("│") - 2, 1)

    content_lines: list[str] = []
    for raw in raw_lines:
        gutter, line_color = _classify(raw)
        body = raw[1:] if raw and raw[0] in "+-@ " else raw
        # Trim/pad content to content_w
        line_text = gutter + " " + body
        if visual_len(line_text) > content_w:
            line_text = line_text[:content_w]
        line_text = visual_ljust(line_text, content_w)
        if line_color:
            styled = style(line_text, color=line_color, enabled=color)
        else:
            styled = style(line_text, dim=True, enabled=color)
        content_lines.append(styled)

    return render_box(
        content_lines,
        width=block.width,
        color=color,
        title=title or "diff",
        dim=True,
    )

"""KPI / stat tile renderer for termrender."""

from __future__ import annotations

from typing import Callable

from termrender.blocks import Block
from termrender.renderers.borders import render_box
from termrender.style import style, visual_center, visual_len, visual_ljust


def _resolve_trend(delta: str | None, trend: str | None) -> tuple[str, str | None]:
    """Pick an arrow + color from explicit trend or by inspecting delta sign."""
    if trend:
        if trend == "up":
            return ("▲", "green")
        if trend == "down":
            return ("▼", "red")
        if trend == "flat":
            return ("▶", "yellow")
    if delta:
        d = delta.strip()
        if d.startswith("+"):
            return ("▲", "green")
        if d.startswith("-"):
            return ("▼", "red")
    return ("•", None)


def render(
    block: Block, color: bool, render_child: Callable[[Block, bool], list[str]]
) -> list[str]:
    """Render a stat tile: label, large value, optional delta, optional caption."""
    w = block.width or 30
    label = block.attrs.get("label", "")
    value = block.attrs.get("value", "")
    delta = block.attrs.get("delta")
    trend = block.attrs.get("trend")
    explicit_color = block.attrs.get("color")

    arrow, trend_color = _resolve_trend(delta, trend)

    # Inner content width inside the box (1 space pad each side + 2 borders)
    border_v = visual_len("│")
    content_w = max(w - 2 * border_v - 2, 1)

    content_lines: list[str] = []

    # Label — dim, left aligned
    label_line = style(label, dim=True, enabled=color)
    content_lines.append(visual_ljust(label_line, content_w))

    # Value — bold, larger feel, centered
    value_color = explicit_color or "yellow"
    value_styled = style(str(value), bold=True, color=value_color, enabled=color)
    content_lines.append(visual_center(value_styled, content_w))

    # Delta line
    if delta:
        delta_text = f"{arrow} {delta}"
        delta_styled = style(delta_text, color=trend_color, bold=True, enabled=color) if trend_color else delta_text
        content_lines.append(visual_ljust(delta_styled, content_w))

    # Optional caption: render children (e.g. paragraph) and append
    for child in block.children:
        child_lines = render_child(child, color)
        for cl in child_lines:
            # Strip child's outer padding and reflow inside our content_w
            content_lines.append(visual_ljust(cl, content_w))

    border_color = explicit_color
    title_color = None if explicit_color else "yellow"
    return render_box(
        content_lines,
        width=w,
        color=color,
        title=None,
        border_color=border_color,
        title_color=title_color,
        dim=color and not explicit_color,
    )

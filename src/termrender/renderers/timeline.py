"""Timeline renderer for termrender — native ASCII vertical timeline."""

from __future__ import annotations

from termrender.blocks import Block
from termrender.style import style, visual_len, visual_ljust


def render(block: Block, color: bool, render_child=None) -> list[str]:
    """Render a vertical timeline with date markers and event text."""
    w = block.width or 60
    title = block.attrs.get("title")
    entries = block.attrs.get("entries", [])
    accent = block.attrs.get("color", "cyan")

    if not entries:
        if title:
            return [visual_ljust(style(title, bold=True, enabled=color), w)]
        return [visual_ljust("", w)]

    date_w = max(visual_len(e["date"]) for e in entries)

    lines: list[str] = []
    if title:
        lines.append(visual_ljust(style(title, bold=True, enabled=color), w))

    bullet = style("●", color=accent, bold=True, enabled=color)
    bar = style("│", color=accent, dim=True, enabled=color)

    event_w = max(w - date_w - 4, 5)  # date + space + bullet + space + event

    for i, entry in enumerate(entries):
        date_text = entry["date"].rjust(date_w)
        date_styled = style(date_text, dim=True, enabled=color)
        event_text = entry["event"]
        if visual_len(event_text) > event_w:
            event_text = event_text[: max(event_w - 1, 0)] + "…"
        line = f"{date_styled} {bullet} {event_text}"
        lines.append(visual_ljust(line, w))
        if i < len(entries) - 1:
            connector_indent = " " * (date_w + 1)
            connector = f"{connector_indent}{bar}"
            lines.append(visual_ljust(connector, w))

    return lines

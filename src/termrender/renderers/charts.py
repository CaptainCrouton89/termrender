"""Bar chart, progress bar, and gauge renderers for termrender."""

from __future__ import annotations

from termrender.blocks import Block
from termrender.style import style, visual_len, visual_ljust


# Eighths block characters for sub-cell precision
_EIGHTHS = " ▏▎▍▌▋▊▉█"
_FULL = "█"
_EMPTY = "░"


def _format_value(v: float, unit: str = "") -> str:
    """Format a numeric value with optional unit, dropping trailing .0."""
    if v == int(v):
        s = f"{int(v):,}"
    else:
        s = f"{v:,.2f}"
    return f"{s}{unit}" if unit else s


def _draw_bar(width: int, ratio: float) -> str:
    """Draw a horizontal bar with sub-cell precision via eighth blocks."""
    if width <= 0:
        return ""
    ratio = max(0.0, min(ratio, 1.0))
    total_eighths = int(round(ratio * width * 8))
    full = total_eighths // 8
    remainder = total_eighths % 8
    out = _FULL * full
    if remainder and full < width:
        out += _EIGHTHS[remainder]
        full += 1
    out += _EMPTY * max(width - full, 0)
    return out


def render_bar(block: Block, color: bool, render_child=None) -> list[str]:
    """Render a multi-bar horizontal chart."""
    items = block.attrs.get("items", [])
    title = block.attrs.get("title")
    bar_color = block.attrs.get("color", "cyan")
    w = block.width or 60

    if not items:
        return [visual_ljust("", w)]

    label_w = max(visual_len(it["label"]) for it in items)
    value_strs = [_format_value(it["value"], it.get("unit", "")) for it in items]
    value_w = max(visual_len(s) for s in value_strs)

    # Layout: label + 2 spaces + bar + 2 spaces + value
    bar_w = max(w - label_w - value_w - 4, 5)

    max_value = max((it["value"] for it in items), default=1) or 1

    lines: list[str] = []
    if title:
        lines.append(visual_ljust(style(title, bold=True, enabled=color), w))

    for it, vstr in zip(items, value_strs):
        label = visual_ljust(it["label"], label_w)
        ratio = (it["value"] / max_value) if max_value > 0 else 0
        bar = _draw_bar(bar_w, ratio)
        bar_styled = style(bar, color=bar_color, enabled=color)
        value_str = vstr.rjust(value_w)
        line = f"{label}  {bar_styled}  {value_str}"
        lines.append(visual_ljust(line, w))

    return lines


def _coerce_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def render_progress(block: Block, color: bool, render_child=None) -> list[str]:
    """Render a single-line progress bar with label and percentage."""
    w = block.width or 60
    value = _coerce_float(block.attrs.get("value", 0))
    maximum = _coerce_float(block.attrs.get("max", 100)) or 1
    label = block.attrs.get("label", "")
    bar_color = block.attrs.get("color")
    ratio = max(0.0, min(value / maximum, 1.0))

    pct = f"{int(round(ratio * 100))}%"
    value_str = f"{_format_value(value)}/{_format_value(maximum)} ({pct})"

    label_part = f"{label}  " if label else ""
    label_w = visual_len(label_part)
    value_w = visual_len(value_str) + 2  # 2-space gap

    bar_w = max(w - label_w - value_w, 5)
    bar = _draw_bar(bar_w, ratio)

    # Default color: green when full, yellow >50, red below
    if not bar_color:
        if ratio >= 0.99:
            bar_color = "green"
        elif ratio >= 0.5:
            bar_color = "cyan"
        else:
            bar_color = "yellow"

    bar_styled = style(bar, color=bar_color, enabled=color)
    line = f"{label_part}{bar_styled}  {value_str}"
    return [visual_ljust(line, w)]


def render_gauge(block: Block, color: bool, render_child=None) -> list[str]:
    """Render a 3-line gauge: label / bar / numeric."""
    w = block.width or 60
    value = _coerce_float(block.attrs.get("value", 0))
    maximum = _coerce_float(block.attrs.get("max", 100)) or 1
    label = block.attrs.get("label", "")
    bar_color = block.attrs.get("color")
    unit = block.attrs.get("unit", "")
    ratio = max(0.0, min(value / maximum, 1.0))

    if not bar_color:
        if ratio >= 0.9:
            bar_color = "red"
        elif ratio >= 0.7:
            bar_color = "yellow"
        else:
            bar_color = "green"

    bar = _draw_bar(w, ratio)
    bar_styled = style(bar, color=bar_color, bold=True, enabled=color)
    pct = f"{int(round(ratio * 100))}%"
    value_str = f"{_format_value(value, unit)} / {_format_value(maximum, unit)} ({pct})"

    label_line = visual_ljust(style(label, bold=True, enabled=color), w) if label else visual_ljust("", w)
    bar_line = visual_ljust(bar_styled, w)
    value_line = visual_ljust(style(value_str, dim=True, enabled=color), w)
    return [label_line, bar_line, value_line]

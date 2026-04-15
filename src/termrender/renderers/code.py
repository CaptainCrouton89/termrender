"""Syntax-highlighted code block renderer for termrender."""

from __future__ import annotations

from typing import Callable

from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import TextLexer, get_lexer_by_name

from termrender.blocks import Block
from termrender.renderers.borders import render_box
from termrender.style import visual_len, wrap_text


def render(
    block: Block, color: bool, render_child: Callable[[Block, bool], list[str]]
) -> list[str]:
    """Render a code block with syntax highlighting and box-drawing borders."""
    source = block.attrs.get("source", "")
    lang = block.attrs.get("lang")

    # Wrap raw source lines to fit within the box before highlighting,
    # so render_box doesn't need to grow beyond the layout allocation.
    border_v = visual_len("│")
    content_w = max((block.width or 1) - 2 * border_v - 2, 1)
    raw_lines = source.split("\n") if source else [""]
    wrapped_lines = []
    for line in raw_lines:
        wrapped_lines.extend(wrap_text(line, content_w))

    wrapped_source = "\n".join(wrapped_lines)

    # Syntax highlight (or plain text)
    if color and wrapped_source:
        try:
            lexer = get_lexer_by_name(lang) if lang else TextLexer()
        except Exception:
            lexer = TextLexer()
        highlighted = highlight(wrapped_source, lexer, TerminalFormatter())
        # Pygments adds a trailing newline — strip it
        highlighted = highlighted.rstrip("\n")
        code_lines = highlighted.split("\n")
    else:
        code_lines = wrapped_lines

    return render_box(
        code_lines,
        width=block.width,
        color=color,
        title=lang,
        dim=True,
    )

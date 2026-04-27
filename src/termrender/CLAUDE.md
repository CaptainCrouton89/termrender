- `layout.py` imports `fix_mermaid_encoding` and `preprocess_mermaid_for_ascii` from `renderers/mermaid.py` — the only reverse dependency from layout into renderers. Reorganizing `renderers/` must preserve these imports. The two mermaid subprocess call sites differ: layout uses `check=True` (non-zero exit raises → caught → raw-source fallback); the renderer omits `check` (non-zero exit silently reads `stdout`, which may be empty or partial).

- `--check` calls `parse()` and exits — it never runs `layout.py`. Layout-time failures (mermaid subprocess missing, column percent overflow, `resolve_width`/`resolve_height` exceptions) pass `--check` cleanly but crash at render time.

- Column widths: explicit percent/absolute allocations are subtracted first; remaining space is split among auto-width columns with `max(remaining, 0)`. Two columns each claiming 80% of a 100px terminal leaves auto-width columns with `width = 1` — no error, no proportional scaling.

- **QUOTE** height gets `+1` only when `author` or `by` attr is set. Using any other key (`attribution`, `source`) silently omits the extra line — the renderer's attribution line is clipped.

- **LIST_ITEM** layout wraps at `max(width - 2, 1)`, hardcoding a 2-column indent. If the renderer changes the indent width, layout height and actual render height diverge silently.

- `text.py:32–33`: after each wrapped line, the offset skips one character if the next plain-text character is a space (the space `wrap_text` consumed). If wrapping preserves trailing spaces, this skip shifts subsequent span styling by one character.

- `--tmux` exits `EXIT_OK` after the tmux pane command succeeds — the `--check` branch comes later and is never reached. `--check` is silently dropped when combined with `--tmux`.

- `_EMOJI_WIDE_RANGES` in `style.py`: `_char_width()` exits early when `cp < lo`, assuming ranges are in ascending codepoint order. Adding a range out of order silently misclassifies all codepoints whose `lo` is higher than the inserted range's `lo`.

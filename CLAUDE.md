# termrender

## Commands
```bash
pip install -e .
pytest tests/
cat file.md | termrender doc render          # render markdown
cat file.md | termrender doc check           # validate syntax
termrender doc watch /path/to/file.md        # live-render
python -m build
```

## Constraints
- **Layout pass order is load-bearing**: `resolve_width()` top-down must complete before `resolve_height()` bottom-up — height calls `wrap_text(text, width)`, which requires width already set.
- **`wrap_text()` CJK bug**: uses `len()` internally, not `visual_len()` — silently overflows for CJK content.
- **`_ambiguous_width` is global mutable state** with no reset path — `set_ambiguous_width()` or `TERMRENDER_CJK` env var changes persist for the process lifetime.
- **Commits**: conventional commits. `feat` → minor, `fix`/`perf` → patch. Auto-released via python-semantic-release on main.

## Supplementary CLAUDE.md files
- `src/termrender/CLAUDE.md` — parser, layout, mermaid, nesting, and `--check`/`--tmux` implementation gotchas
- `src/termrender/renderers/CLAUDE.md` — renderer contracts, `render_box` width semantics, EAW edge cases

Read these before modifying layout, parsing, or renderer code.

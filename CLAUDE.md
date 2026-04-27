# termrender

## Commands
```bash
pip install -e .
pytest tests/
python -m termrender <file.md>
python -m build
```

No linter or formatter is configured.

## Constraints
- **Layout pass order is load-bearing**: `resolve_width()` top-down must complete before `resolve_height()` bottom-up — height calls `wrap_text(text, width)`, which requires width already set.
- **`borders.py` `render_box` width**: takes **total** width including borders, not content width. Passing content width silently overflows.
- **`wrap_text()` CJK bug**: uses `len()` internally, not `visual_len()` — silently overflows for CJK content.
- **`_ambiguous_width` is global mutable state** with no reset path — `set_ambiguous_width()` or `TERMRENDER_CJK` env var changes persist for the process lifetime.
- **Version**: derived from git tags via hatch-vcs — no version in `pyproject.toml`. Adding one will conflict.
- **Commits**: conventional commits. `feat` → minor, `fix`/`perf` → patch. Auto-released via python-semantic-release on main.

## Supplementary CLAUDE.md files
- `src/termrender/CLAUDE.md` — parser, layout, mermaid, nesting, and `--check`/`--tmux` implementation gotchas
- `src/termrender/renderers/CLAUDE.md` — renderer contracts, `render_box` width semantics, EAW edge cases

Read these before modifying layout, parsing, or renderer code.

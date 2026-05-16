"""CLI entry point for termrender — frozen agent-oriented API contract."""

import argparse
import json
import os
import sys
from typing import Any, NoReturn

from termrender import render, TerminalError, DirectiveError

_MISSING = object()

# Exit codes
EXIT_OK = 0
EXIT_INPUT = 1    # bad stdin JSON, missing required field, not-in-tmux, tmux-missing, pane-gone
EXIT_SYNTAX = 2   # directive syntax / nesting error, pre-check failure
EXIT_TERMINAL = 3 # terminal capability error

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("termrender")
except Exception:
    __version__ = "dev"


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _json_error(
    error: str,
    message: str,
    *,
    received: Any = _MISSING,
    field: str | None = None,
    next_: str,
    code: int = EXIT_INPUT,
) -> NoReturn:
    obj: dict[str, Any] = {"error": error, "message": message}
    if received is not _MISSING:
        obj["received"] = received
    if field is not None:
        obj["field"] = field
    obj["next"] = next_
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()
    sys.exit(code)


def _read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        _json_error(
            "bad_stdin_json",
            f"stdin is not valid JSON: {e}",
            received=raw[:200] if len(raw) > 200 else raw,
            next_="send a single JSON object on stdin",
        )
    if not isinstance(parsed, dict):
        _json_error(
            "bad_stdin_json",
            "stdin JSON must be an object, not a " + type(parsed).__name__,
            received=parsed,
            next_="send a single JSON object on stdin, e.g. {\"source\": \"...\"}",
        )
    return parsed


def _require(params: dict[str, Any], field: str, typ: type, label: str) -> Any:
    if field not in params:
        _json_error(
            "bad_input",
            f"required field '{field}' is missing",
            field=field,
            next_=f"add \"{field}\": <{label}> to your stdin JSON object",
        )
    val = params[field]
    if not isinstance(val, typ):
        _json_error(
            "bad_input",
            f"field '{field}' must be {label}, got {type(val).__name__}",
            received=val,
            field=field,
            next_=f"set \"{field}\" to a {label} value",
        )
    return val


def _opt(params: dict[str, Any], field: str, typ: type | tuple, default: Any = None) -> Any:
    if field not in params:
        return default
    val = params[field]
    if not isinstance(val, typ):
        _json_error(
            "bad_input",
            f"field '{field}' has wrong type: expected {typ}, got {type(val).__name__}",
            received=val,
            field=field,
            next_=f"fix the type of '{field}' in your stdin JSON object",
        )
    return val


def _opt_nullable(params: dict[str, Any], field: str, typ: type, default: Any = None) -> Any:
    """Accept field as typ | null | absent; absent → default."""
    if field not in params:
        return default
    val = params[field]
    if val is None:
        return None
    if not isinstance(val, typ):
        _json_error(
            "bad_input",
            f"field '{field}' must be {typ.__name__} or null, got {type(val).__name__}",
            received=val,
            field=field,
            next_=f"set '{field}' to a {typ.__name__} or null",
        )
    return val


def _resolve_color(color_param: bool | None, *, force_env: bool = False) -> bool:
    if color_param is not None:
        return color_param
    if os.environ.get("TERMRENDER_COLOR") == "1":
        return True
    if os.environ.get("NO_COLOR"):
        return False
    return sys.stdout.isatty()


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def _cmd_doc_render(params: dict[str, Any]) -> None:
    source = _require(params, "source", str, "string")
    width = _opt_nullable(params, "width", int, default=None)
    color_param = _opt_nullable(params, "color", bool, default=None)
    cjk = _opt(params, "cjk", bool, False)

    if cjk:
        os.environ["TERMRENDER_CJK"] = "1"

    color = _resolve_color(color_param)

    try:
        output = render(source, width=width, color=color)
    except TerminalError as e:
        _json_error(
            "terminal_error",
            f"terminal does not support required capabilities: {e}",
            next_="use a terminal that supports Unicode, or set color=false in your request",
            code=EXIT_TERMINAL,
        )
    except DirectiveError as e:
        _json_error(
            "syntax_error",
            f"directive syntax error: {e}",
            next_="fix the malformed/unclosed directive in 'source', or call termrender doc check first",
            code=EXIT_SYNTAX,
        )
    except ValueError as e:
        _json_error(
            "nesting_error",
            f"directive nesting error: {e}",
            next_="ensure outer fences use strictly more colons than inner fences",
            code=EXIT_SYNTAX,
        )
    except Exception as e:
        _json_error(
            "internal",
            f"unexpected render error: {e}",
            next_="report this as a bug with the 'source' value that triggered it",
            code=EXIT_INPUT,
        )

    sys.stdout.write(output)
    sys.stdout.flush()


def _cmd_doc_check(params: dict[str, Any]) -> None:
    source = _require(params, "source", str, "string")
    cjk = _opt(params, "cjk", bool, False)

    if cjk:
        os.environ["TERMRENDER_CJK"] = "1"

    from termrender.parser import parse

    errors: list[dict[str, str]] = []
    ok = True
    try:
        parse(source)
    except DirectiveError as e:
        ok = False
        errors.append({"kind": "syntax", "message": str(e)})
    except ValueError as e:
        ok = False
        errors.append({"kind": "nesting", "message": str(e)})

    sys.stdout.write(json.dumps({"ok": ok, "errors": errors}) + "\n")
    sys.stdout.flush()
    sys.exit(EXIT_OK if ok else EXIT_SYNTAX)


def _cmd_doc_watch(params: dict[str, Any]) -> None:
    path = _require(params, "path", str, "string")
    color_param = _opt_nullable(params, "color", bool, default=None)
    cjk = _opt(params, "cjk", bool, False)

    if cjk:
        os.environ["TERMRENDER_CJK"] = "1"

    color = _resolve_color(color_param)
    _watch_loop(path, color=color)
    sys.exit(EXIT_OK)


def _cmd_pane_open(params: dict[str, Any]) -> None:
    import shlex
    import subprocess
    import tempfile

    path = _require(params, "path", str, "string")
    width = _opt_nullable(params, "width", int, default=None)
    color_param = _opt_nullable(params, "color", bool, default=None)
    cjk = _opt(params, "cjk", bool, False)
    watch = _opt(params, "watch", bool, True)
    window = _opt(params, "window", str, "split")

    if window not in ("split", "new"):
        _json_error(
            "bad_input",
            f"field 'window' must be \"split\" or \"new\", got {window!r}",
            received=window,
            field="window",
            next_='set "window" to "split" or "new"',
        )

    if not os.environ.get("TMUX"):
        _json_error(
            "not_in_tmux",
            "not inside a tmux session",
            next_="run inside a tmux session before calling termrender pane open",
            code=EXIT_INPUT,
        )

    # Read source for pre-check only when not watch mode (watch points at live file)
    try:
        with open(path) as f:
            source = f.read()
    except OSError as e:
        _json_error(
            "bad_input",
            f"cannot read file: {e}",
            field="path",
            next_=f"ensure the file exists and is readable: {path}",
        )

    # Syntax pre-check
    try:
        from termrender.parser import parse as _parse
        _parse(source)
    except DirectiveError as e:
        _json_error(
            "syntax_error",
            f"directive syntax error: {e}",
            next_="fix the syntax error in the file before opening a pane",
            code=EXIT_SYNTAX,
        )
    except ValueError as e:
        _json_error(
            "nesting_error",
            f"directive nesting error: {e}",
            next_="fix the nesting error in the file before opening a pane",
            code=EXIT_SYNTAX,
        )

    # Determine pane width
    if window == "new":
        pane_width = None
    elif width is not None:
        pane_width = max(width, 40)
    else:
        try:
            result = subprocess.run(
                ["tmux", "display-message", "-p", "#{window_width}"],
                capture_output=True, text=True, check=True,
            )
            window_width = int(result.stdout.strip())
            if window_width >= 140:
                pane_width = 80
            elif window_width >= 100:
                pane_width = window_width // 2
            else:
                pane_width = max(window_width - 2 - 50, 40)
        except Exception:
            pane_width = 80
        pane_width = max(pane_width, 40)

    if watch:
        source_path = path
        tmpfile = None
    else:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", prefix="termrender-", delete=False,
        ) as f:
            f.write(source)
            tmpfile = f.name
        source_path = tmpfile

    cmd_parts = ["termrender", "doc"]
    if watch:
        cmd_parts += ["watch"]
        stdin_json = json.dumps({"path": source_path, "color": True, "cjk": cjk})
        pane_cmd = f"echo {shlex.quote(stdin_json)} | termrender doc watch"
    else:
        stdin_json = json.dumps({
            "source": source,
            "color": True,
            "cjk": cjk,
            **({"width": pane_width} if pane_width is not None else {}),
        })
        pane_cmd = (
            f"echo {shlex.quote(stdin_json)} | termrender doc render"
            + f" | less -R; rm -f {shlex.quote(source_path)}"
        )

    try:
        if window == "new":
            result = subprocess.run(
                ["tmux", "new-window", "-P", "-F", "#{pane_id}", pane_cmd],
                check=True, capture_output=True, text=True,
            )
            pane_id = result.stdout.strip()
        else:
            split_args = ["tmux", "split-window", "-h", "-f"]
            if pane_width is not None:
                split_args += ["-l", str(pane_width)]
            split_args += ["-P", "-F", "#{pane_id}", pane_cmd]
            result = subprocess.run(split_args, check=True, capture_output=True, text=True)
            pane_id = result.stdout.strip()
    except FileNotFoundError:
        if tmpfile:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass
        _json_error(
            "tmux_missing",
            "tmux executable not found",
            next_="install tmux and ensure it is on PATH",
            code=EXIT_INPUT,
        )
    except subprocess.CalledProcessError as e:
        if tmpfile:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass
        _json_error(
            "internal",
            f"tmux command failed: {e}",
            next_="check that tmux is running and has space for a new pane",
            code=EXIT_INPUT,
        )

    sys.stdout.write(json.dumps({"pane_id": pane_id}) + "\n")
    sys.stdout.flush()


def _cmd_pane_update(params: dict[str, Any]) -> None:
    import shlex
    import subprocess
    import tempfile

    pane_id = _require(params, "pane_id", str, "string")
    path = _require(params, "path", str, "string")
    width = _opt_nullable(params, "width", int, default=None)
    color_param = _opt_nullable(params, "color", bool, default=None)
    cjk = _opt(params, "cjk", bool, False)
    watch = _opt(params, "watch", bool, True)

    try:
        with open(path) as f:
            source = f.read()
    except OSError as e:
        _json_error(
            "bad_input",
            f"cannot read file: {e}",
            field="path",
            next_=f"ensure the file exists and is readable: {path}",
        )

    # Syntax pre-check
    try:
        from termrender.parser import parse as _parse
        _parse(source)
    except DirectiveError as e:
        _json_error(
            "syntax_error",
            f"directive syntax error: {e}",
            next_="fix the syntax error in the file before updating the pane",
            code=EXIT_SYNTAX,
        )
    except ValueError as e:
        _json_error(
            "nesting_error",
            f"directive nesting error: {e}",
            next_="fix the nesting error in the file before updating the pane",
            code=EXIT_SYNTAX,
        )

    # Determine pane width
    if width is not None:
        pane_width = max(width, 20)
    else:
        try:
            result = subprocess.run(
                ["tmux", "display-message", "-p", "-t", pane_id, "#{pane_width}"],
                capture_output=True, text=True, check=True,
            )
            pane_width = int(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
            _json_error(
                "pane_gone",
                f"could not query tmux pane {pane_id!r}",
                received=pane_id,
                field="pane_id",
                next_="the pane may have been closed; spawn a fresh one with termrender pane open",
                code=EXIT_INPUT,
            )
        pane_width = max(pane_width, 20)

    if watch:
        source_path = path
        tmpfile = None
    else:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", prefix="termrender-", delete=False,
        ) as f:
            f.write(source)
            tmpfile = f.name
        source_path = tmpfile

    if watch:
        stdin_json = json.dumps({"path": source_path, "color": True, "cjk": cjk})
        pane_cmd = f"echo {shlex.quote(stdin_json)} | termrender doc watch"
    else:
        stdin_json = json.dumps({
            "source": source,
            "color": True,
            "cjk": cjk,
            "width": pane_width,
        })
        pane_cmd = (
            f"echo {shlex.quote(stdin_json)} | termrender doc render"
            + f" | less -R; rm -f {shlex.quote(source_path)}"
        )

    try:
        subprocess.run(
            ["tmux", "respawn-pane", "-k", "-t", pane_id, pane_cmd],
            check=True,
        )
    except FileNotFoundError:
        if tmpfile:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass
        _json_error(
            "tmux_missing",
            "tmux executable not found",
            next_="install tmux and ensure it is on PATH",
            code=EXIT_INPUT,
        )
    except subprocess.CalledProcessError:
        if tmpfile:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass
        _json_error(
            "pane_gone",
            f"failed to respawn tmux pane {pane_id!r} — it may have been closed",
            received=pane_id,
            field="pane_id",
            next_="spawn a fresh pane with termrender pane open",
            code=EXIT_INPUT,
        )

    sys.stdout.write(json.dumps({"pane_id": pane_id}) + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Watch loop (unchanged from original)
# ---------------------------------------------------------------------------

def _watch_loop(file_path: str, *, color: bool, poll_interval: float = 0.2) -> None:
    import time
    import shutil as _shutil
    import select

    interactive = sys.stdin.isatty()
    old_term = None
    if interactive:
        try:
            import termios
            import tty
            old_term = termios.tcgetattr(sys.stdin.fileno())
        except Exception:
            interactive = False

    rendered: list[str] = []
    scroll = 0
    first_render = True
    last_mtime: float | None = None
    last_size: tuple[int, int] = (0, 0)

    def _render_source() -> list[str]:
        try:
            with open(file_path) as f:
                source = f.read()
        except FileNotFoundError:
            return [f"termrender: file not found: {file_path}"]
        except OSError as e:
            return [f"termrender: cannot read {file_path}: {e}"]
        try:
            body = render(source, width=None, color=color)
        except DirectiveError as e:
            body = f"termrender: syntax error: {e}"
        except TerminalError as e:
            body = f"termrender: terminal error: {e}"
        except ValueError as e:
            body = f"termrender: nesting error: {e}"
        except Exception as e:
            body = f"termrender: render error: {e}"
        return body.split("\n")

    def _status(view_h: int) -> str:
        total = len(rendered)
        if total <= view_h:
            pos = "all"
        else:
            pos = f"{scroll + 1}-{min(scroll + view_h, total)}/{total}"
        keys = (
            "↑↓/wheel scroll · g/G top/bottom · q quit"
            if interactive
            else "Ctrl+C to exit"
        )
        return f"watching {os.path.basename(file_path)} — {keys}  [{pos}]"

    def _draw() -> None:
        nonlocal scroll
        size = _shutil.get_terminal_size()
        view_h = max(1, size.lines - 1)
        max_scroll = max(0, len(rendered) - view_h)
        scroll = min(max(scroll, 0), max_scroll)
        window = rendered[scroll:scroll + view_h]
        window += [""] * (view_h - len(window))
        status = _status(view_h)
        if color:
            status = f"\033[2m{status}\033[0m"
        sys.stdout.write(
            "\033[?25l\033[2J\033[H"
            + "\n".join(window)
            + f"\033[{size.lines};1H"
            + status
        )
        sys.stdout.flush()

    def _consume(buf: str, view_h: int) -> tuple[str, bool, bool]:
        nonlocal scroll
        page = max(1, view_h - 1)
        i, n, moved = 0, len(buf), False
        while i < n:
            c = buf[i]
            if c == "q" or c == "\x03":
                return "", True, moved
            if c == "\x1b":
                if i + 1 >= n:
                    break
                if buf[i + 1] != "[":
                    i += 1
                    continue
                j = i + 2
                if j < n and buf[j] == "<":
                    k = j + 1
                    while k < n and buf[k] not in ("M", "m"):
                        k += 1
                    if k >= n:
                        break
                    try:
                        btn = int(buf[j + 1:k].split(";")[0])
                    except ValueError:
                        btn = -1
                    if buf[k] == "M":
                        if btn == 64:
                            scroll -= 3; moved = True
                        elif btn == 65:
                            scroll += 3; moved = True
                    i = k + 1
                    continue
                k = j
                while k < n and not ("\x40" <= buf[k] <= "\x7e"):
                    k += 1
                if k >= n:
                    break
                seq = buf[i:k + 1]
                if seq == "\x1b[A":
                    scroll -= 1; moved = True
                elif seq == "\x1b[B":
                    scroll += 1; moved = True
                elif seq == "\x1b[5~":
                    scroll -= page; moved = True
                elif seq == "\x1b[6~":
                    scroll += page; moved = True
                elif seq == "\x1b[H":
                    scroll = 0; moved = True
                elif seq == "\x1b[F":
                    scroll = 1 << 30; moved = True
                i = k + 1
                continue
            if c == "k":
                scroll -= 1; moved = True
            elif c == "j":
                scroll += 1; moved = True
            elif c == "g":
                scroll = 0; moved = True
            elif c == "G":
                scroll = 1 << 30; moved = True
            elif c in (" ", "f", "d"):
                scroll += page; moved = True
            elif c in ("b", "u"):
                scroll -= page; moved = True
            i += 1
        return buf[i:], False, moved

    sys.stdout.write("\033[?1049h")
    if interactive:
        sys.stdout.write("\033[?1000h\033[?1006h")
        tty.setcbreak(sys.stdin.fileno())
    sys.stdout.flush()

    buf = ""
    try:
        while True:
            try:
                mtime = os.path.getmtime(file_path)
            except FileNotFoundError:
                mtime = None
            size = _shutil.get_terminal_size()
            size_tuple = (size.columns, size.lines)
            view_h = max(1, size.lines - 1)

            dirty = False
            if mtime != last_mtime or size_tuple != last_size:
                pinned = (not first_render) and scroll >= max(0, len(rendered) - view_h)
                rendered[:] = _render_source()
                last_mtime, last_size = mtime, size_tuple
                if first_render:
                    scroll = 0
                    first_render = False
                elif pinned:
                    scroll = max(0, len(rendered) - view_h)
                dirty = True

            if dirty:
                _draw()

            if not interactive:
                time.sleep(poll_interval)
                continue

            if select.select([sys.stdin], [], [], poll_interval)[0]:
                chunk = os.read(sys.stdin.fileno(), 4096).decode("utf-8", "replace")
                if chunk:
                    buf, quit_, moved = _consume(buf + chunk, view_h)
                    if quit_:
                        break
                    if moved:
                        _draw()
    except KeyboardInterrupt:
        pass
    finally:
        if interactive:
            sys.stdout.write("\033[?1000l\033[?1006l")
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_term)
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Help text
# ---------------------------------------------------------------------------

_ROOT_HELP = f"""\
termrender {__version__}

Render directive-flavored markdown as rich ANSI terminal output.

I/O CONTRACT (applies to all leaf commands):
  Input:  a single JSON object on stdin
  Output: see per-leaf below (ANSI or JSON)
  Errors: a JSON object on stdout, exit non-zero
    {{
      "error":    "<stable_code>",
      "message":  "<human readable>",
      "received": <offending value>,   // when applicable
      "field":    "<field name>",       // when applicable
      "next":     "<recovery action>"
    }}

  Stable error codes:
    bad_stdin_json   stdin is not valid JSON or not an object
    bad_input        missing/wrong-type/invalid field value
    syntax_error     directive syntax error in source
    nesting_error    directive nesting error in source
    terminal_error   terminal does not support required capabilities
    not_in_tmux      pane command run outside tmux
    tmux_missing     tmux binary not found
    pane_gone        target pane no longer exists
    internal         unexpected error (report as bug)

Exit codes:
  0  ok
  1  input / usage error
  2  syntax / nesting error
  3  terminal capability error

Branches:
  doc   | use when: rendering, checking, or watching a markdown document
  pane  | use when: managing a tmux side-pane renderer

Use -h on any branch or leaf for its input/output schema.
"""

_DOC_HELP = """\
termrender doc — document rendering commands

Leaves:
  render  | render markdown to ANSI and print to stdout
  check   | validate directive syntax without rendering
  watch   | live-render a file in the controlling terminal (human use)

Use -h on a leaf for its input/output schema.
"""

_DOC_RENDER_HELP = """\
termrender doc render

Render a markdown document to ANSI and write to stdout.

Input (JSON object on stdin):
  source  string   required   Markdown source to render
  width   int|null optional   Output width in columns; null = auto-detect terminal width
  color   bool|null optional  Force color on/off; null = true when stdout isatty or TERMRENDER_COLOR=1
  cjk     bool     optional   Treat ambiguous-width Unicode as double-width (default false)

Output:
  The rendered ANSI string written directly to stdout (NOT JSON).
  This is the only leaf that outputs non-JSON on success.

Errors:
  syntax_error    exit 2 — malformed/unclosed directive in source
  nesting_error   exit 2 — outer fence does not use strictly more colons than inner
  terminal_error  exit 3 — terminal does not support required capabilities

Effects: none.
"""

_DOC_CHECK_HELP = """\
termrender doc check

Validate directive syntax without rendering.

Input (JSON object on stdin):
  source  string  required   Markdown source to validate
  cjk     bool    optional   Treat ambiguous-width Unicode as double-width (default false)

Output (JSON):
  { "ok": bool, "errors": [ {"kind": "syntax"|"nesting", "message": string} ] }
  errors is [] when ok is true.

Exit: 0 when ok, 2 when not ok.
Effects: none.
"""

_DOC_WATCH_HELP = """\
termrender doc watch

Live-render a file in the controlling terminal, updating on every save.

WARNING: this command takes over the controlling terminal until quit (q or Ctrl-C).
It is intended for human interactive use, NOT for agent capture or subprocess piping.

Input (JSON object on stdin):
  path   string    required   File path to watch and re-render on change
  color  bool|null optional   Force color on/off; null = auto-detect
  cjk    bool      optional   Treat ambiguous-width Unicode as double-width (default false)

Output: none (renders directly to the controlling terminal).
Exit: 0 on quit. Effects: takes over the controlling terminal until quit.
"""

_PANE_HELP = """\
termrender pane — tmux pane management commands

Leaves:
  open    | spawn a new tmux pane rendering a file
  update  | respawn an existing pane with new content

Use -h on a leaf for its input/output schema.
"""

_PANE_OPEN_HELP = """\
termrender pane open

Spawn a tmux pane rendering a file. Returns immediately.
Requires: running inside an active tmux session.

Input (JSON object on stdin):
  path    string         required   File to render in the pane
  width   int|null       optional   Pane width in columns; null = auto-size from window
  color   bool|null      optional   Force color; null = always true in pane
  cjk     bool           optional   Double-width ambiguous Unicode (default false)
  watch   bool           optional   Live-update on file save (default true)
  window  "split"|"new"  optional   Split current pane or open a new tmux window (default "split")

Output (JSON):
  { "pane_id": string }

Errors:
  not_in_tmux  exit 1 — not inside a tmux session
  tmux_missing exit 1 — tmux binary not found
  syntax_error exit 2 — file has directive syntax errors (pre-check)
  nesting_error exit 2 — file has nesting errors (pre-check)
  bad_input    exit 1 — file unreadable or field invalid

Effects: spawns a detached tmux pane (split or new window) running the renderer.
The pane lives until closed by the user.
"""

_PANE_UPDATE_HELP = """\
termrender pane update

Respawn an existing tmux pane with new content. Pane id is unchanged.
Requires: running inside an active tmux session.

Input (JSON object on stdin):
  pane_id  string    required   Tmux pane id to update (e.g. "%23")
  path     string    required   New file to render in the pane
  width    int|null  optional   Override pane width; null = read from pane
  color    bool|null optional   Force color; null = always true in pane
  cjk      bool      optional   Double-width ambiguous Unicode (default false)
  watch    bool      optional   Live-update on file save (default true)

Output (JSON):
  { "pane_id": string }   (same pane_id as input)

Errors:
  pane_gone    exit 1 — target pane no longer exists
  tmux_missing exit 1 — tmux binary not found
  syntax_error exit 2 — file has directive syntax errors (pre-check)
  nesting_error exit 2 — file has nesting errors (pre-check)

Effects: replaces the process in the target pane.
"""


# ---------------------------------------------------------------------------
# Parser construction (help-only, no flags)
# ---------------------------------------------------------------------------

class _HelpAction(argparse.Action):
    def __init__(self, option_strings, dest=argparse.SUPPRESS, default=argparse.SUPPRESS, help=None):
        super().__init__(option_strings=option_strings, dest=dest, default=default, nargs=0, help=help)

    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        parser.exit(0)


def _make_parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="termrender",
        add_help=False,
    )
    root.add_argument("-h", action=_HelpAction, help="show this help")

    subs = root.add_subparsers(dest="branch", metavar="BRANCH")

    # --- doc branch ---
    doc = subs.add_parser("doc", add_help=False)
    doc.add_argument("-h", action=_HelpAction, help="show this help")
    doc_subs = doc.add_subparsers(dest="leaf", metavar="LEAF")

    doc_render = doc_subs.add_parser("render", add_help=False)
    doc_render.add_argument("-h", action=_HelpAction, help="show this help")

    doc_check = doc_subs.add_parser("check", add_help=False)
    doc_check.add_argument("-h", action=_HelpAction, help="show this help")

    doc_watch = doc_subs.add_parser("watch", add_help=False)
    doc_watch.add_argument("-h", action=_HelpAction, help="show this help")

    # --- pane branch ---
    pane = subs.add_parser("pane", add_help=False)
    pane.add_argument("-h", action=_HelpAction, help="show this help")
    pane_subs = pane.add_subparsers(dest="leaf", metavar="LEAF")

    pane_open = pane_subs.add_parser("open", add_help=False)
    pane_open.add_argument("-h", action=_HelpAction, help="show this help")

    pane_update = pane_subs.add_parser("update", add_help=False)
    pane_update.add_argument("-h", action=_HelpAction, help="show this help")

    return root, doc, doc_render, doc_check, doc_watch, pane, pane_open, pane_update


def main() -> None:
    (
        root, doc_parser, doc_render_parser, doc_check_parser, doc_watch_parser,
        pane_parser, pane_open_parser, pane_update_parser,
    ) = _make_parser()

    # Monkey-patch format_help for each parser
    root.format_help = lambda: _ROOT_HELP
    doc_parser.format_help = lambda: _DOC_HELP
    doc_render_parser.format_help = lambda: _DOC_RENDER_HELP
    doc_check_parser.format_help = lambda: _DOC_CHECK_HELP
    doc_watch_parser.format_help = lambda: _DOC_WATCH_HELP
    pane_parser.format_help = lambda: _PANE_HELP
    pane_open_parser.format_help = lambda: _PANE_OPEN_HELP
    pane_update_parser.format_help = lambda: _PANE_UPDATE_HELP

    args, extra = root.parse_known_args()

    branch = args.branch
    leaf = getattr(args, "leaf", None)

    if branch is None:
        root.print_help()
        sys.exit(EXIT_INPUT)

    if branch == "doc":
        if leaf is None:
            doc_parser.print_help()
            sys.exit(EXIT_INPUT)
        params = _read_stdin_json()
        if leaf == "render":
            _cmd_doc_render(params)
        elif leaf == "check":
            _cmd_doc_check(params)
        elif leaf == "watch":
            _cmd_doc_watch(params)
        else:
            doc_parser.print_help()
            sys.exit(EXIT_INPUT)

    elif branch == "pane":
        if leaf is None:
            pane_parser.print_help()
            sys.exit(EXIT_INPUT)
        params = _read_stdin_json()
        if leaf == "open":
            _cmd_pane_open(params)
        elif leaf == "update":
            _cmd_pane_update(params)
        else:
            pane_parser.print_help()
            sys.exit(EXIT_INPUT)

    else:
        root.print_help()
        sys.exit(EXIT_INPUT)


if __name__ == "__main__":
    main()

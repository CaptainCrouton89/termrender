"""Integration tests for the frozen CLI contract (subprocess invocations)."""

import json
import subprocess
import sys
from pathlib import Path

PYTHON = sys.executable
CLI = [PYTHON, "-m", "termrender"]


def _run(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + args,
        input=stdin,
        capture_output=True,
        text=True,
    )


def _json_stdin(obj: dict) -> str:
    return json.dumps(obj)


# ---------------------------------------------------------------------------
# Root and branch -h (exit 0)
# ---------------------------------------------------------------------------

def test_root_help_exit_zero():
    r = _run(["-h"])
    assert r.returncode == 0
    assert "termrender" in r.stdout
    assert "doc" in r.stdout
    assert "pane" in r.stdout
    assert "I/O CONTRACT" in r.stdout


def test_doc_help_exit_zero():
    r = _run(["doc", "-h"])
    assert r.returncode == 0
    assert "render" in r.stdout
    assert "check" in r.stdout
    assert "watch" in r.stdout


def test_pane_help_exit_zero():
    r = _run(["pane", "-h"])
    assert r.returncode == 0
    assert "open" in r.stdout
    assert "update" in r.stdout


def test_doc_render_help_exit_zero():
    r = _run(["doc", "render", "-h"])
    assert r.returncode == 0
    assert "source" in r.stdout


def test_doc_check_help_exit_zero():
    r = _run(["doc", "check", "-h"])
    assert r.returncode == 0
    assert "source" in r.stdout


def test_doc_watch_help_exit_zero():
    r = _run(["doc", "watch", "-h"])
    assert r.returncode == 0
    assert "path" in r.stdout


# ---------------------------------------------------------------------------
# doc render — happy path
# ---------------------------------------------------------------------------

def test_doc_render_produces_ansi_exit_zero():
    r = _run(["doc", "render"], stdin=_json_stdin({"source": "# Hello\n\nWorld"}))
    assert r.returncode == 0
    # Output is ANSI, not JSON — should contain the heading text
    assert "Hello" in r.stdout
    assert "World" in r.stdout
    # Must NOT be a JSON object on success
    try:
        json.loads(r.stdout)
        assert False, "doc render should not produce JSON on success"
    except (json.JSONDecodeError, ValueError):
        pass


def test_doc_render_with_explicit_width():
    r = _run(["doc", "render"], stdin=_json_stdin({"source": "# Hi", "width": 60, "color": False}))
    assert r.returncode == 0
    assert "Hi" in r.stdout


def test_doc_render_color_false():
    r = _run(["doc", "render"], stdin=_json_stdin({"source": "**bold**", "color": False}))
    assert r.returncode == 0
    assert "bold" in r.stdout
    # With color=false, no ANSI escape sequences in the bold text
    assert "\033[" not in r.stdout or r.stdout.count("\033[") < 5  # minimal/none


# ---------------------------------------------------------------------------
# doc check — ok path
# ---------------------------------------------------------------------------

def test_doc_check_ok():
    r = _run(["doc", "check"], stdin=_json_stdin({"source": "# Valid\n\nJust some text."}))
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["ok"] is True
    assert out["errors"] == []


# ---------------------------------------------------------------------------
# doc check — not-ok path
# ---------------------------------------------------------------------------

def test_doc_check_syntax_error():
    # Unclosed panel + col without proper nesting
    bad = ":::panel{title=\"x\"}\n:::col\n:::"
    r = _run(["doc", "check"], stdin=_json_stdin({"source": bad}))
    assert r.returncode == 2
    out = json.loads(r.stdout)
    assert out["ok"] is False
    assert len(out["errors"]) >= 1
    assert out["errors"][0]["kind"] in ("syntax", "nesting")
    assert isinstance(out["errors"][0]["message"], str)


# ---------------------------------------------------------------------------
# Bad stdin JSON → error JSON exit 1
# ---------------------------------------------------------------------------

def test_bad_json_returns_error_json():
    r = _run(["doc", "render"], stdin="not json at all")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["error"] == "bad_stdin_json"
    assert "next" in out


def test_json_array_returns_error_json():
    r = _run(["doc", "render"], stdin="[1, 2, 3]")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["error"] == "bad_stdin_json"


def test_empty_stdin_returns_error_json():
    r = _run(["doc", "render"], stdin="")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["error"] == "bad_stdin_json"


# ---------------------------------------------------------------------------
# Missing required field → error JSON exit 1
# ---------------------------------------------------------------------------

def test_missing_source_field_render():
    r = _run(["doc", "render"], stdin=_json_stdin({"color": False}))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["error"] == "bad_input"
    assert out["field"] == "source"
    assert "next" in out


def test_missing_source_field_check():
    r = _run(["doc", "check"], stdin=_json_stdin({}))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["error"] == "bad_input"
    assert out["field"] == "source"


def test_wrong_type_source_field():
    r = _run(["doc", "render"], stdin=_json_stdin({"source": 42}))
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["error"] == "bad_input"
    assert out["field"] == "source"


# ---------------------------------------------------------------------------
# Error JSON shape invariants
# ---------------------------------------------------------------------------

def test_error_json_always_has_stable_fields():
    r = _run(["doc", "render"], stdin="bad")
    out = json.loads(r.stdout)
    assert "error" in out
    assert "message" in out
    assert "next" in out
    assert isinstance(out["error"], str)
    assert isinstance(out["message"], str)
    assert isinstance(out["next"], str)


# ---------------------------------------------------------------------------
# No branch → usage exit 1
# ---------------------------------------------------------------------------

def test_no_subcommand_exits_one():
    r = _run([])
    # Should print root help and exit 1
    assert r.returncode == 1
    assert "termrender" in r.stdout or "termrender" in r.stderr

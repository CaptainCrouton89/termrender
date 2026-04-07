import unittest

from termrender import render
from termrender.parser import parse
from termrender.blocks import BlockType
from termrender.style import visual_len


class TestTimeline(unittest.TestCase):

    def test_parses_timeline(self):
        src = ":::timeline\n- 2024-01: launched\n- 2024-06: v2\n:::"
        doc = parse(src)
        self.assertEqual(doc.children[0].type, BlockType.TIMELINE)
        entries = doc.children[0].attrs["entries"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["date"], "2024-01")
        self.assertEqual(entries[0]["event"], "launched")

    def test_parses_pipe_separator(self):
        src = ":::timeline\n- 2024 | first\n:::"
        doc = parse(src)
        entries = doc.children[0].attrs["entries"]
        self.assertEqual(entries[0]["date"], "2024")
        self.assertEqual(entries[0]["event"], "first")

    def test_renders_with_bullets_and_connectors(self):
        src = ":::timeline\n- 2024: a\n- 2025: b\n:::"
        output = render(src, width=40, color=False)
        self.assertIn("●", output)  # bullet
        self.assertIn("│", output)  # connector

    def test_visual_widths_match(self):
        src = ":::timeline\n- 2024: alpha\n- 2025: beta\n- 2026: gamma\n:::"
        output = render(src, width=50, color=False)
        for ln in output.split("\n"):
            if ln:
                self.assertEqual(visual_len(ln), 50)

    def test_title_renders(self):
        src = ':::timeline{title="Releases"}\n- 2024: a\n:::'
        output = render(src, width=40, color=False)
        self.assertIn("Releases", output)

    def test_no_connector_after_last_entry(self):
        src = ":::timeline\n- 2024: a\n- 2025: b\n:::"
        output = render(src, width=40, color=False)
        lines = [ln for ln in output.split("\n") if ln]
        # last line should be the second event, not a connector
        self.assertIn("b", lines[-1])

    def test_long_event_truncates(self):
        long_event = "x" * 200
        src = f":::timeline\n- 2024: {long_event}\n:::"
        output = render(src, width=40, color=False)
        for ln in output.split("\n"):
            if ln:
                self.assertEqual(visual_len(ln), 40)

    def test_empty_timeline_renders_title_only(self):
        src = ':::timeline{title="Empty"}\n:::'
        output = render(src, width=40, color=False)
        self.assertIn("Empty", output)

    def test_height_matches_rendered_lines(self):
        src = ":::timeline\n- 2024: a\n- 2025: b\n- 2026: c\n:::"
        output = render(src, width=40, color=False)
        lines = [ln for ln in output.split("\n") if ln]
        # 3 entries -> 3 event lines + 2 connectors = 5 lines
        self.assertEqual(len(lines), 5)


if __name__ == "__main__":
    unittest.main()

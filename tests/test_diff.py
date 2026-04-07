import unittest

from termrender import render
from termrender.parser import parse
from termrender.blocks import BlockType
from termrender.style import visual_len


class TestDiff(unittest.TestCase):

    def test_parses_diff_directive(self):
        doc = parse(":::diff\n+ added\n- removed\n  unchanged\n:::")
        self.assertEqual(len(doc.children), 1)
        self.assertEqual(doc.children[0].type, BlockType.DIFF)
        self.assertIn("added", doc.children[0].attrs["source"])

    def test_renders_with_box_borders(self):
        src = ":::diff{title=\"auth.py\"}\n+ new line\n- old line\n:::"
        output = render(src, width=60, color=False)
        lines = output.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        # Top + 2 content + bot = 4 lines
        self.assertEqual(len(lines), 4)
        self.assertIn("auth.py", lines[0])
        self.assertTrue(lines[0].startswith("┌"))
        self.assertTrue(lines[-1].startswith("└"))

    def test_color_applies_red_and_green(self):
        src = ":::diff\n+ added\n- removed\n:::"
        output = render(src, width=60, color=True)
        # Green for + lines, red for - lines
        self.assertIn("\x1b[32m", output)  # green
        self.assertIn("\x1b[31m", output)  # red

    def test_visual_widths_match(self):
        src = ":::diff\n+ a\n- b\n  c\n:::"
        output = render(src, width=50, color=False)
        lines = [ln for ln in output.split("\n") if ln]
        for ln in lines:
            self.assertEqual(visual_len(ln), 50, f"line {ln!r}")

    def test_empty_diff_does_not_crash(self):
        output = render(":::diff\n:::", width=40, color=False)
        self.assertGreater(len(output), 0)

    def test_default_title_is_diff(self):
        output = render(":::diff\n+ x\n:::", width=40, color=False)
        self.assertIn("diff", output)

    def test_hunk_header_classified(self):
        src = ":::diff\n@@ -1,3 +1,4 @@\n+ added\n:::"
        output = render(src, width=60, color=True)
        self.assertIn("\x1b[35m", output)  # magenta for @


if __name__ == "__main__":
    unittest.main()

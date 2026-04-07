import unittest

from termrender import render
from termrender.parser import parse
from termrender.blocks import BlockType
from termrender.style import visual_len
from termrender.renderers.charts import _draw_bar


class TestBar(unittest.TestCase):

    def test_parses_bar_directive(self):
        src = ":::bar\napi: 100\nauth: 50\n:::"
        doc = parse(src)
        self.assertEqual(doc.children[0].type, BlockType.BAR)
        items = doc.children[0].attrs["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["label"], "api")
        self.assertEqual(items[0]["value"], 100.0)

    def test_renders_with_full_bar_at_max(self):
        src = ":::bar\nfoo: 100\nbar: 50\n:::"
        output = render(src, width=50, color=False)
        lines = [ln for ln in output.split("\n") if ln]
        self.assertEqual(len(lines), 2)
        # First line (max value) should have all full blocks
        self.assertIn("█", lines[0])
        # Second should have empty blocks
        self.assertIn("░", lines[1])

    def test_visual_widths_match(self):
        src = ":::bar\na: 10\nb: 20\nc: 30\n:::"
        output = render(src, width=60, color=False)
        for ln in output.split("\n"):
            if ln:
                self.assertEqual(visual_len(ln), 60)

    def test_title_renders_above_bars(self):
        src = ':::bar{title="Throughput"}\na: 1\n:::'
        output = render(src, width=40, color=False)
        first_line = output.split("\n")[0]
        self.assertIn("Throughput", first_line)

    def test_value_with_unit(self):
        src = ":::bar\nfoo | 12 ms\n:::"
        doc = parse(src)
        items = doc.children[0].attrs["items"]
        self.assertEqual(items[0]["unit"], "ms")

    def test_empty_bar_handled(self):
        out = render(":::bar\n:::", width=40, color=False)
        self.assertGreaterEqual(len(out), 0)

    def test_draw_bar_proportions(self):
        bar = _draw_bar(10, 0.5)
        self.assertEqual(visual_len(bar), 10)
        bar_full = _draw_bar(10, 1.0)
        self.assertEqual(bar_full, "█" * 10)
        bar_empty = _draw_bar(10, 0.0)
        self.assertEqual(bar_empty, "░" * 10)


class TestProgress(unittest.TestCase):

    def test_parses_progress(self):
        doc = parse(":::progress{value=70 max=100 label=\"Build\"}")
        self.assertEqual(doc.children[0].type, BlockType.PROGRESS)
        self.assertEqual(doc.children[0].attrs["value"], "70")
        self.assertEqual(doc.children[0].attrs["label"], "Build")

    def test_renders_single_line(self):
        src = ':::progress{value=50 max=100 label="X"}'
        output = render(src, width=60, color=False).rstrip("\n")
        lines = output.split("\n")
        self.assertEqual(len(lines), 1)
        self.assertEqual(visual_len(lines[0]), 60)

    def test_percentage_in_output(self):
        src = ':::progress{value=42 max=100}'
        output = render(src, width=60, color=False)
        self.assertIn("42", output)
        self.assertIn("%", output)

    def test_color_used_when_enabled(self):
        src = ':::progress{value=100 max=100 label="Done"}'
        output = render(src, width=60, color=True)
        # Full bar should be green
        self.assertIn("\x1b[32m", output)


class TestGauge(unittest.TestCase):

    def test_parses_gauge(self):
        doc = parse(':::gauge{value=88 max=100 label="Memory"}')
        self.assertEqual(doc.children[0].type, BlockType.GAUGE)

    def test_renders_three_lines(self):
        src = ':::gauge{value=50 max=100 label="Memory"}'
        output = render(src, width=60, color=False).rstrip("\n")
        lines = output.split("\n")
        self.assertEqual(len(lines), 3)
        for ln in lines:
            self.assertEqual(visual_len(ln), 60)

    def test_high_value_uses_red(self):
        src = ':::gauge{value=95 max=100 label="Memory"}'
        out = render(src, width=60, color=True)
        self.assertIn("\x1b[31m", out)  # red for >=90%

    def test_low_value_uses_green(self):
        src = ':::gauge{value=20 max=100 label="Memory"}'
        out = render(src, width=60, color=True)
        self.assertIn("\x1b[32m", out)


if __name__ == "__main__":
    unittest.main()

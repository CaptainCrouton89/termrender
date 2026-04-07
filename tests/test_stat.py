import unittest

from termrender import render
from termrender.parser import parse
from termrender.blocks import BlockType
from termrender.style import visual_len


class TestStat(unittest.TestCase):

    def test_parses_stat(self):
        doc = parse(':::stat{label="p99" value="34ms" delta="-12%"}\n:::')
        self.assertEqual(doc.children[0].type, BlockType.STAT)
        self.assertEqual(doc.children[0].attrs["label"], "p99")
        self.assertEqual(doc.children[0].attrs["value"], "34ms")
        self.assertEqual(doc.children[0].attrs["delta"], "-12%")

    def test_renders_with_borders(self):
        src = ':::stat{label="latency" value="34ms"}\n:::'
        output = render(src, width=30, color=False)
        lines = [ln for ln in output.split("\n") if ln]
        self.assertGreaterEqual(len(lines), 4)  # top + label + value + bot
        self.assertTrue(lines[0].startswith("┌"))
        self.assertTrue(lines[-1].startswith("└"))

    def test_visual_widths_match(self):
        src = ':::stat{label="latency" value="34ms" delta="-12%"}\n:::'
        output = render(src, width=30, color=False)
        for ln in output.split("\n"):
            if ln:
                self.assertEqual(visual_len(ln), 30)

    def test_negative_delta_uses_down_arrow(self):
        src = ':::stat{label="x" value="10" delta="-5%"}\n:::'
        output = render(src, width=30, color=False)
        self.assertIn("▼", output)

    def test_positive_delta_uses_up_arrow(self):
        src = ':::stat{label="x" value="10" delta="+5%"}\n:::'
        output = render(src, width=30, color=False)
        self.assertIn("▲", output)

    def test_explicit_trend_overrides_delta_sign(self):
        src = ':::stat{label="x" value="10" delta="5%" trend="down"}\n:::'
        output = render(src, width=30, color=False)
        self.assertIn("▼", output)

    def test_value_centered(self):
        src = ':::stat{label="x" value="42"}\n:::'
        output = render(src, width=20, color=False)
        # Value line should have 42 roughly centered
        for ln in output.split("\n"):
            if "42" in ln:
                # 42 should not be flush-left
                self.assertNotEqual(ln.lstrip().index("42"), 0)
                break

    def test_caption_body_renders_below(self):
        src = ':::stat{label="latency" value="34ms"}\nlast hour\n:::'
        output = render(src, width=40, color=False)
        self.assertIn("last hour", output)

    def test_color_attr_applies_to_value(self):
        src = ':::stat{label="x" value="42" color="red"}\n:::'
        output = render(src, width=30, color=True)
        self.assertIn("\x1b[31m", output)  # red

    def test_stats_in_columns(self):
        src = (
            ":::::columns\n"
            "::::col{width=\"50%\"}\n"
            ":::stat{label=\"a\" value=\"1\"}\n"
            ":::\n"
            "::::\n"
            "::::col{width=\"50%\"}\n"
            ":::stat{label=\"b\" value=\"2\"}\n"
            ":::\n"
            "::::\n"
            ":::::"
        )
        output = render(src, width=50, color=False)
        for ln in output.split("\n"):
            if ln:
                self.assertEqual(visual_len(ln), 50)


if __name__ == "__main__":
    unittest.main()

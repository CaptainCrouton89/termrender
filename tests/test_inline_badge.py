import unittest

from termrender import render
from termrender.parser import parse, _expand_inline_roles
from termrender.blocks import InlineSpan
from termrender.style import visual_len


class TestInlineBadge(unittest.TestCase):

    def test_expands_simple_badge(self):
        spans = [InlineSpan(text=":badge[stable]{color=green}")]
        out = _expand_inline_roles(spans)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].text, " stable ")
        self.assertEqual(out[0].fg, "green")
        self.assertIsNotNone(out[0].bg)
        self.assertTrue(out[0].bold)

    def test_keeps_text_around_badge(self):
        spans = [InlineSpan(text="before :badge[x]{color=red} after")]
        out = _expand_inline_roles(spans)
        texts = [s.text for s in out]
        self.assertEqual(texts, ["before ", " x ", " after"])
        self.assertEqual(out[1].fg, "red")

    def test_multiple_badges_in_sequence(self):
        spans = [InlineSpan(text=":badge[a]{color=red} :badge[b]{color=blue}")]
        out = _expand_inline_roles(spans)
        # 3 spans: badge a, " ", badge b
        badge_spans = [s for s in out if s.fg]
        self.assertEqual(len(badge_spans), 2)

    def test_badge_default_color(self):
        spans = [InlineSpan(text=":badge[hi]")]
        out = _expand_inline_roles(spans)
        self.assertEqual(out[0].fg, "blue")

    def test_unknown_color_falls_back(self):
        spans = [InlineSpan(text=":badge[hi]{color=mauve}")]
        out = _expand_inline_roles(spans)
        # Falls back to blue
        self.assertEqual(out[0].fg, "blue")

    def test_unknown_role_kept_as_text(self):
        spans = [InlineSpan(text=":foo[bar]{x=1}")]
        out = _expand_inline_roles(spans)
        self.assertEqual(out[0].text, ":foo[bar]{x=1}")
        self.assertIsNone(out[0].fg)

    def test_preserves_outer_formatting(self):
        spans = [InlineSpan(text="hello :badge[ok]{color=green} world", bold=True)]
        out = _expand_inline_roles(spans)
        # Surrounding text keeps bold
        self.assertTrue(out[0].bold)
        self.assertTrue(out[2].bold)

    def test_code_spans_untouched(self):
        spans = [InlineSpan(text=":badge[x]{color=red}", code=True)]
        out = _expand_inline_roles(spans)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].code)
        self.assertIsNone(out[0].fg)

    def test_full_render_with_badge(self):
        src = "Status: :badge[ok]{color=green}"
        out = render(src, width=40, color=False)
        self.assertIn("Status:", out)
        self.assertIn("ok", out)

    def test_render_with_color_emits_ansi(self):
        src = "Status: :badge[ok]{color=green}"
        out = render(src, width=40, color=True)
        self.assertIn("\x1b[32m", out)  # green fg

    def test_visual_width_correct_with_badge(self):
        src = "Status: :badge[ok]{color=green}"
        out = render(src, width=40, color=False)
        for ln in out.split("\n"):
            if ln:
                self.assertEqual(visual_len(ln), 40)

    def test_badge_in_paragraph_after_mistune_split(self):
        # mistune splits text on `[` — verify the merge pass reassembles
        src = "Tag: :badge[v3.2.0]{color=blue}"
        doc = parse(src)
        # Should produce a paragraph whose spans contain a badge span
        para = doc.children[0]
        badge_spans = [s for s in para.text if s.fg == "blue"]
        self.assertEqual(len(badge_spans), 1)
        self.assertIn("v3.2.0", badge_spans[0].text)


if __name__ == "__main__":
    unittest.main()

"""Tests for MyST Markdown syntax support in the parser."""

import unittest

from termrender.blocks import BlockType
from termrender.parser import parse, _strip_options


class TestBacktickFenceDirective(unittest.TestCase):
    """Feature 1: Backtick fence directive syntax."""

    def test_basic_backtick_fence_directive(self):
        """```{panel}\ncontent\n``` → BlockType.PANEL"""
        doc = parse("```{panel}\ncontent\n```")
        self.assertEqual(len(doc.children), 1)
        self.assertEqual(doc.children[0].type, BlockType.PANEL)

    def test_backtick_fence_with_option_lines(self):
        """```{panel}\n:title: Hello\ncontent\n``` → panel with title attr"""
        doc = parse("```{panel}\n:title: Hello\ncontent\n```")
        panel = doc.children[0]
        self.assertEqual(panel.type, BlockType.PANEL)
        self.assertEqual(panel.attrs["title"], "Hello")

    def test_backtick_mermaid_directive(self):
        """```{mermaid}\ngraph LR\nA-->B\n``` → BlockType.MERMAID"""
        doc = parse("```{mermaid}\ngraph LR\nA-->B\n```")
        self.assertEqual(len(doc.children), 1)
        block = doc.children[0]
        self.assertEqual(block.type, BlockType.MERMAID)
        self.assertIn("graph LR", block.attrs["source"])

    def test_bare_mermaid_still_works(self):
        """```mermaid\ngraph LR\n``` → BlockType.MERMAID (backward compat)"""
        doc = parse("```mermaid\ngraph LR\nA-->B\n```")
        self.assertEqual(doc.children[0].type, BlockType.MERMAID)

    def test_empty_body_backtick_directive(self):
        """```{panel}\n``` → panel with no children"""
        doc = parse("```{panel}\n```")
        panel = doc.children[0]
        self.assertEqual(panel.type, BlockType.PANEL)

    def test_backtick_fence_with_argument(self):
        """```{code-block} python\nprint("hi")\n``` → attrs["argument"] = "python" """
        doc = parse('```{code-block} python\nprint("hi")\n```')
        block = doc.children[0]
        self.assertEqual(block.attrs.get("argument"), "python")

    def test_four_backtick_fence(self):
        """````{panel}\ncontent\n```` → works via mistune"""
        doc = parse("````{panel}\ncontent\n````")
        self.assertEqual(len(doc.children), 1)
        self.assertEqual(doc.children[0].type, BlockType.PANEL)


class TestDirectiveOptionLines(unittest.TestCase):
    """Feature 2: Directive option lines."""

    def test_colon_directive_with_options(self):
        """:::panel\n:title: Hi\n:color: blue\ncontent\n::: → attrs have title and color"""
        doc = parse(":::panel\n:title: Hi\n:color: blue\ncontent\n:::")
        panel = doc.children[0]
        self.assertEqual(panel.attrs["title"], "Hi")
        self.assertEqual(panel.attrs["color"], "blue")

    def test_options_dont_override_inline_attrs(self):
        """:::panel{title="Inline"}\n:title: Option\n::: → title is "Inline" """
        doc = parse(':::panel{title="Inline"}\n:title: Option\n:::')
        panel = doc.children[0]
        self.assertEqual(panel.attrs["title"], "Inline")

    def test_body_after_options_preserved(self):
        """Body content after option lines is preserved correctly."""
        doc = parse(":::panel\n:title: Hi\nHello world\n:::")
        panel = doc.children[0]
        self.assertEqual(panel.attrs["title"], "Hi")
        # Body should have been parsed and contain a paragraph with "Hello world"
        self.assertTrue(len(panel.children) > 0)

    def test_non_option_lines_not_eaten(self):
        """:not-an-option without trailing colon-space should not be eaten."""
        doc = parse(":::panel\n:not-an-option\ncontent\n:::")
        panel = doc.children[0]
        # ":not-an-option" doesn't match `:key: value` pattern, so no options
        self.assertNotIn("not-an-option", panel.attrs)


class TestStripOptions(unittest.TestCase):
    """Unit tests for _strip_options."""

    def test_empty_body(self):
        opts, body = _strip_options("")
        self.assertEqual(opts, {})
        self.assertEqual(body, "")

    def test_no_options(self):
        opts, body = _strip_options("just content\nmore content")
        self.assertEqual(opts, {})
        self.assertEqual(body, "just content\nmore content")

    def test_options_with_blank_lines(self):
        opts, body = _strip_options(":title: Hi\n\n:color: blue\ncontent")
        self.assertEqual(opts, {"title": "Hi", "color": "blue"})
        self.assertEqual(body, "content")

    def test_option_key_with_hyphens(self):
        opts, body = _strip_options(":my-key: value\ncontent")
        self.assertEqual(opts, {"my-key": "value"})
        self.assertEqual(body, "content")


if __name__ == "__main__":
    unittest.main()

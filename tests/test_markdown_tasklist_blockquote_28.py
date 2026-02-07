"""Tests for task list and blockquote recognition in Markdown parser.

Issue #28: Additional Markdown Parser features.
Task lists (- [ ], - [x]) and blockquotes (> text) should be recognized
as element types.
"""

import tempfile
from pathlib import Path


class TestTaskListRecognition:
    """Task lists (- [ ] and - [x]) are recognized as list elements."""

    def test_unchecked_task_list_recognized(self):
        """Unchecked task list items are recognized."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Tasks

- [ ] Buy milk
- [ ] Write tests
- [ ] Deploy app
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        task_lists = [e for e in list_elements if e.attributes.get("list_type") == "task"]
        assert len(task_lists) >= 1

    def test_checked_task_list_recognized(self):
        """Checked task list items are recognized."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Tasks

- [x] Buy milk
- [x] Write tests
- [ ] Deploy app
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        task_lists = [e for e in list_elements if e.attributes.get("list_type") == "task"]
        assert len(task_lists) >= 1

    def test_task_list_has_correct_source_location(self):
        """Task list has correct start and end line."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Tasks

- [ ] First task
- [x] Second task
- [ ] Third task
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        task_lists = [e for e in list_elements if e.attributes.get("list_type") == "task"]
        assert len(task_lists) == 1
        assert task_lists[0].source_location.line == 3
        assert task_lists[0].source_location.end_line == 5

    def test_task_list_has_correct_parent_section(self):
        """Task list has correct parent section."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

## Todo

- [ ] Item A
- [x] Item B
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        task_lists = [e for e in list_elements if e.attributes.get("list_type") == "task"]
        assert len(task_lists) >= 1
        assert "todo" in task_lists[0].parent_section

    def test_task_list_content_is_stored(self):
        """Task list content lines are stored in attributes."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Tasks

- [ ] Buy milk
- [x] Write tests
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        task_lists = [e for e in list_elements if e.attributes.get("list_type") == "task"]
        assert len(task_lists) >= 1
        assert "content" in task_lists[0].attributes
        assert "Buy milk" in task_lists[0].attributes["content"]

    def test_task_list_separate_from_regular_unordered_list(self):
        """Task list is recognized as separate from regular unordered list."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Mixed Lists

- Regular item 1
- Regular item 2

- [ ] Task item 1
- [x] Task item 2
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        list_elements = [e for e in doc.elements if e.type == "list"]
        unordered = [e for e in list_elements if e.attributes.get("list_type") == "unordered"]
        task = [e for e in list_elements if e.attributes.get("list_type") == "task"]
        assert len(unordered) >= 1
        assert len(task) >= 1


class TestBlockquoteRecognition:
    """Blockquotes (> text) are recognized as elements."""

    def test_simple_blockquote_recognized(self):
        """Simple blockquote is recognized."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Quotes

> This is a blockquote.
> It has multiple lines.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        blockquotes = [e for e in doc.elements if e.type == "blockquote"]
        assert len(blockquotes) >= 1

    def test_blockquote_has_correct_source_location(self):
        """Blockquote has correct start and end line."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

> First line of quote.
> Second line of quote.
> Third line of quote.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        blockquotes = [e for e in doc.elements if e.type == "blockquote"]
        assert len(blockquotes) == 1
        assert blockquotes[0].source_location.line == 3
        assert blockquotes[0].source_location.end_line == 5

    def test_blockquote_has_correct_parent_section(self):
        """Blockquote has correct parent section."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

## Quotes Section

> A famous quote.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        blockquotes = [e for e in doc.elements if e.type == "blockquote"]
        assert len(blockquotes) >= 1
        assert "quotes-section" in blockquotes[0].parent_section

    def test_blockquote_content_is_stored(self):
        """Blockquote content is stored in attributes."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Quotes

> First line.
> Second line.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        blockquotes = [e for e in doc.elements if e.type == "blockquote"]
        assert len(blockquotes) >= 1
        assert "content" in blockquotes[0].attributes
        assert "First line" in blockquotes[0].attributes["content"]

    def test_multiple_blockquotes_separated_by_text(self):
        """Multiple blockquotes separated by other content are recognized separately."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Document

> First quote.

Some text.

> Second quote.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        blockquotes = [e for e in doc.elements if e.type == "blockquote"]
        assert len(blockquotes) == 2

    def test_blockquote_not_detected_inside_code_block(self):
        """Blockquotes inside code blocks are not detected."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Code

```
> This is not a blockquote
> It's inside a code block
```
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        blockquotes = [e for e in doc.elements if e.type == "blockquote"]
        assert len(blockquotes) == 0

    def test_empty_blockquote_line(self):
        """Blockquote with empty continuation line (just >) is part of the quote."""
        from dacli.markdown_parser import MarkdownStructureParser

        parser = MarkdownStructureParser()
        content = """# Quotes

> First paragraph.
>
> Second paragraph.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()
            doc = parser.parse_file(Path(f.name))

        blockquotes = [e for e in doc.elements if e.type == "blockquote"]
        assert len(blockquotes) == 1
        assert blockquotes[0].source_location.line == 3
        assert blockquotes[0].source_location.end_line == 5

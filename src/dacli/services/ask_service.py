"""Ask service for the experimental LLM-powered documentation Q&A.

Searches documentation for relevant sections, builds a context prompt,
and calls an LLM provider to answer the user's question.
"""

from dacli.file_handler import FileSystemHandler
from dacli.services.llm_provider import get_provider
from dacli.structure_index import StructureIndex

MAX_SECTION_CHARS = 4000
MAX_TOTAL_CONTEXT_CHARS = 20000
DEFAULT_MAX_SECTIONS = 5

SYSTEM_PROMPT = """\
You are a documentation assistant. Answer the user's question based ONLY on the \
provided documentation context. If the context doesn't contain enough information \
to answer the question, say so clearly. Do not make up information.

Keep your answer concise and focused on the question asked."""


def _get_section_content(
    path: str,
    index: StructureIndex,
    file_handler: FileSystemHandler,
) -> str | None:
    """Retrieve the text content of a section by path.

    Returns None if the section or its file cannot be read.
    """
    section = index.get_section(path)
    if section is None:
        return None

    try:
        file_content = file_handler.read_file(section.source_location.file)
        lines = file_content.splitlines()

        start_line = section.source_location.line - 1  # Convert to 0-based
        end_line = section.source_location.end_line
        if end_line is None:
            end_line = len(lines)

        return "\n".join(lines[start_line:end_line])
    except Exception:
        return None


def _build_context(
    question: str,
    index: StructureIndex,
    file_handler: FileSystemHandler,
    max_sections: int = DEFAULT_MAX_SECTIONS,
) -> list[dict]:
    """Search for relevant sections and assemble context for the LLM.

    Args:
        question: The user's question to search for.
        index: Structure index for searching.
        file_handler: File handler for reading content.
        max_sections: Maximum number of sections to include.

    Returns:
        List of dicts with 'path', 'title', and 'content' keys.
    """
    results = index.search(
        query=question,
        scope=None,
        case_sensitive=False,
        max_results=max_sections,
    )

    context_sections = []
    total_chars = 0

    for result in results:
        if total_chars >= MAX_TOTAL_CONTEXT_CHARS:
            break

        content = _get_section_content(result.path, index, file_handler)
        if content is None:
            continue

        # Truncate long sections
        if len(content) > MAX_SECTION_CHARS:
            content = content[:MAX_SECTION_CHARS] + "\n... (truncated)"

        # Check total context limit
        if total_chars + len(content) > MAX_TOTAL_CONTEXT_CHARS:
            remaining = MAX_TOTAL_CONTEXT_CHARS - total_chars
            if remaining > 200:
                content = content[:remaining] + "\n... (truncated)"
            else:
                break

        # Look up the section title
        section = index.get_section(result.path)
        title = section.title if section else result.path

        context_sections.append({
            "path": result.path,
            "title": title,
            "content": content,
        })
        total_chars += len(content)

    return context_sections


def ask_documentation(
    question: str,
    index: StructureIndex,
    file_handler: FileSystemHandler,
    provider_name: str | None = None,
    max_sections: int = DEFAULT_MAX_SECTIONS,
) -> dict:
    """Answer a question about the documentation using an LLM.

    This is an experimental feature that searches documentation for relevant
    sections and uses an LLM to generate an answer.

    Args:
        question: The user's question.
        index: Structure index for searching.
        file_handler: File handler for reading content.
        provider_name: LLM provider name (None for auto-detect).
        max_sections: Maximum sections to include as context.

    Returns:
        Dict with 'answer', 'provider', 'sections_used', and 'experimental' keys.
        On error, returns dict with 'error' key.
    """
    try:
        provider = get_provider(preferred=provider_name)
    except RuntimeError as e:
        return {"error": str(e)}

    # Build context from documentation
    context_sections = _build_context(question, index, file_handler, max_sections)

    # Assemble the user message with context
    if context_sections:
        context_text = "\n\n---\n\n".join(
            f"## {s['title']} (path: {s['path']})\n\n{s['content']}"
            for s in context_sections
        )
        user_message = (
            f"Documentation context:\n\n{context_text}\n\n---\n\n"
            f"Question: {question}"
        )
    else:
        user_message = (
            f"No relevant documentation sections were found for the search.\n\n"
            f"Question: {question}"
        )

    # Call the LLM
    try:
        response = provider.ask(SYSTEM_PROMPT, user_message)
    except RuntimeError as e:
        return {"error": str(e)}

    return {
        "answer": response.text,
        "provider": response.provider,
        "model": response.model,
        "sections_used": len(context_sections),
        "experimental": True,
    }

"""Ask service for the experimental LLM-powered documentation Q&A.

Implements iterative context building as described in Issue #186:
1. Collect all sections from the documentation structure
2. Iterate through sections one by one, passing each + question + previous
   findings to the LLM — the LLM decides relevance, not keyword search
3. Consolidate all findings into a final answer with source references
"""

from dacli.file_handler import FileSystemHandler
from dacli.services.llm_provider import get_provider
from dacli.structure_index import StructureIndex

MAX_SECTION_CHARS = 4000

ITERATION_PROMPT = """\
Question: {question}

Previous findings:
{previous_findings}

Current section: {section_path} - "{section_title}"
{section_content}

Task:
1. Does this section contain information relevant to the question?
2. If yes, extract key points.
3. Note what information is still missing to fully answer the question.

Respond concisely:
KEY_POINTS: [bullet list of relevant findings, or "none"]
MISSING: [what's still needed, or "nothing"]"""

CONSOLIDATION_PROMPT = """\
Question: {question}

All findings from documentation:
{accumulated_findings}

Sections consulted:
{sources_list}

Task: Provide a final, consolidated answer that:
1. Directly answers the question
2. Synthesizes information from all sections
3. Is clear and well-structured

Provide only the answer, no meta-commentary."""


def _get_all_sections(index: StructureIndex) -> list[dict]:
    """Get all sections from the index as a flat list.

    Walks the hierarchical structure and returns all sections
    with their path, title, and level.
    """
    structure = index.get_structure()
    sections = []

    def _walk(section_list: list[dict]):
        for s in section_list:
            sections.append({
                "path": s["path"],
                "title": s["title"],
                "level": s["level"],
            })
            if s.get("children"):
                _walk(s["children"])

    _walk(structure.get("sections", []))
    return sections


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

        content = "\n".join(lines[start_line:end_line])

        # Truncate overly long sections
        if len(content) > MAX_SECTION_CHARS:
            content = content[:MAX_SECTION_CHARS] + "\n... (truncated)"

        return content
    except Exception:
        return None


def ask_documentation(
    question: str,
    index: StructureIndex,
    file_handler: FileSystemHandler,
    provider_name: str | None = None,
    max_sections: int | None = None,
) -> dict:
    """Answer a question about the documentation using iterative LLM reasoning.

    Implements the iterative approach from Issue #186:
    1. Collect all sections from the documentation
    2. Iterate through each section, letting the LLM decide relevance
       and accumulate findings
    3. Consolidate all findings into a final answer

    No keyword search is used — the LLM handles semantic matching,
    so synonyms and natural language questions work correctly.

    Args:
        question: The user's question.
        index: Structure index for searching.
        file_handler: File handler for reading content.
        provider_name: LLM provider name (None for auto-detect).
        max_sections: Limit sections to iterate (None = all sections).

    Returns:
        Dict with 'answer', 'provider', 'sources', 'iterations',
        'sections_used', and 'experimental' keys.
        On error, returns dict with 'error' key.
    """
    try:
        provider = get_provider(preferred=provider_name)
    except RuntimeError as e:
        return {"error": str(e)}

    # Step 1: Get all sections from the documentation
    all_sections = _get_all_sections(index)

    # Optionally limit sections (None = all)
    if max_sections is not None:
        sections_to_check = all_sections[:max_sections]
    else:
        sections_to_check = all_sections

    # Step 2: Iterate through sections, accumulating findings
    accumulated_findings = ""
    sources = []
    iterations = 0

    for section_info in sections_to_check:
        content = _get_section_content(
            section_info["path"], index, file_handler
        )
        if content is None:
            continue

        iterations += 1

        prompt = ITERATION_PROMPT.format(
            question=question,
            previous_findings=accumulated_findings or "(none yet)",
            section_path=section_info["path"],
            section_title=section_info["title"],
            section_content=content,
        )

        try:
            response = provider.ask(
                "You are analyzing documentation sections to answer a question. "
                "Extract relevant key points concisely.",
                prompt,
            )
            accumulated_findings += (
                f"\n\nFrom '{section_info['title']}'"
                f" ({section_info['path']}):\n"
                f"{response.text}"
            )
            sources.append({
                "path": section_info["path"],
                "title": section_info["title"],
            })
        except RuntimeError:
            continue

    # Step 3: Consolidation
    if accumulated_findings:
        sources_list = "\n".join(
            f"- {s['title']} ({s['path']})" for s in sources
        )
        consolidation_prompt = CONSOLIDATION_PROMPT.format(
            question=question,
            accumulated_findings=accumulated_findings,
            sources_list=sources_list,
        )
        try:
            final_response = provider.ask(
                "You are a documentation assistant. Provide a clear, "
                "consolidated answer based on the findings. Answer in "
                "the same language as the question.",
                consolidation_prompt,
            )
            answer = final_response.text
        except RuntimeError as e:
            return {"error": f"Consolidation failed: {e}"}
    else:
        try:
            response = provider.ask(
                "You are a documentation assistant.",
                f"No documentation sections were available.\n\n"
                f"Question: {question}\n\n"
                f"Please let the user know that no documentation "
                f"content was found.",
            )
            answer = response.text
        except RuntimeError as e:
            return {"error": str(e)}

    return {
        "answer": answer,
        "provider": provider.name,
        "model": getattr(provider, "model", None),
        "sources": sources,
        "iterations": iterations,
        "sections_used": len(sources),
        "experimental": True,
    }

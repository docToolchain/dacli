"""Ask service for the experimental LLM-powered documentation Q&A.

Implements iterative context building as described in Issue #186:
1. Search for relevant sections (keyword extraction from question)
2. Iterate through sections one by one, passing each + question + previous
   findings to the LLM
3. Consolidate all findings into a final answer with source references
"""

import re

from dacli.file_handler import FileSystemHandler
from dacli.services.llm_provider import get_provider
from dacli.structure_index import StructureIndex

MAX_SECTION_CHARS = 4000
MAX_TOTAL_CONTEXT_CHARS = 20000
DEFAULT_MAX_SECTIONS = 5

# Stop words for keyword extraction (German + English)
_STOP_WORDS = frozenset(
    # German
    "aber alle allem allen aller alles als also am an andere anderem anderen "
    "anderer anderes auch auf aus bei bin bis bist da damit dann das dass "
    "dein deine deinem deinen deiner dem den denn der des die dies diese "
    "diesem diesen dieser dieses doch dort du durch ein eine einem einen "
    "einer er es etwas euch euer eure eurem euren eurer für gegen gibt "
    "hab habe haben hat hatte hätte ich ihm ihn ihnen ihr ihre ihrem ihren "
    "ihrer im in indem ins ist ja jede jedem jeden jeder jedes jedoch "
    "jene jenem jenen jener jenes kann kein keine keinem keinen keiner "
    "man manche manchem manchen mancher manches mein meine meinem meinen "
    "meiner mit muss musste nach nicht nichts noch nun nur ob oder ohne "
    "sehr sein seine seinem seinen seiner seit sich sie sind so solche "
    "solchem solchen solcher sondern um und uns unser unsere unserem unseren "
    "unserer unter viel vom von vor was welche welchem welchen welcher "
    "welches wenn wer wie wir wird wollen worden wurde würde zu zum zur "
    # English
    "a about above after again against all am an and any are aren as at "
    "be because been before being below between both but by can could "
    "did didn do does doesn doing don down during each few for from "
    "further get got had has have having he her here hers herself him "
    "himself his how i if in into is isn it its itself just let like ll "
    "me might more most mustn my myself no nor not now of off on once "
    "only or other our ours ourselves out over own re same shall she "
    "should shouldn so some such than that the their theirs them "
    "themselves then there these they this those through to too under "
    "until up us ve very was wasn we were weren what when where which "
    "while who whom why will with won would wouldn you your yours "
    "yourself yourselves".split()
)

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


def _extract_keywords(question: str) -> list[str]:
    """Extract search keywords from a natural language question.

    Removes stop words and punctuation, returning meaningful terms.
    Falls back to all words if everything is a stop word.
    """
    # Remove punctuation and lowercase
    cleaned = re.sub(r"[^\w\s]", "", question.lower())
    words = cleaned.split()

    # Filter stop words
    keywords = [w for w in words if w not in _STOP_WORDS and len(w) > 1]

    # Fallback: if all words were stop words, return original words
    if not keywords and words:
        keywords = [w for w in words if len(w) > 1]

    return keywords


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
    """Search for relevant sections and return their content.

    Uses keyword extraction to find sections matching the question.

    Args:
        question: The user's question.
        index: Structure index for searching.
        file_handler: File handler for reading content.
        max_sections: Maximum number of sections to include.

    Returns:
        List of dicts with 'path', 'title', and 'content' keys.
    """
    keywords = _extract_keywords(question)

    # Search with each keyword and merge results (deduplicate by path)
    seen_paths = set()
    all_results = []

    for keyword in keywords:
        results = index.search(
            query=keyword,
            scope=None,
            case_sensitive=False,
            max_results=max_sections * 2,  # Fetch more, deduplicate later
        )
        for result in results:
            if result.path not in seen_paths:
                seen_paths.add(result.path)
                all_results.append(result)

    # Also try the full question as-is (might match multi-word phrases)
    full_results = index.search(
        query=question,
        scope=None,
        case_sensitive=False,
        max_results=max_sections,
    )
    for result in full_results:
        if result.path not in seen_paths:
            seen_paths.add(result.path)
            all_results.append(result)

    # Limit to max_sections
    all_results = all_results[:max_sections]

    context_sections = []
    total_chars = 0

    for result in all_results:
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
    """Answer a question about the documentation using iterative LLM reasoning.

    Implements the iterative approach from Issue #186:
    1. Find relevant sections via keyword extraction + search
    2. Iterate through each section, accumulating findings
    3. Consolidate all findings into a final answer

    Args:
        question: The user's question.
        index: Structure index for searching.
        file_handler: File handler for reading content.
        provider_name: LLM provider name (None for auto-detect).
        max_sections: Maximum sections to iterate through.

    Returns:
        Dict with 'answer', 'provider', 'sources', 'iterations',
        'sections_used', and 'experimental' keys.
        On error, returns dict with 'error' key.
    """
    try:
        provider = get_provider(preferred=provider_name)
    except RuntimeError as e:
        return {"error": str(e)}

    # Step 1: Find relevant sections
    context_sections = _build_context(question, index, file_handler, max_sections)

    # Step 2: Iterate through sections, accumulating findings
    accumulated_findings = ""
    sources = []
    iterations = 0

    for section in context_sections:
        iterations += 1

        prompt = ITERATION_PROMPT.format(
            question=question,
            previous_findings=accumulated_findings or "(none yet)",
            section_path=section["path"],
            section_title=section["title"],
            section_content=section["content"],
        )

        try:
            response = provider.ask(
                "You are analyzing documentation sections to answer a question. "
                "Extract relevant key points concisely.",
                prompt,
            )
            accumulated_findings += (
                f"\n\nFrom '{section['title']}' ({section['path']}):\n"
                f"{response.text}"
            )
            sources.append({"path": section["path"], "title": section["title"]})
        except RuntimeError:
            # If one iteration fails, continue with others
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
                "You are a documentation assistant. Provide a clear, consolidated "
                "answer based on the findings. Answer in the same language as the question.",
                consolidation_prompt,
            )
            answer = final_response.text
        except RuntimeError as e:
            return {"error": f"Consolidation failed: {e}"}
    else:
        # No sections found - ask LLM to respond gracefully
        try:
            response = provider.ask(
                "You are a documentation assistant.",
                f"No relevant documentation sections were found for the search.\n\n"
                f"Question: {question}\n\n"
                f"Please let the user know that you couldn't find relevant "
                f"documentation to answer their question.",
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

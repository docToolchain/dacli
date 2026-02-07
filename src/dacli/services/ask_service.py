"""Ask service for the experimental LLM-powered documentation Q&A.

Implements iterative context building as described in Issue #186:
1. Collect all documentation files from the index
2. Iterate through files one by one, passing each file's content + question
   + previous findings to the LLM — the LLM decides relevance
3. Consolidate all findings into a final answer with source references

File-based iteration is more efficient than section-based: a typical project
has ~35 files vs ~460 sections, reducing LLM calls by ~13x while providing
better context (full file content) per call.
"""

from collections.abc import Callable
from pathlib import Path

from dacli.file_handler import FileSystemHandler
from dacli.services.llm_provider import get_provider
from dacli.structure_index import StructureIndex

ITERATION_PROMPT = """\
Question: {question}

Previous findings:
{previous_findings}

Current file: {file_path}
---
{file_content}
---

Task:
1. Does this file contain information relevant to the question?
2. If yes, extract key points.
3. Note what information is still missing to fully answer the question.

Respond concisely:
KEY_POINTS: [bullet list of relevant findings, or "none"]
MISSING: [what's still needed, or "nothing"]"""

CONSOLIDATION_PROMPT = """\
Question: {question}

All findings from documentation:
{accumulated_findings}

Files consulted:
{sources_list}

Task: Provide a final, consolidated answer that:
1. Directly answers the question
2. Synthesizes information from all files
3. Is clear and well-structured

Provide only the answer, no meta-commentary."""


def _get_all_files(index: StructureIndex) -> list[dict]:
    """Get all documentation files from the index.

    Returns a list of dicts with 'file' (Path) and 'name' (str) keys,
    sorted by file name for deterministic ordering.
    """
    files = []
    for file_path in sorted(index._file_to_sections.keys()):
        files.append({
            "file": file_path,
            "name": file_path.name,
        })
    return files


def _read_file_content(
    file_path: Path,
    file_handler: FileSystemHandler,
) -> str | None:
    """Read the full content of a documentation file.

    Returns None if the file cannot be read.
    """
    try:
        return file_handler.read_file(file_path)
    except Exception:
        return None


def ask_documentation(
    question: str,
    index: StructureIndex,
    file_handler: FileSystemHandler,
    provider_name: str | None = None,
    max_sections: int | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> dict:
    """Answer a question about the documentation using iterative LLM reasoning.

    Implements the iterative approach from Issue #186:
    1. Collect all documentation files
    2. Iterate through each file, letting the LLM decide relevance
       and accumulate findings
    3. Consolidate all findings into a final answer

    No keyword search is used — the LLM handles semantic matching,
    so synonyms and natural language questions work correctly.

    Args:
        question: The user's question.
        index: Structure index for searching.
        file_handler: File handler for reading content.
        provider_name: LLM provider name (None for auto-detect).
        max_sections: Limit files to iterate (None = all files).

    Returns:
        Dict with 'answer', 'provider', 'sources', 'iterations',
        'sections_used', and 'experimental' keys.
        On error, returns dict with 'error' key.
    """
    try:
        provider = get_provider(preferred=provider_name)
    except RuntimeError as e:
        return {"error": str(e)}

    # Step 1: Get all documentation files
    all_files = _get_all_files(index)

    # Optionally limit files (None = all)
    if max_sections is not None:
        files_to_check = all_files[:max_sections]
    else:
        files_to_check = all_files

    # Step 2: Iterate through files, accumulating findings
    accumulated_findings = ""
    sources = []
    iterations = 0

    total_files = len(files_to_check)

    for file_info in files_to_check:
        content = _read_file_content(file_info["file"], file_handler)
        if content is None or not content.strip():
            continue

        iterations += 1

        if progress_callback:
            progress_callback(iterations, total_files, file_info["name"])

        prompt = ITERATION_PROMPT.format(
            question=question,
            previous_findings=accumulated_findings or "(none yet)",
            file_path=file_info["name"],
            file_content=content,
        )

        try:
            response = provider.ask(
                "You are analyzing documentation files to answer a question. "
                "Extract relevant key points concisely.",
                prompt,
            )
            accumulated_findings += (
                f"\n\nFrom '{file_info['name']}':\n"
                f"{response.text}"
            )
            sources.append({
                "file": str(file_info["file"]),
                "name": file_info["name"],
            })
        except RuntimeError:
            continue

    # Step 3: Consolidation
    if accumulated_findings:
        sources_list = "\n".join(
            f"- {s['name']}" for s in sources
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
                f"No documentation files were available.\n\n"
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

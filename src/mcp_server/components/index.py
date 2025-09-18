from typing import Dict, List
from mcp_server.models.document import Document, Section

class DocumentIndex:
    """
    An in-memory index for parsed documents, allowing retrieval of sections by path.
    """
    def __init__(self):
        self._sections: Dict[str, Section] = {}
        self._documents: Dict[str, Document] = {}

    def _generate_section_path(self, section: Section) -> str:
        """Generates a canonical path for a section (e.g., 'level-1-title')."""
        # For now, just use the title, lowercased and hyphenated
        return section.title.lower().replace(' ', '-')

    def add_document(self, document: Document):
        """
        Adds all sections from a parsed Document to the index.
        """
        self._documents[document.filepath] = document

        def _add_sections_recursive(sections: List[Section]):
            for section in sections:
                path = self._generate_section_path(section)
                self._sections[path] = section
                _add_sections_recursive(section.subsections)

        _add_sections_recursive(document.sections)

    def get_section_by_path(self, path: str) -> Section | None:
        """
        Retrieves a section from the index by its canonical path.
        """
        return self._sections.get(path)

    def get_document_by_path(self, filepath: str) -> Document | None:
        """
        Retrieves a full Document object from the index by its filepath.
        """
        return self._documents.get(filepath)

    def get_all_top_level_sections(self) -> List[Section]:
        """
        Returns a list of all top-level sections from all indexed documents.
        """
        all_top_sections: List[Section] = []
        for doc in self._documents.values():
            all_top_sections.extend(doc.sections)
        return all_top_sections

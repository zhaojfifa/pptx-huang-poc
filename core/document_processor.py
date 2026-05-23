"""
Document processor: converts user attachments (pptx/docx/txt/pdf) to markdown.
"""

import logging
from pathlib import Path

from skills.skill_markitdown.markitdown_skill import MarkItDownSkill

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self):
        self.md_skill = MarkItDownSkill()

    def process(self, file_paths: list) -> str:
        """Convert multiple documents to a single combined markdown string."""
        parts = []
        for fp in file_paths:
            path = Path(fp)
            if not path.exists():
                logger.warning(f"File not found, skipping: {fp}")
                continue
            logger.info(f"Processing document: {fp}")
            try:
                md = self.md_skill.convert(str(path))
                parts.append(f"## Source: {path.name}\n\n{md}\n")
            except Exception as e:
                logger.error(f"Failed to process {fp}: {e}")
                parts.append(f"## Source: {path.name}\n\n[Error processing file: {e}]\n")
        return "\n".join(parts)

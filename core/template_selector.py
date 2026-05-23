"""
Template selector: uses LLM to pick the best template from the database.
"""

import json
import logging

from database.db import TemplateDAO
from skills.skill_llm.llm_skill import LLMSkill

logger = logging.getLogger(__name__)


class TemplateSelector:
    def __init__(self):
        self.llm = LLMSkill()

    def select(self, user_requirements: str, document_markdown: str) -> dict:
        templates = TemplateDAO.get_all()
        if not templates:
            logger.warning("No templates in database.")
            return None

        if len(templates) == 1:
            logger.info(f"Only one template available, selecting ID={templates[0]['id']}")
            return templates[0]

        # Build prompt
        template_summaries = []
        for t in templates:
            style = t.get("overall_style") or {}
            summary = {
                "id": t["id"],
                "name": t["name"],
                "style_name": style.get("style_name", "Unknown"),
                "description": style.get("description", ""),
                "color_palette": style.get("color_palette", []),
                "design_keywords": style.get("design_keywords", []),
                "target_audience": style.get("target_audience", ""),
                "content_suitability": style.get("content_suitability", ""),
            }
            template_summaries.append(summary)

        system = "You are a PPT design consultant. Select the best template for user's needs. Output JSON only."
        prompt = f"""
User requirements:
```
{user_requirements}
```

Document content summary (first 1500 chars):
```
{document_markdown[:1500]}
```

Available templates:
```json
{json.dumps(template_summaries, ensure_ascii=False, indent=2)}
```

Please select the most suitable template and return JSON:
{{
    "selected_template_id": <int>,
    "reason": "<why this template fits>",
    "confidence": "<high/medium/low>"
}}
"""
        logger.info("Asking LLM to select template...")
        result = self.llm.chat_structured(prompt, system=system)
        selected_id = result.get("selected_template_id")
        logger.info(f"LLM selected template ID={selected_id}, reason={result.get('reason')}")

        for t in templates:
            if t["id"] == selected_id:
                return t

        # Fallback to first
        logger.warning("LLM returned invalid ID, falling back to first template.")
        return templates[0]

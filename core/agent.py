"""
Main Agent Orchestrator

Coordinates the full PPT generation pipeline with checkpoints and logging.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from config.settings import LOGS_DIR, OUTPUT_DIR
from database.db import GenerationJobDAO, TemplateDAO, TemplatePageDAO

logger = logging.getLogger(__name__)


class PPTXAgent:
    def __init__(self):
        self._doc_processor = None
        self._template_selector = None
        self._content_generator = None
        self._layout_generator = None
        self._renderer = None

    @property
    def doc_processor(self):
        if self._doc_processor is None:
            from core.document_processor import DocumentProcessor
            self._doc_processor = DocumentProcessor()
        return self._doc_processor

    @property
    def template_selector(self):
        if self._template_selector is None:
            from core.template_selector import TemplateSelector
            self._template_selector = TemplateSelector()
        return self._template_selector

    @property
    def content_generator(self):
        if self._content_generator is None:
            from core.content_generator import ContentGenerator
            self._content_generator = ContentGenerator()
        return self._content_generator

    @property
    def layout_generator(self):
        if self._layout_generator is None:
            from core.layout_generator import LayoutGenerator
            self._layout_generator = LayoutGenerator()
        return self._layout_generator

    @property
    def renderer(self):
        if self._renderer is None:
            from core.ppt_renderer import PPTRenderer
            self._renderer = PPTRenderer()
        return self._renderer

    def start_job(self, user_requirements: str, input_files: list) -> int:
        job_id = GenerationJobDAO.create(user_requirements, input_files)
        logger.info(f"Job {job_id} created.")
        return job_id

    def step_process_documents(self, job_id: int) -> str:
        job = GenerationJobDAO.get_by_id(job_id)
        files = job.get("input_files") or []
        md = self.doc_processor.process(files)

        log = {
            "step": "document_processing",
            "time": datetime.now().isoformat(),
            "input_files": files,
            "output_markdown_length": len(md),
        }
        GenerationJobDAO.append_log(job_id, log)
        self._save_checkpoint(job_id, "document_markdown.md", md)
        logger.info(f"Job {job_id}: documents processed.")
        return md

    def step_select_template(self, job_id: int, user_requirements: str, document_markdown: str) -> dict:
        template = self.template_selector.select(user_requirements, document_markdown)
        if not template:
            raise RuntimeError("No template available in database.")

        GenerationJobDAO.update(job_id, selected_template_id=template["id"])
        log = {
            "step": "template_selection",
            "time": datetime.now().isoformat(),
            "selected_template_id": template["id"],
            "template_name": template["name"],
        }
        GenerationJobDAO.append_log(job_id, log)
        self._save_checkpoint(job_id, "selected_template.json", self._json_dumps(template))
        logger.info(f"Job {job_id}: template selected={template['id']}")
        return template

    def step_generate_outline(self, job_id: int, user_requirements: str, document_markdown: str, template: dict) -> dict:
        pages = TemplatePageDAO.get_by_template(template["id"])
        outline = self.content_generator.generate_outline(user_requirements, document_markdown, template, pages, job_id=job_id)

        GenerationJobDAO.update(job_id, outline_json=outline)
        log = {
            "step": "outline_generation",
            "time": datetime.now().isoformat(),
            "slide_count": len(outline.get("slides", [])),
        }
        GenerationJobDAO.append_log(job_id, log)
        self._save_checkpoint(job_id, "outline.json", self._json_dumps(outline))
        logger.info(f"Job {job_id}: outline generated with {len(outline.get('slides', []))} slides.")
        return outline

    def step_generate_content_and_layout(self, job_id: int, outline: dict, document_markdown: str, template: dict) -> list:
        pages = TemplatePageDAO.get_by_template(template["id"])
        slides_data = []
        checkpoint = self._load_checkpoint(job_id, "slides_data.json")
        if checkpoint:
            slides_data = checkpoint
            logger.info(f"Job {job_id}: resumed content generation from checkpoint ({len(slides_data)} slides done).")

        from core.content_normalizer import ContentNormalizer
        normalizer = ContentNormalizer()

        all_slides = outline.get("slides", [])
        for idx, slide_outline in enumerate(all_slides):
            if idx < len(slides_data):
                continue  # skip already generated slides
            template_page = pages[idx] if idx < len(pages) else (pages[-1] if pages else {})
            try:
                pptx_path = template.get("file_path") if template else None
                slide_data = self.content_generator.generate_slide_content(slide_outline, document_markdown, template_page, job_id=job_id, pptx_path=pptx_path)

                # Hard normalization: enforce slot count and capacity limits
                if template_page:
                    from core.template_style_engine import TemplateStyleEngine
                    template_obj = TemplateDAO.get_by_id(template["id"]) if template else None
                    pptx_path = template_obj.get("file_path") if template_obj else None
                    engine = TemplateStyleEngine(template_page, pptx_path)
                    blueprint = engine.blueprint
                    slide_data = normalizer.normalize_slide_content(slide_data, blueprint)

                slides_data.append(slide_data)
            except Exception as e:
                # save partial progress before re-raising
                self._save_checkpoint(job_id, "slides_data.json", self._json_dumps(slides_data))
                logger.error(f"Job {job_id}: slide {idx + 1} content generation failed: {e}")
                raise RuntimeError(f"Slide {idx + 1}/{len(all_slides)} content generation failed: {e}")

            log = {
                "step": "slide_content_generation",
                "time": datetime.now().isoformat(),
                "slide_number": idx + 1,
            }
            GenerationJobDAO.append_log(job_id, log)

        GenerationJobDAO.update(job_id, content_markdown="\n\n---\n\n".join([s.get("markdown_content", "") for s in slides_data]))
        log = {
            "step": "all_content_generated",
            "time": datetime.now().isoformat(),
            "total_slides": len(slides_data),
        }
        GenerationJobDAO.append_log(job_id, log)
        self._save_checkpoint(job_id, "slides_data.json", self._json_dumps(slides_data))
        logger.info(f"Job {job_id}: content and layout generated for {len(slides_data)} slides.")
        return slides_data

    def step_normalize_layouts(self, job_id: int, slides_data: list) -> list:
        # Get template pages to learn style
        job = GenerationJobDAO.get_by_id(job_id)
        template_id = job.get("selected_template_id")
        template_pages = TemplatePageDAO.get_by_template(template_id) if template_id else []
        template = TemplateDAO.get_by_id(template_id) if template_id else None

        layouts = []
        blueprints = []
        for i, slide_data in enumerate(slides_data):
            template_page = template_pages[i] if i < len(template_pages) else (template_pages[-1] if template_pages else {})
            if template_page:
                from core.template_style_engine import TemplateLayoutMapper
                pptx_path = template.get("file_path") if template else None
                mapper = TemplateLayoutMapper(template_page, pptx_path)
                blueprint = mapper.generate_content_mapping(slide_data)
                blueprints.append(blueprint)
                # Also generate a legacy layout for DB compatibility / fallback
                layout = mapper.get_style_profile()
                layout["slide_number"] = i + 1
            else:
                layout = self.layout_generator.normalize_layout(slide_data, i + 1)
                blueprints.append(None)
            layouts.append(layout)

        GenerationJobDAO.update(job_id, layout_json={"layouts": layouts})
        self._save_checkpoint(job_id, "blueprints.json", self._json_dumps({"blueprints": blueprints, "template_path": template.get("file_path") if template else None}))
        log = {
            "step": "layout_normalization",
            "time": datetime.now().isoformat(),
            "layout_count": len(layouts),
        }
        GenerationJobDAO.append_log(job_id, log)
        self._save_checkpoint(job_id, "layouts.json", self._json_dumps(layouts))
        logger.info(f"Job {job_id}: layouts normalized.")
        return layouts

    def _render_with_template(self, job_id: int, output_path: str):
        """Render using template clone mode if template is available."""
        job = GenerationJobDAO.get_by_id(job_id)
        template_id = job.get("selected_template_id")
        template = TemplateDAO.get_by_id(template_id) if template_id else None
        template_path = template.get("file_path") if template else None

        # Load slides_data and blueprints from checkpoints
        slides_data = self._load_checkpoint(job_id, "slides_data.json") or []
        blueprint_checkpoint = self._load_checkpoint(job_id, "blueprints.json")
        blueprints = blueprint_checkpoint.get("blueprints") if isinstance(blueprint_checkpoint, dict) else None

        if template_path:
            from pathlib import Path
            tp = Path(template_path)
            if tp.exists():
                self.renderer.render_from_template(slides_data, str(tp), output_path, blueprints=blueprints)
                return True
            else:
                logger.warning(f"Template path not found: {template_path}, falling back to custom build.")

        # Fallback to custom build
        layouts = self._load_checkpoint(job_id, "layouts.json") or []
        self.renderer.render(layouts, output_path)
        return True

    def step_render_preview(self, job_id: int, layouts: list) -> str:
        preview_path = str(OUTPUT_DIR / f"job_{job_id}_preview.pptx")
        self._render_with_template(job_id, preview_path)

        GenerationJobDAO.update(job_id, rendered_pptx_path=preview_path, status="preview_ready")
        log = {
            "step": "render_preview",
            "time": datetime.now().isoformat(),
            "preview_path": preview_path,
        }
        GenerationJobDAO.append_log(job_id, log)
        logger.info(f"Job {job_id}: preview rendered to {preview_path}")
        return preview_path

    def step_generate_final(self, job_id: int, layouts: list) -> str:
        final_path = str(OUTPUT_DIR / f"job_{job_id}_final.pptx")
        self._render_with_template(job_id, final_path)

        GenerationJobDAO.update(job_id, final_pptx_path=final_path, status="completed")
        log = {
            "step": "generate_final",
            "time": datetime.now().isoformat(),
            "final_path": final_path,
        }
        GenerationJobDAO.append_log(job_id, log)
        logger.info(f"Job {job_id}: final PPTX saved to {final_path}")
        return final_path

    def _save_checkpoint(self, job_id: int, filename: str, data: str):
        checkpoint_dir = LOGS_DIR / f"job_{job_id}"
        checkpoint_dir.mkdir(exist_ok=True)
        (checkpoint_dir / filename).write_text(data, encoding="utf-8")

    def _load_checkpoint(self, job_id: int, filename: str):
        checkpoint = LOGS_DIR / f"job_{job_id}" / filename
        if checkpoint.exists():
            try:
                return json.loads(checkpoint.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                return None
        return None

    @staticmethod
    def _json_dumps(obj: dict) -> str:
        """JSON dumps with datetime serialization support."""
        def _default(o):
            if isinstance(o, datetime):
                return o.isoformat()
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
        return json.dumps(obj, ensure_ascii=False, indent=2, default=_default)

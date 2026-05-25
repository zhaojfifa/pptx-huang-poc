"""
Content generator: generates PPT outline and per-page markdown content using LLM.
Strictly template-slot-aware: every module count, title length, and bullet count
is constrained by the actual text-box capacities extracted from the template.
"""

import json
import logging
import re
from pathlib import Path

from skills.skill_llm.llm_skill import LLMSkill

logger = logging.getLogger(__name__)


def _safe_text(value) -> str:
    """Coerce an LLM-supplied JSON field into a plain string.

    LLMs occasionally return a list/dict/None where a string is expected
    (e.g. ``title`` or ``key_points`` entries). Calling ``.lower()`` /
    ``.strip()`` on those raises ``AttributeError``. This normalizes them
    before any string operation or matching.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_safe_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(_safe_text(v) for v in value.values())
    return str(value)


class ContentGenerator:
    def __init__(self):
        self.llm = LLMSkill()
        self._doc_summary_cache = {}

    def summarize_document(self, document_markdown: str, job_id: int = None) -> str:
        """Generate a comprehensive summary of the document. Return original if short enough."""
        if not document_markdown:
            return ""

        cache_key = job_id if job_id is not None else hash(document_markdown[:2000])
        if cache_key in self._doc_summary_cache:
            return self._doc_summary_cache[cache_key]

        # Short document: no need to summarize
        if len(document_markdown) <= 10000:
            self._doc_summary_cache[cache_key] = document_markdown
            return document_markdown

        system = "You are a professional document analyst. Summarize the given document comprehensively in Chinese. Preserve all key arguments, data points, conclusions, and section hierarchy. Output plain text only."

        # For very long documents, take first 60% and last 40% of paragraphs to fit context
        paragraphs = document_markdown.split("\n\n")
        if len(paragraphs) > 30:
            n = len(paragraphs)
            selected_paras = paragraphs[:max(3, n // 3)] + ["\n...[文档中间部分省略]...\n"] + paragraphs[-max(3, n // 3):]
            doc_for_prompt = "\n\n".join(selected_paras)
        else:
            doc_for_prompt = document_markdown

        prompt = f"""请对以下文档进行全面摘要。要求：
1. 保留文档的完整结构（章节、层级关系）
2. 保留所有关键论点、重要数据、核心结论
3. 不要遗漏任何对制作PPT有用的信息
4. 摘要控制在6000个中文字以内
5. 直接输出摘要文本，不要添加额外说明

文档内容：
```
{doc_for_prompt}
```

请输出结构化摘要："""
        try:
            summary = self.llm.chat(prompt, system=system, enable_thinking=False)
            self._doc_summary_cache[cache_key] = summary
            logger.info(f"Document summarized from {len(document_markdown)} to {len(summary)} chars.")
            return summary
        except Exception as e:
            logger.error(f"Document summarization failed: {e}. Falling back to smart truncation.")
            # Smart fallback: beginning + end (most important parts)
            fallback = document_markdown[:5000] + "\n\n...[中间部分省略]...\n\n" + document_markdown[-3000:]
            self._doc_summary_cache[cache_key] = fallback
            return fallback

    def _summarize_relevant_doc(self, relevant_doc: str, slide_outline: dict) -> str:
        """Summarize extracted relevant doc if it's too long."""
        if not relevant_doc or len(relevant_doc) <= 3000:
            return relevant_doc

        title = slide_outline.get("title", "")
        key_points = slide_outline.get("key_points", [])
        context = f"主题: {title}"
        if key_points:
            context += f"，要点: {'; '.join(str(k) for k in key_points[:3])}"

        system = "You are a content extraction specialist. Extract and summarize content relevant to a specific topic from a document. Output plain text only."
        prompt = f"""以下是从文档中提取的与"{title}"相关的原始段落，内容可能较长且有些冗余。

请针对该主题，对这些内容进行精炼和重组：
1. 保留所有关键信息、数据、论点
2. 去除重复和冗余内容
3. 按逻辑顺序组织
4. 控制在2500个中文字以内
5. 直接输出结果，不要添加额外说明

原始段落：
```
{relevant_doc}
```

请输出精炼后的内容："""
        try:
            summary = self.llm.chat(prompt, system=system, enable_thinking=False)
            logger.info(f"Relevant doc summarized from {len(relevant_doc)} to {len(summary)} chars for slide '{title}'.")
            return summary
        except Exception as e:
            logger.error(f"Relevant doc summarization failed: {e}. Returning original.")
            return relevant_doc

    def _save_prompt(self, job_id: int, phase: str, prompt: str):
        """Save LLM prompt to job checkpoint directory for inspection."""
        if job_id is None:
            return
        from config.settings import LOGS_DIR
        prompt_dir = Path(LOGS_DIR) / f"job_{job_id}"
        prompt_dir.mkdir(parents=True, exist_ok=True)
        filepath = prompt_dir / f"llm_prompt_{phase}.txt"
        filepath.write_text(prompt, encoding="utf-8")
        logger.info(f"Job {job_id}: LLM prompt saved to {filepath}")

    def _save_llm_output(self, job_id: int, phase: str, output):
        """Save LLM structured response output to job checkpoint directory for inspection."""
        if job_id is None:
            return
        from config.settings import LOGS_DIR
        import json
        out_dir = Path(LOGS_DIR) / f"job_{job_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        filepath = out_dir / f"llm_output_{phase}.json"
        try:
            if isinstance(output, dict):
                text = json.dumps(output, ensure_ascii=False, indent=2)
            else:
                text = str(output)
            filepath.write_text(text, encoding="utf-8")
            logger.info(f"Job {job_id}: LLM output saved to {filepath}")
        except Exception as e:
            logger.warning(f"Job {job_id}: Failed to save LLM output for phase '{phase}': {e}")

    def generate_outline(
        self,
        user_requirements: str,
        document_markdown: str,
        template_info: dict,
        template_pages: list,
        job_id: int = None,
    ) -> dict:
        system = "You are a PPT content strategist. Create a detailed PPT outline. Output JSON only."

        template_style = template_info.get("overall_style", {}) if isinstance(template_info, dict) else {}
        page_count_hint = len(template_pages) if template_pages else 8

        # Build per-page slot specifications for ALL template pages
        from core.template_style_engine import TemplateStyleEngine
        page_specs = []
        for i, tp in enumerate(template_pages):
            engine = TemplateStyleEngine(tp)
            bp = engine.blueprint
            slots = bp["slots"]
            content_slots = slots.get("content", [])
            labels = slots.get("labels", [])
            capacities = [s.get("_capacity", {}).get("total_chars", 160) for s in content_slots]
            avg_cap = int(sum(capacities) / len(capacities)) if capacities else 160
            label_capacities = [s.get("_capacity", {}).get("total_chars", 20) for s in labels]
            avg_label_cap = int(sum(label_capacities) / len(label_capacities)) if label_capacities else 20

            tables = slots.get("tables", [])
            spec_lines = [f"Template Page {i+1} layout:"]
            if slots.get("title"):
                spec_lines.append("  - 1 title slot (slide heading)")
            if slots.get("subtitle"):
                spec_lines.append("  - 1 subtitle/desc slot (short paragraph)")
            if tables:
                for tbl in tables:
                    t = tbl.get("table", {})
                    spec_lines.append(f"  - 1 TABLE: {t.get('rows', 0)} rows x {t.get('cols', 0)} cols")
                    headers = t.get("headers", [])
                    if headers:
                        spec_lines.append(f"    Table headers: {headers}")
            spec_lines.append(f"  - {len(content_slots)} content text slot(s), avg capacity ~{avg_cap} chars")
            if capacities and len(capacities) <= 12:
                cap_str = ", ".join(str(c) for c in capacities)
                spec_lines.append(f"    Content slot capacities: [{cap_str}]")
            if labels:
                spec_lines.append(f"  - {len(labels)} label/caption slot(s), avg capacity ~{avg_label_cap} chars")
                if label_capacities and len(label_capacities) <= 12:
                    lcap_str = ", ".join(str(c) for c in label_capacities)
                    spec_lines.append(f"    Label slot capacities: [{lcap_str}]")
            page_specs.append("\n".join(spec_lines))

        page_specs_text = "\n\n".join(page_specs)

        # Summarize document if too long, to preserve comprehensive information
        doc_for_outline = self.summarize_document(document_markdown, job_id=job_id)

        prompt = f"""
Create a PPT outline based on the following inputs.

User requirements:
```
{user_requirements}
```

Source document content:
```
{doc_for_outline}
```

Template style to follow:
- Style: {template_style.get('style_name', 'General')}
- Description: {template_style.get('description', '')}
- Suitable content: {template_style.get('content_suitability', '')}
- Design keywords: {', '.join(template_style.get('design_keywords', []))}
- Target audience: {template_style.get('target_audience', '')}

=== TEMPLATE SLOT SPECIFICATIONS (STRICT) ===
{page_specs_text}

CRITICAL RULES:
1. The template has EXACTLY {page_count_hint} pages. You MUST generate EXACTLY {page_count_hint} slides.
2. Each slide MUST strictly correspond to its template page in order: slide 1 uses template page 1, slide 2 uses template page 2, etc.
   - NEVER suggest reusing earlier template pages (e.g., "复用Page 3" is FORBIDDEN).
   - Each slide's layout and slot count must match its corresponding template page.
3. Each slide MUST have exactly the same number of key_points as the template page has CONTENT slots.
   - Example: if template page 4 has 4 content slots, slide 4 MUST have exactly 4 key_points.
   - Example: if template page 6 has 16 content slots, slide 6 MUST have exactly 16 key_points.
4. Each key_point must be a concise summary (under 20 Chinese chars or 30 English chars).
   - For small-capacity slots (under 30 chars), the key_point should be a very short tag/keyword (2-6 chars).
   - For large-capacity slots (over 80 chars), the key_point can be a slightly longer descriptive phrase.
5. The outline is a plan only — detailed text will be expanded later per slot capacity.
6. Label/caption slots are small text boxes in diagrams/charts. Their specific text will be generated later, but you should be aware of their existence and quantity when planning the slide structure.
7. Do NOT generate more or fewer key_points than the template page has content slots.

=== AGENDA STRUCTURE (REQUIRED — top-down 总分关系) ===
8. Produce a top-level "agenda" array of 3–6 sections that is the 总纲 of the whole deck.
   Each section = {{"section_id": "A"/"B"/"C"...", "section_title": "<并列、业务化的章节名, 6-14字>"}}.
   - Section titles MUST be parallel in wording and business-meaningful (e.g.
     「经营质效与财务表现」「产能效率与智能制造」「风险挑战与应对」「下一步战略重点」).
   - FORBIDDEN: metric cards as sections (e.g. 「营收3,612亿」), vague single buckets
     (e.g. only 「六大板块」), conclusions, or random page summaries.
   - Sections must collectively cover the body slides; each section covers ≥1 body slide.
9. The agenda/目录 slide (the section/agenda-type page, usually slide 2) MUST display these
   sections: set its key_points to the section_titles (a real table of contents), NOT KPIs
   or metrics.
10. Every body slide (NOT cover/title, NOT the agenda slide, NOT ending) MUST be bound to one
    agenda section and include:
    - "section_id": the owning section's id
    - "section_title": the owning section's title (copied verbatim)
    - "slide_role_under_section": one sentence on how this page supports that section.
    A slide's topic MUST stay within its section — do not introduce unrelated themes.

Return JSON:
{{
    "title": "<presentation title>",
    "agenda": [
        {{"section_id": "A", "section_title": "<并列业务化章节名>"}}
    ],
    "slides": [
        {{
            "slide_number": 1,
            "template_page_number": 1,
            "type": "<title|content|section|chart|ending>",
            "title": "<slide title, under 15 Chinese chars>",
            "key_points": ["<point 1>", "<point 2>"],
            "section_id": "<A/B/C... ; omit for cover/agenda/ending>",
            "section_title": "<owning section title ; omit for cover/agenda/ending>",
            "slide_role_under_section": "<how this page supports the section ; omit for cover/agenda/ending>",
            "notes": "<which template page this slide maps to and why>"
        }}
    ]
}}
"""
        self._save_prompt(job_id, "outline", prompt)
        logger.info("Generating outline with LLM...")
        outline = self.llm.chat_structured(prompt, system=system, enable_thinking=False)
        self._save_llm_output(job_id, "outline", outline)
        logger.info(f"Outline generated with {len(outline.get('slides', []))} slides.")
        return outline

    def generate_slide_content(
        self,
        slide_outline: dict,
        document_markdown: str,
        template_page: dict,
        job_id: int = None,
        pptx_path: str = None,
    ) -> dict:
        """Generate detailed markdown content for a single slide.
        
        Uses JSON modules array for reliable slot-to-module mapping.
        Each array element maps 1:1 to a template content slot.
        """
        system = "You are a PPT content writer. Generate slide content as a JSON array of modules. Output JSON only."

        from core.template_style_engine import TemplateStyleEngine
        engine = TemplateStyleEngine(template_page, pptx_path)
        bp = engine.blueprint
        slots = bp["slots"]
        rows = slots.get("_rows", [])
        row_order = slots.get("_row_order", slots.get("content", []))
        total_slots = len(row_order)

        # Page-type prompt router: pick per-type guidance from outline hint + slots
        from core import page_type_prompt as ptp
        _ptype = ptp.classify(
            slide_index=slide_outline.get("slide_number", 1),
            total_pages=slide_outline.get("_total_pages", slide_outline.get("slide_number", 1)),
            outline_type=slide_outline.get("type"),
            slots=ptp.slot_summary(bp),
        )
        _tkey = slide_outline.get("_template_key")
        page_type_block = f"=== 页面类型指引 ===\n{ptp.content_guidance(_ptype, _tkey)}"

        # Agenda-to-slides consistency injection (top-down): keep this slide as a supporting
        # detail under its assigned agenda section; do not drift to unrelated themes.
        _agenda_section = _safe_text(slide_outline.get("_agenda_section")
                                     or slide_outline.get("section_title") or "").strip()
        _slide_role = _safe_text(slide_outline.get("slide_role_under_section") or "").strip()
        if _agenda_section and _ptype not in ("cover", "agenda", "closing"):
            page_type_block += (
                f"\n=== 目录归属（必须遵守）===\n"
                f"本页隶属目录章节：「{_agenda_section}」。"
            )
            if _slide_role:
                page_type_block += f"本页在该章节中的作用：{_slide_role}。"
            page_type_block += (
                "请将本页内容作为该章节的分论展开/支撑细节来生成，"
                "紧扣该章节主题，禁止引入与该章节无关的其它主题。"
            )

        # Build row-aware slot specifications
        slot_specs = []
        for row_idx, row in enumerate(rows):
            slot_specs.append(f"\n第{row_idx + 1}行 ({len(row)}个文本区域):")
            for slot_idx, slot in enumerate(row):
                global_idx = sum(len(r) for r in rows[:row_idx]) + slot_idx + 1
                cap = slot.get("_capacity", {})
                total = cap.get("total_chars", 40)
                lines = cap.get("max_lines", 1)
                cpl = slot.get("_text_len") or cap.get("chars_per_line", 20)
                w = slot.get("width", 0)
                h = slot.get("height", 0)
                if total > 40 and lines >= 2:
                    role = "主内容"
                    bullet_hint = f", 建议{max(1, lines - 1)}个bullet"
                elif w > h * 2:
                    role = "横向标签/说明"
                    bullet_hint = ", 只写简短标题"
                else:
                    role = "标签/提炼"
                    bullet_hint = ", 只写简短标题"
                slot_specs.append(
                    f"  {global_idx}. [{role}] 容量{total}字符/{lines}行"
                    f"(共约~{cpl}字){bullet_hint}"
                )

        slot_specs_text = "\n".join(slot_specs) if slot_specs else "  未检测到文本区域。"

        # Check if template has a subtitle slot
        subtitle_slot = slots.get("subtitle")
        subtitle_instruction = ""
        subtitle_json_field = ""
        if subtitle_slot:
            cap = subtitle_slot.get("_capacity", {})
            sub_lines = cap.get("max_lines", 2)
            sub_chars = cap.get("total_chars", 120)
            subtitle_instruction = (
                f"\n7. 此模板还包含一个副标题/描述文本框（约{sub_lines}行，{sub_chars}字以内）。"
                f"请同时生成一句副标题，概括幻灯片核心观点。"
            )
            subtitle_json_field = ',\n    "subtitle": "<slide subtitle, max 30 Chinese chars>"'

        # Extract relevant document excerpts
        relevant_doc = self._extract_relevant_doc(document_markdown, slide_outline)
        relevant_doc = self._summarize_relevant_doc(relevant_doc, slide_outline)
        doc_summary = self.summarize_document(document_markdown, job_id=job_id)
        logger.info(
            f"Slide {slide_outline.get('slide_number')} source context — "
            f"doc_present={bool(document_markdown)} "
            f"relevant_chars={len(relevant_doc)} summary_chars={len(doc_summary)}"
        )

        # Load generation hints from template page if available
        generation_hints = template_page.get("generation_hints") if isinstance(template_page, dict) else None
        if generation_hints:
            layout_description = generation_hints.get("layout_description", "")
            content_relevance = generation_hints.get("content_relevance", "")
            capacity_constraints = generation_hints.get("capacity_constraints", "")
            module_title_rule = generation_hints.get("module_title_rule", "")
        else:
            layout_description = ""
            content_relevance = ""
            capacity_constraints = ""
            module_title_rule = ""

        # Fallback defaults if any hint is empty
        if not layout_description:
            layout_description = (
                "模板将文本区域按视觉行组织。每个文本区域必须生成一个独立的内容条目，禁止合并。\n"
                "  - 主内容区域（2行+）: 需要标题 + bullet，详细论述\n"
                "  - 标签/说明区域（1行）: 只需要简短标题，不要bullet"
            )
        if not content_relevance:
            content_relevance = (
                "同一行内的条目应围绕同一主题或概念，各有侧重。\n"
                "不同行之间可以有递进、并列或分类关系。"
            )
        if not capacity_constraints:
            capacity_constraints = (
                "主内容区域（2行+）: 标题 + 1-2个bullet，总字数不超过容量。\n"
                "标签/说明区域（1行）: 只写简短标题，不要bullet，字数严格控制在容量内。"
            )
        if not module_title_rule:
            module_title_rule = "每个模块标题: 15个中文字以内。"

        # Build dynamic modules example based on actual layout
        modules_example = self._build_modules_example(rows)

        # Check for tables
        tables = slots.get("tables", [])
        table_instruction = ""
        table_json_field = ""
        table_constraint = ""
        table_column_constraints = ""
        if tables:
            tbl = tables[0]
            t = tbl.get("table", {})
            headers = t.get("headers", [])
            columns = t.get("columns", [])
            
            # Build per-column capacity constraints based on template data
            col_constraints = []
            emu_per_inch = 914400
            for col in columns:
                col_width_inch = col.get("width", 0) / emu_per_inch
                font_size = col.get("font_size") or 14
                max_len = col.get("max_text_len", 20)
                header = col.get("header", f"列{col['index']+1}")
                # Estimate chars per line based on font size and column width
                # Chinese char width ≈ font_size pt ≈ font_size/72 inch
                char_width_inch = font_size / 72
                padding_inch = 0.12
                est_chars_per_line = max(3, int((col_width_inch - padding_inch) / char_width_inch))
                col_constraints.append(
                    f'  - 第{col["index"]+1}列 "{header}"：'
                    f'宽度{col_width_inch:.2f}英寸，字体{font_size}pt，'
                    f'估计单行约{est_chars_per_line}字，'
                    f'模板中最长文本{max_len}字（建议不超过{max_len}字，可换行但总长度参照模板）'
                )
            
            table_instruction = (
                f"\n此幻灯片页面包含一个表格（{t.get('rows', 0)}行 x {t.get('cols', 0)}列）。"
                f"表格表头为: {headers}。"
                f"你需要在返回的JSON中额外提供一个 'table_data' 字段，包含表格的 headers 和 rows 数据。"
                f"表格数据必须紧扣幻灯片主题，信息密集、专业、数据驱动。"
            )
            if col_constraints:
                table_column_constraints = (
                    "\n表格列容量约束（基于模板实际排版，请严格参照）：\n"
                    + "\n".join(col_constraints)
                    + "\n每单元格文本允许换行，但总字符数建议不超过模板中最长文本的参考值。"
                )
            table_json_field = ',\n    "table_data": {"headers": [...], "rows": [[...], ...]}'
            table_constraint = (
                "7. 此页面包含表格，必须在JSON中返回 'table_data' 字段。"
                "表格行数可以与模板不一致（可以更多或更少），但列数应与表头一致。"
                "表格每列的文本长度请严格参照上述'列容量约束'，超过参考值的内容会被截断。"
            )

        # Adjust prompt for table-only slides (no text content slots)
        if total_slots == 0 and tables:
            modules_instruction = (
                "1. 此页面没有普通文本区域，只有表格。你不需要输出 modules 数组"
                "（modules 可设为空数组 []）。"
            )
            modules_example_str = '"modules": []'
            modules_return_str = '"modules": []'
        else:
            modules_instruction = (
                f"1. 数组长度是最高优先级。你必须输出一个 modules 数组，数组长度必须 EXACTLY 等于 {total_slots}。\n"
                f"   - modules[0] 对应区域1，modules[1] 对应区域2，...，modules[{total_slots-1}] 对应区域{total_slots}\n"
                "   - 禁止把多个区域的内容合并到一个数组元素中\n"
                f"   - 禁止生成超过 {total_slots} 个数组元素\n"
                f"   - 禁止生成少于 {total_slots} 个数组元素"
            )
            modules_example_str = '"modules": [\n        {"title": "模块1标题", "bullets": ["要点1", "要点2"]},\n        {"title": "标签2", "bullets": []},\n        ...\n    ]'
            modules_return_str = '"modules": [\n        {"title": "...", "bullets": []},\n        ...\n    ]'

        prompt = f"""
为PPT幻灯片生成详细内容。

幻灯片大纲:
```json
{json.dumps(slide_outline, ensure_ascii=False, indent=2)}
```

相关文档摘录（与当前幻灯片主题直接相关）:
```
{relevant_doc}
```

文档全局背景（供参考）:
```
{doc_summary}
```

{page_type_block}

=== 模板布局约束 ===
此幻灯片使用具有以下文本区域的模板页：
{slot_specs_text}
{table_instruction}
{table_column_constraints}

总共需要生成内容的文本区域数: {total_slots}

布局说明:
{layout_description}

严格要求:
{modules_instruction}
2. 每个 module 包含 title（标题）和 bullets（bullet 列表）:
   - 主内容区域（2行及以上，容量>40）: bullets 放 1-2 个要点，每个要点信息密集、具体
   - 横向标签/说明区域（容量<=40，1行）: bullets 必须设为空数组 []，title 严格控制在15字以内，绝对禁止换行
3. 内容相关性:
   {content_relevance}
4. 容量约束:
   {capacity_constraints}
5. {module_title_rule}
6. bullet要信息密集、专业、数据驱动，与幻灯片主题直接相关。{subtitle_instruction}
{table_constraint}

正确格式示例:
```json
{{
    "slide_number": 1,
    "title": "示例标题",
    "subtitle": "示例副标题",
    {modules_example_str}{table_json_field}
}}
```

返回JSON:
{{
    "slide_number": <int>,
    "title": "<slide title, max 15 Chinese chars>"{subtitle_json_field},
    {modules_return_str}{table_json_field}
}}
"""
        self._save_prompt(job_id, f"slide_{slide_outline.get('slide_number', 1)}", prompt)
        logger.info(
            f"Generating content for slide {slide_outline.get('slide_number')} "
            f"with {total_slots} total slots in {len(rows)} row(s)..."
        )
        result = self.llm.chat_structured(prompt, system=system, enable_thinking=False)
        self._save_llm_output(job_id, f"slide_{slide_outline.get('slide_number', 1)}", result)

        # Ensure main content areas have bullets (LLM sometimes omits them)
        result = self._ensure_main_content_bullets(result, rows, slide_outline)

        # Normalize modules: validate count, fix if needed, convert to markdown
        result = self._normalize_modules(
            result, total_slots, system, job_id, slide_outline, has_table=bool(tables)
        )

        # Generate label mappings separately (avoids array-order mismatch disaster)
        labels = slots.get("labels", [])
        if labels:
            label_mappings = self._generate_label_mappings(
                labels, slide_outline, document_markdown, job_id=job_id
            )
            result["labels_content"] = label_mappings

        return result

    def _ensure_main_content_bullets(
        self,
        result: dict,
        rows: list,
        slide_outline: dict = None,
    ) -> dict:
        """Post-process LLM output: ensure main content slots have bullets.
        
        LLMs sometimes return empty bullets for main content areas (capacity>80,
        lines>=3). When this happens, we distribute key_points from the outline
        as fallback bullets so the slide doesn't end up with single-line titles only.
        """
        modules = result.get("modules", [])
        if not modules or not rows:
            return result
        
        key_points = slide_outline.get("key_points", []) if slide_outline else []
        if not key_points:
            return result
        
        # Collect content slots that have empty bullets (relaxed threshold to catch more slots)
        empty_main = []
        slot_idx = 0
        for row in rows:
            for slot in row:
                cap = slot.get("_capacity", {})
                total = cap.get("total_chars", 40)
                lines = cap.get("max_lines", 1)
                # Relaxed: catch any slot with 2+ lines and reasonable capacity
                if total > 40 and lines >= 2:
                    if slot_idx < len(modules):
                        mod = modules[slot_idx]
                        bullets = mod.get("bullets", []) if isinstance(mod, dict) else []
                        if not bullets:
                            empty_main.append((slot_idx, cap, slot))
                slot_idx += 1
        
        if not empty_main:
            return result
        
        # Distribute key_points evenly across empty main content slots
        per_slot = max(2, len(key_points) // len(empty_main))
        for i, (idx, cap, slot) in enumerate(empty_main):
            start = i * per_slot
            end = min(start + per_slot, len(key_points))
            cpl = slot.get("_text_len") or cap.get("chars_per_line", 15)
            assigned = []
            for kp in key_points[start:end]:
                if isinstance(kp, str):
                    # Truncate to fit one line
                    if len(kp) > cpl:
                        kp = kp[:cpl - 1] + "…"
                    assigned.append(kp)
            if assigned:
                modules[idx]["bullets"] = assigned
                logger.info(
                    f"Filled empty bullets for module {idx} with {len(assigned)} key_points"
                )
        
        return result

    def _normalize_modules(
        self,
        result: dict,
        expected_count: int,
        system: str,
        job_id: int = None,
        slide_outline: dict = None,
        max_retries: int = 1,
        has_table: bool = False,
    ) -> dict:
        """Validate modules array length, fix by truncation/padding, and convert to markdown."""
        modules = result.get("modules", [])
        # Preserve table_data from original response across corrections
        original_table_data = result.get("table_data")

        for attempt in range(max_retries + 1):
            if len(modules) == expected_count:
                break

            if attempt >= max_retries:
                logger.warning(
                    f"Module count mismatch after {max_retries} retries: "
                    f"got {len(modules)}, expected {expected_count}. Forcing fix."
                )
                break

            logger.warning(
                f"Module count mismatch (attempt {attempt + 1}): "
                f"got {len(modules)}, expected {expected_count}. Requesting correction..."
            )

            title_escaped = result.get('title', '').replace('"', '\\"')
            subtitle_escaped = result.get('subtitle', '').replace('"', '\\"')
            subtitle_field = f',\n    "subtitle": "{subtitle_escaped}"' if subtitle_escaped else ""
            table_field = ""
            if has_table:
                table_field = ',\n    "table_data": {"headers": [...], "rows": [[...], ...]}'
            correction_prompt = f"""
Your previous response did NOT follow the module count requirement.

Requirement: output EXACTLY {expected_count} modules in the "modules" array.
Your previous response contained {len(modules)} module(s).

Please return a corrected JSON with EXACTLY {expected_count} modules. Each module must have a "title" string and a "bullets" array.

Previous modules (first 5 shown): {json.dumps(modules[:5], ensure_ascii=False)}

Return corrected JSON:
{{
    "slide_number": {result.get('slide_number', 1)},
    "title": "{title_escaped}"{subtitle_field},
    "modules": [exactly {expected_count} elements with "title" and "bullets"]{table_field}
}}
"""
            slide_num = slide_outline.get('slide_number', 1) if slide_outline else 1
            self._save_prompt(job_id, f"slide_{slide_num}_correction_{attempt + 1}", correction_prompt)
            try:
                result = self.llm.chat_structured(correction_prompt, system=system, enable_thinking=False)
                self._save_llm_output(job_id, f"slide_{slide_num}_correction_{attempt + 1}", result)
                modules = result.get("modules", [])
            except Exception as e:
                logger.error(f"Correction attempt {attempt + 1} failed: {e}")
                break

        # Force-fix: truncate or pad modules to exact count
        if len(modules) > expected_count:
            modules = modules[:expected_count]
        elif len(modules) < expected_count:
            last = modules[-1] if modules else {"title": "", "bullets": []}
            while len(modules) < expected_count:
                modules.append({"title": last.get("title", ""), "bullets": []})

        # Convert modules array to markdown_content
        md_parts = []
        for mod in modules:
            title = mod.get("title", "") if isinstance(mod, dict) else ""
            if not title or not isinstance(title, str):
                title = " "
            md_parts.append(f"### {title}")
            bullets = mod.get("bullets", []) if isinstance(mod, dict) else []
            for b in bullets:
                if isinstance(b, str):
                    md_parts.append(f"- {b}")

        result["markdown_content"] = "\n".join(md_parts)
        # Preserve table_data if present (for slides with tables)
        # Prefer original table_data if correction response shrank columns
        corrected_td = result.get("table_data")
        if corrected_td and original_table_data:
            orig_cols = len(original_table_data.get("headers", []))
            corr_cols = len(corrected_td.get("headers", []))
            table_data = original_table_data if corr_cols < orig_cols else corrected_td
        else:
            table_data = corrected_td or original_table_data
        if table_data:
            result["_table_data"] = table_data
        # Clean up: remove modules from result to keep downstream compatibility
        if "modules" in result:
            del result["modules"]
        if "table_data" in result:
            del result["table_data"]

        logger.info(f"Modules normalized: {len(modules)} == {expected_count}")
        return result

    @staticmethod
    def _build_modules_example(rows: list) -> str:
        """Build a JSON modules example based on actual rows."""
        modules = []
        for row in rows:
            for slot in row:
                cap = slot.get("_capacity", {})
                total = cap.get("total_chars", 40)
                lines = cap.get("max_lines", 1)
                if total > 80 and lines >= 2:
                    bullets = ["要点示例一"]
                    if lines >= 3:
                        bullets.append("要点示例二")
                else:
                    bullets = []
                modules.append({"title": f"模块{len(modules)+1}标题", "bullets": bullets})

        if len(modules) > 8:
            display = modules[:3] + [{"title": "...(中间省略，每个区域一个独立模块)...", "bullets": []}] + modules[-2:]
        else:
            display = modules

        return json.dumps(display, ensure_ascii=False, indent=2)

    def _generate_label_mappings(
        self,
        labels: list,
        slide_outline: dict,
        document_markdown: str,
        job_id: int = None,
    ) -> list:
        """Generate label replacements via dictionary mapping instead of flat array.
        
        This avoids the catastrophic index-order mismatch that happens when LLMs
        generate long flat arrays of labels.
        """
        if not labels:
            return []

        # Collect unique original texts and their indices
        orig_to_indices = {}
        for i, lbl in enumerate(labels):
            orig = lbl.get("_text", "").strip()
            if not orig:
                continue
            if orig not in orig_to_indices:
                orig_to_indices[orig] = []
            orig_to_indices[orig].append(i)

        if not orig_to_indices:
            return [""] * len(labels)

        # Hard-rule: pure numeric labels are ALWAYS preserved (never sent to LLM)
        numeric_pattern = re.compile(r'^\d+[\.、\)\]\.]?$')
        preserved = {}  # orig -> preserved text
        llm_labels = []
        for orig in orig_to_indices.keys():
            if orig.isdigit() or numeric_pattern.match(orig):
                preserved[orig] = orig
            else:
                llm_labels.append(orig)

        mapping = {}
        # Pre-fill preserved numeric labels
        mapping.update(preserved)

        # Only send non-numeric labels to LLM
        if llm_labels:
            batch_size = 20
            slide_title = slide_outline.get("title", "")
            doc_summary = self.summarize_document(document_markdown, job_id=job_id)

            system = "You are a PPT terminology specialist. Replace template labels with theme-appropriate equivalents. Output JSON only."

            for start in range(0, len(llm_labels), batch_size):
                batch = llm_labels[start:start + batch_size]
                batch_list = "\n".join([f'  - "{text}"' for text in batch])
                prompt = f"""
请将以下模板标签根据当前幻灯片主题进行语义替换。

当前幻灯片主题: {slide_title}
文档背景摘要:
```
{doc_summary[:1500]}
```

要求:
1. 每个新词必须与主题直接相关，保持专业凝练
2. 字数尽量与原词相同或相近（±2字），确保能填入原位置
3. 原词是数字/编号的（如"1"、"①"），直接保留原词
4. 返回严格JSON映射表: {{"原词1": "新词1", "原词2": "新词2", ...}}
5. 如果某个词无法替换，映射为空字符串""（将保留原词）

原词列表:
{batch_list}

返回JSON映射表:"""
                if job_id is not None:
                    self._save_prompt(job_id, f"slide_{slide_outline.get('slide_number', 1)}_labels_batch_{start//batch_size + 1}", prompt)
                try:
                    result = self.llm.chat_structured(prompt, system=system, enable_thinking=False)
                    self._save_llm_output(job_id, f"slide_{slide_outline.get('slide_number', 1)}_labels_batch_{start//batch_size + 1}", result)
                    if isinstance(result, dict):
                        for k, v in result.items():
                            mapping[k] = v
                except Exception as e:
                    logger.error(f"Label mapping batch {start//batch_size + 1} failed: {e}")
                    # Fallback: keep original texts for this batch
                    for text in batch:
                        mapping[text] = ""

        # Build final labels_content in original order (truncate with +2 char relaxation)
        labels_content = []
        for i, lbl in enumerate(labels):
            orig = lbl.get("_text", "").strip()
            mapped = mapping.get(orig, "") if orig else ""
            if not mapped:
                mapped = orig  # fallback: keep original text
            cap = lbl.get("_capacity", {})
            max_chars = cap.get("total_chars", 20) + 2
            if len(mapped) > max_chars:
                mapped = mapped[:max_chars - 1] + "…"
            labels_content.append(mapped)

        logger.info(f"Label mappings generated: {len(labels)} labels, {len([l for l in labels_content if l])} mapped")
        return labels_content

    @staticmethod
    def _extract_relevant_doc(document_markdown: str, slide_outline: dict) -> str:
        """Extract document excerpts most relevant to the slide topic.
        
        Expands keyword matching range and preserves original document order
        to maintain coherent context.
        """
        if not document_markdown:
            return ""
        title = _safe_text(slide_outline.get("title", ""))
        key_points = slide_outline.get("key_points", [])
        if not isinstance(key_points, list):
            key_points = [key_points]
        keywords = [title] + [_safe_text(kp) for kp in key_points]
        lines = document_markdown.split("\n")
        scored = []
        for line in lines:
            score = sum(1 for kw in keywords if kw and kw.lower() in line.lower())
            if score > 0:
                scored.append((score, line))
        scored.sort(key=lambda x: -x[0])
        # Take more top-scoring lines with wider surrounding context
        selected = []
        seen = set()
        for score, line in scored[:30]:
            idx = lines.index(line)
            for j in range(max(0, idx - 2), min(len(lines), idx + 3)):
                if j not in seen:
                    seen.add(j)
                    selected.append((j, lines[j]))
        # Reconstruct in original document order for coherence
        selected.sort(key=lambda x: x[0])
        result = "\n".join([line for _, line in selected])
        return result if result else document_markdown[:2000]

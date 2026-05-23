"""
Content Normalizer: post-processes LLM-generated content to strictly match
template slot capacities and counts. This is a hard enforcement layer —
LLMs are unreliable at following precise character counts, so we truncate/
merge/pad after generation to ensure content always fits the template.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)


def _parse_modules(markdown: str) -> List[dict]:
    """Extract content modules from markdown."""
    modules = []
    if not markdown:
        return modules
    pattern = r'###\s*([^\n]+)(.*?)(?=###|\Z)'
    for title, content in re.findall(pattern, markdown, re.DOTALL):
        lines = [l.strip() for l in content.split('\n') if l.strip()]
        bullets = []
        for l in lines:
            for marker in ('- ', '* ', '\u2022 ', '\u2013 ', '\u2014 '):
                if l.startswith(marker):
                    bullet_text = l[len(marker):]
                    # Strip any nested bullet markers (e.g., LLM generates "- • text")
                    for inner in ('\u2022 ', '\u00b7 ', '- ', '* '):
                        if bullet_text.startswith(inner):
                            bullet_text = bullet_text[len(inner):]
                    bullets.append(bullet_text)
                    break
        modules.append({'title': title.strip(), 'bullets': bullets})
    return modules


def _rebuild_markdown(modules: List[dict]) -> str:
    """Rebuild markdown from normalized modules."""
    parts = []
    for mod in modules:
        title = mod['title'] if mod['title'] else ""
        if not title:
            continue
        lines = [f"### {title}"]
        for b in mod['bullets']:
            lines.append(f"- {b}")
        parts.append('\n'.join(lines))
    return '\n\n'.join(parts)


def _truncate_text(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, preserving whole words/characters."""
    if len(text) <= max_chars:
        return text
    # Try to cut at last sentence boundary or comma
    trunc = text[:max_chars]
    for delim in ('。', '，', '；', '.', ',', ';', ' '):
        idx = trunc.rfind(delim)
        if idx > max_chars * 0.5:
            return trunc[:idx + 1]
    return trunc[:max_chars - 1] + '…'


class ContentNormalizer:
    """Normalize LLM-generated slide content to fit template slot constraints."""

    def normalize_slide_content(self, slide_data: dict, blueprint: dict) -> dict:
        """
        Adjust markdown_content to precisely match blueprint slot specs.

        Strategy (v2):
        - Every content slot (large and small) gets its own module.
        - Modules are mapped 1:1 to slots in row-ordered visual sequence.
        - Each module is truncated to fit its specific slot capacity.
        """
        markdown = slide_data.get("markdown_content", "")
        modules = _parse_modules(markdown)
        contents = blueprint.get("slots", {}).get("content", [])
        row_order = blueprint.get("slots", {}).get("_row_order", contents)

        if not contents:
            # Still process tables even if there are no text content slots
            tables = blueprint.get("slots", {}).get("tables", [])
            if not tables:
                logger.warning("No content slots in blueprint, returning slide_data unchanged.")
                return slide_data
            logger.info(f"No text content slots, but {len(tables)} table(s) found. Processing tables only.")

        target_count = len(row_order)
        logger.info(
            f"Normalizing slide {slide_data.get('slide_number')}: "
            f"{len(modules)} modules -> {target_count} slots in {len(blueprint.get('slots', {}).get('_rows', []))} row(s)"
        )

        # Step 1: adjust module count to match total slots
        modules = self._adjust_module_count(modules, target_count)

        # Step 2: build slot mappings in row order
        slot_mappings = []
        normalized_modules = []

        for i, slot in enumerate(row_order):
            mod = modules[i]
            cap = slot.get("_capacity", {})
            max_chars = cap.get("total_chars", 40)
            max_lines = cap.get("max_lines", 1)
            chars_per_line = cap.get("chars_per_line", 20)
            orig_text = slot.get("_text", "")

            # Truncate module to fit slot capacity
            normalized_mod = self._truncate_module(mod, max_chars, max_lines, chars_per_line)

            # Detect short tag slots: must be single-line, no bullets, no line breaks
            # Conservative: only force single-line if truly tiny or original text was very short
            is_short_tag = (
                max_lines <= 1
                or (len(orig_text) <= 15 and max_lines <= 4)
                or (max_lines <= 2 and max_chars <= 40 and len(orig_text) <= 20)
            )

            # Check original paragraph count: if template had only 1 paragraph,
            # <20 chars: keep title only; >=20 chars: merge title + bullets
            orig_paras = slot.get("paragraphs", [])
            if len(orig_paras) == 1:
                orig_text_len = len(slot.get("_text", ""))
                if orig_text_len < 20:
                    text = normalized_mod["title"]
                else:
                    text = normalized_mod["title"]
                    if normalized_mod["bullets"]:
                        text += "：" + "；".join(normalized_mod["bullets"])
            elif is_short_tag:
                # Force single-line text: use title only, drop bullets, no newlines
                title = normalized_mod["title"]
                max_title_len = min(chars_per_line, max_chars, max(12, len(orig_text)))
                if len(title) > max_title_len:
                    title = _truncate_text(title, max_title_len)
                text = title
            else:
                # Build text for this slot
                text = normalized_mod["title"]
                for b in normalized_mod["bullets"]:
                    text += "\n• " + b

            slot_mappings.append({
                "shape_name": slot.get("name"),
                "shape_id": slot.get("shape_id"),
                "text": text,
                "capacity": cap,
            })
            normalized_modules.append(normalized_mod)

        # Step 3: normalize table data if present
        table_data = slide_data.get("_table_data")
        tables = blueprint.get("slots", {}).get("tables", [])
        if table_data and tables:
            normalized_tables = []
            for tbl_slot in tables:
                t = tbl_slot.get("table", {})
                target_cols = t.get("cols", 0)
                target_rows = t.get("rows", 0)
                headers = table_data.get("headers", [])
                rows = table_data.get("rows", [])
                
                # Adjust headers to match target column count
                if len(headers) > target_cols:
                    headers = headers[:target_cols]
                elif len(headers) < target_cols:
                    while len(headers) < target_cols:
                        headers.append(f"列{len(headers)+1}")
                
                # Filter out completely empty rows (all cells are empty/whitespace)
                rows = [
                    row for row in rows
                    if any(str(c).strip() for c in (row if isinstance(row, list) else [row]))
                ]
                
                # Cap rows to target count (do NOT pad with blank rows;
                # _fill_table will delete excess template rows if needed)
                data_row_target = max(1, target_rows - 1)
                if len(rows) > data_row_target:
                    rows = rows[:data_row_target]
                
                # Ensure each row has exactly target_cols columns
                normalized_rows = []
                for row in rows:
                    if not isinstance(row, list):
                        row = [str(row)]
                    if len(row) > target_cols:
                        row = row[:target_cols]
                    elif len(row) < target_cols:
                        while len(row) < target_cols:
                            row.append("")
                    normalized_rows.append(row)
                
                # Build per-column capacity info for the cloner
                columns_info = []
                emu_per_inch = 914400
                for c_idx in range(target_cols):
                    col_data = None
                    if c_idx < len(t.get("columns", [])):
                        col_data = t["columns"][c_idx]
                    
                    col_width = col_data.get("width", 0) if col_data else 0
                    font_size = col_data.get("font_size") if col_data else None
                    max_text_len = col_data.get("max_text_len", 20) if col_data else 20
                    
                    col_width_inch = col_width / emu_per_inch if col_width else 1.5
                    fs = font_size or 14
                    char_width_inch = fs / 72
                    padding_inch = 0.12
                    chars_per_line = max(3, int((col_width_inch - padding_inch) / char_width_inch))
                    # Allow some buffer over template max_text_len
                    max_total_chars = max(max_text_len, int(chars_per_line * 1.5))
                    
                    columns_info.append({
                        "index": c_idx,
                        "width": col_width,
                        "font_size": fs,
                        "chars_per_line": chars_per_line,
                        "max_total_chars": max_total_chars,
                        "template_max_len": max_text_len,
                    })
                
                normalized_tables.append({
                    "shape_name": tbl_slot.get("name"),
                    "shape_id": tbl_slot.get("shape_id"),
                    "headers": headers,
                    "rows": normalized_rows,
                    "columns": columns_info,
                })
                logger.info(
                    f"Normalized table for slide {slide_data.get('slide_number')}: "
                    f"{len(headers)} cols x {len(normalized_rows)} data rows"
                )
            slide_data["_table_mappings"] = normalized_tables

        # Step 4: normalize labels if present
        labels_content = slide_data.get("labels_content", [])
        labels = blueprint.get("slots", {}).get("labels", [])
        if labels:
            target_label_count = len(labels)
            if len(labels_content) > target_label_count:
                labels_content = labels_content[:target_label_count]
            elif len(labels_content) < target_label_count:
                while len(labels_content) < target_label_count:
                    labels_content.append("")
            # Label text: truncate with relaxed limit (+2 chars)
            normalized_labels = []
            for i, slot in enumerate(labels):
                text = labels_content[i] if i < len(labels_content) else ""
                cap = slot.get("_capacity", {})
                max_chars = cap.get("total_chars", 20) + 2
                if len(text) > max_chars:
                    text = _truncate_text(text, max_chars)
                normalized_labels.append(text)
            slide_data["labels_content"] = normalized_labels
            logger.info(
                f"Normalized slide {slide_data.get('slide_number')} labels: "
                f"{len(normalized_labels)} labels truncated to capacities"
            )

        # Step 5: rebuild markdown from normalized modules
        normalized_md = _rebuild_markdown(normalized_modules)
        slide_data["markdown_content"] = normalized_md
        slide_data["_slot_mappings"] = slot_mappings
        return slide_data

    def _adjust_module_count(self, modules: List[dict], target_count: int) -> List[dict]:
        """Truncate or pad modules to reach exactly target_count."""
        if len(modules) == target_count:
            return modules

        if len(modules) > target_count:
            logger.warning(f"Truncating modules from {len(modules)} to {target_count}")
            return modules[:target_count]

        # Pad with empty modules
        while len(modules) < target_count:
            modules.append({"title": "", "bullets": []})
        return modules

    def _truncate_module(self, mod: dict, max_chars: int, max_lines: int, chars_per_line: int = 40) -> dict:
        """Truncate a single module so title + bullets fit within max_lines and max_chars.

        Strategy:
        - Title always takes exactly 1 line (conservative).
        - Each bullet's line count is estimated by chars_per_line.
        - Total lines (title + all bullets) must not exceed max_lines.
        - Total chars must not exceed max_chars.
        """
        title = mod["title"]
        bullets = mod["bullets"]

        # Title always gets 1 line; truncate if too long
        if len(title) > chars_per_line:
            title = _truncate_text(title, chars_per_line)

        remaining_lines = max(0, max_lines - 1)
        kept_bullets = []
        total_chars = len(title)

        # Bullets have indentation penalty (~0.75x effective width)
        bullet_cpl = max(8, int(chars_per_line * 0.75))

        for b in bullets:
            if remaining_lines <= 0:
                break
            # Estimate lines this bullet needs (accounting for bullet indent)
            bullet_lines = max(1, (len(b) + bullet_cpl - 1) // bullet_cpl)
            if bullet_lines > remaining_lines:
                # Truncate to fit within remaining lines
                max_bullet_chars = max(10, remaining_lines * bullet_cpl - 2)
                b = _truncate_text(b, max_bullet_chars)
                bullet_lines = remaining_lines
            # Also check total char budget
            if total_chars + len(b) + 3 > max_chars:  # +3 for "\n• "
                remaining = max_chars - total_chars - 3
                if remaining > 5:
                    b = _truncate_text(b, remaining)
                else:
                    break
            kept_bullets.append(b)
            remaining_lines -= bullet_lines
            total_chars += len(b) + 3

        return {"title": title, "bullets": kept_bullets}

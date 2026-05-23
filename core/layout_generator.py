"""
Layout generator: converts LLM layout instructions into structured JSON.
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

SLIDE_WIDTH = 9144000
SLIDE_HEIGHT = 6858000
MARGIN = 457200
GAP = 250000
TITLE_H = 800000
MAX_BULLETS = 2


class LayoutGenerator:
    @staticmethod
    def _parse_modules(markdown_content: str) -> List[dict]:
        modules = []
        if not markdown_content:
            return modules
        pattern = r'###\s*([^\n]+)(.*?)(?=###|\Z)'
        for title, content in re.findall(pattern, markdown_content, re.DOTALL):
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            bullets = []
            for l in lines:
                if l.startswith(('- ', '* ')):
                    bullet_text = l.lstrip('- *')
                    # Strip any nested bullet markers (e.g., LLM generates "- • text")
                    for inner in ('\u2022 ', '\u00b7 ', '- ', '* '):
                        if bullet_text.startswith(inner):
                            bullet_text = bullet_text[len(inner):]
                    bullets.append(bullet_text)
            modules.append({'title': title.strip(), 'bullets': bullets})
        return modules

    def normalize_layout(self, layout_data: dict, slide_number: int) -> dict:
        normalized = {
            "slide_number": slide_number,
            "width": SLIDE_WIDTH, "height": SLIDE_HEIGHT,
            "background_color": layout_data.get("background_color", "#FFFFFF"),
            "shapes": [],
        }
        li = layout_data.get("layout_instructions", {})
        fs = layout_data.get("font_style", {})
        cs = layout_data.get("color_scheme", {})

        # Title
        tp = li.get("title_position", {
            "left": MARGIN, "top": MARGIN,
            "width": SLIDE_WIDTH - MARGIN * 2, "height": TITLE_H,
        })
        normalized["shapes"].append({
            "type": "title", "text": layout_data.get("title", ""),
            "left": tp["left"], "top": tp["top"],
            "width": tp["width"], "height": tp["height"],
            "font": fs.get("title_font", "Arial"),
            "font_size": fs.get("title_size", 32),
            "bold": True, "color": cs.get("text", "#000000"),
        })

        modules = self._parse_modules(layout_data.get("markdown_content", ""))
        has_chart = bool(li.get("chart_mermaid_code"))

        if modules and has_chart and len(modules) >= 3:
            self._module_chart_layout(normalized, modules, li, fs, cs)
        elif modules and len(modules) >= 2:
            self._module_layout(normalized, modules, li, fs, cs)
        else:
            self._simple_layout(normalized, layout_data, li, fs, cs)

        return normalized

    def _module_chart_layout(self, normalized, modules, li, fs, cs):
        """Modules on left (2-col grid), chart on right."""
        # Tighten gap between title and content
        content_top = MARGIN + TITLE_H + GAP // 2
        content_h = SLIDE_HEIGHT - content_top - MARGIN

        chart_w = int(SLIDE_WIDTH * 0.34)
        chart_x = SLIDE_WIDTH - MARGIN - chart_w
        chart_h = min(content_h, int(SLIDE_HEIGHT * 0.60))

        mod_area_w = SLIDE_WIDTH - MARGIN * 2 - chart_w - GAP
        mod_area_x = MARGIN

        mod_cols = 2
        mod_rows = (len(modules) + mod_cols - 1) // mod_cols
        mod_w = (mod_area_w - GAP * (mod_cols - 1)) // mod_cols
        mod_h = (content_h - GAP * (mod_rows - 1)) // mod_rows

        # Ensure min height ~1.1 inch; if too small, fall back to 1 column
        if mod_h < 1000000 and len(modules) >= 4:
            mod_cols = 1
            mod_rows = len(modules)
            mod_w = mod_area_w
            mod_h = (content_h - GAP * (mod_rows - 1)) // mod_rows

        body_font = fs.get("body_font", "Arial")
        body_sz = max(10, min(12, fs.get("body_size", 18) - 6))
        text_c = cs.get("text", "#333333")
        accent = cs.get("accent", "#0078D4")

        for i, mod in enumerate(modules):
            col = i % mod_cols
            row = i // mod_cols
            mx = mod_area_x + col * (mod_w + GAP)
            my = content_top + row * (mod_h + GAP)

            # Limit bullets to prevent overflow
            bullets = mod['bullets'][:MAX_BULLETS]
            icon_sz = min(600000, int(mod_w * 0.22))
            text_w = mod_w - icon_sz - 50000

            # Icon FIRST (goes underneath)
            normalized["shapes"].append({
                "type": "image_placeholder",
                "description": f"图标{i+1}: {mod['title'][:10]}",
                "left": mx + text_w + 30000,
                "top": my + 80000,
                "width": icon_sz,
                "height": icon_sz,
            })

            # Module content box (on top layer)
            mod_text = f"{mod['title']}\n" + "\n".join(f"• {b}" for b in bullets)
            normalized["shapes"].append({
                "type": "content",
                "text": mod_text,
                "left": mx,
                "top": my,
                "width": text_w,
                "height": mod_h,
                "font": body_font,
                "font_size": body_sz,
                "color": text_c,
            })

        # Chart on right
        normalized["shapes"].append({
            "type": "chart",
            "mermaid_code": li.get("chart_mermaid_code", ""),
            "left": chart_x, "top": content_top,
            "width": chart_w, "height": chart_h,
        })

    def _module_layout(self, normalized, modules, li, fs, cs):
        """Modules only, no chart."""
        # Tighten gap between title and content
        content_top = MARGIN + TITLE_H + GAP // 2
        content_h = SLIDE_HEIGHT - content_top - MARGIN

        mod_area_w = SLIDE_WIDTH - MARGIN * 2
        mod_area_x = MARGIN

        mod_cols = 2 if len(modules) >= 4 else 1
        mod_rows = (len(modules) + mod_cols - 1) // mod_cols
        mod_w = (mod_area_w - GAP * (mod_cols - 1)) // mod_cols
        mod_h = (content_h - GAP * (mod_rows - 1)) // mod_rows

        if mod_h < 1000000 and len(modules) >= 4:
            mod_cols = 1
            mod_rows = len(modules)
            mod_w = mod_area_w
            mod_h = (content_h - GAP * (mod_rows - 1)) // mod_rows

        body_font = fs.get("body_font", "Arial")
        body_sz = max(10, min(13, fs.get("body_size", 18) - 5))
        text_c = cs.get("text", "#333333")

        for i, mod in enumerate(modules):
            col = i % mod_cols
            row = i // mod_cols
            mx = mod_area_x + col * (mod_w + GAP)
            my = content_top + row * (mod_h + GAP)

            bullets = mod['bullets'][:MAX_BULLETS]
            icon_sz = min(600000, int(mod_w * 0.18))
            text_w = mod_w - icon_sz - 50000

            # Icon FIRST (underneath)
            normalized["shapes"].append({
                "type": "image_placeholder",
                "description": f"图标{i+1}: {mod['title'][:10]}",
                "left": mx + text_w + 30000,
                "top": my + 80000,
                "width": icon_sz,
                "height": icon_sz,
            })

            mod_text = f"{mod['title']}\n" + "\n".join(f"• {b}" for b in bullets)
            normalized["shapes"].append({
                "type": "content",
                "text": mod_text,
                "left": mx, "top": my,
                "width": text_w, "height": mod_h,
                "font": body_font,
                "font_size": body_sz,
                "color": text_c,
            })

    def _simple_layout(self, normalized, layout_data, li, fs, cs):
        cp = li.get("content_position", {
            "left": MARGIN, "top": 1200000,
            "width": SLIDE_WIDTH - MARGIN * 2, "height": 4500000,
        })
        normalized["shapes"].append({
            "type": "content",
            "text": layout_data.get("markdown_content", ""),
            "left": cp["left"], "top": cp["top"],
            "width": cp["width"], "height": cp["height"],
            "font": fs.get("body_font", "Arial"),
            "font_size": fs.get("body_size", 18),
            "color": cs.get("text", "#333333"),
        })

        img = li.get("image_placeholder")
        if img:
            pos = img.get("position", {
                "left": int(SLIDE_WIDTH * 0.65), "top": 1200000,
                "width": int(SLIDE_WIDTH * 0.30), "height": int(SLIDE_WIDTH * 0.25),
            })
            w = max(pos.get("width", 1800000), 800000)
            h = max(pos.get("height", 1800000), 800000)
            normalized["shapes"].append({
                "type": "image_placeholder",
                "description": img.get("description", ""),
                "left": pos.get("left", int(SLIDE_WIDTH * 0.65)),
                "top": pos.get("top", 1200000),
                "width": w, "height": h,
            })

        if li.get("chart_mermaid_code"):
            chart_p = li.get("chart_position", {
                "left": MARGIN, "top": 1200000,
                "width": SLIDE_WIDTH - MARGIN * 2, "height": 4500000,
            })
            normalized["shapes"].append({
                "type": "chart",
                "mermaid_code": li.get("chart_mermaid_code", ""),
                "left": chart_p["left"], "top": chart_p["top"],
                "width": chart_p["width"], "height": chart_p["height"],
            })

    def generate_all_layouts(self, slides_data: List[Dict[str, Any]]) -> List[dict]:
        return [self.normalize_layout(sd, i + 1) for i, sd in enumerate(slides_data)]

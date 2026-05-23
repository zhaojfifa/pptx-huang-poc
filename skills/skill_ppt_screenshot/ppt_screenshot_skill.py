"""
PPT Screenshot Skill: exports PPTX slides to PNG images.

Two backends are supported, in this priority order:

1. Windows PowerPoint COM (pywin32) — only available on Windows with PPT/WPS installed.
2. LibreOffice headless + pypdfium2 — cross-platform fallback (macOS reproduction path).
   Requires `soffice` on PATH (or /Applications/LibreOffice.app/Contents/MacOS/soffice on
   macOS) and the `pypdfium2` Python package. Converts PPTX → PDF via soffice, then
   rasterizes each PDF page to PNG.

Public interface unchanged: `PPTScreenshotSkill(width, height).export_slides(pptx, out)`
returns a list of PNG paths (slide_1.png .. slide_n.png) in slide order.

NOTE (Huang latest service reproduction, macOS): backend 2 was ported from the main
project's PR-V1 skill (backend/expression/skills/ppt_screenshot_skill.py) so template
visual analysis is reproducible on macOS without Windows COM.
"""

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


_SOFFICE_CANDIDATES = [
    "soffice",
    "libreoffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    "/usr/bin/soffice",
    "/usr/local/bin/soffice",
    "/opt/homebrew/bin/soffice",
]


def _find_soffice() -> Optional[str]:
    for cand in _SOFFICE_CANDIDATES:
        path = shutil.which(cand) if "/" not in cand else (cand if os.path.exists(cand) else None)
        if path:
            return path
    return None


class PPTScreenshotSkill:
    """Export PPTX slides to images via Windows COM (preferred) or LibreOffice+pypdfium2."""

    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height

    def export_slides(self, pptx_path: str, output_dir: str) -> List[str]:
        """Export each slide of a PPTX file to a PNG image.

        Tries Windows PowerPoint COM first; if unavailable, falls back to LibreOffice headless
        PDF export + per-page rasterization. Returns the list of exported PNG paths in slide
        order. Raises RuntimeError if no backend can produce output.
        """
        pptx_path = str(Path(pptx_path).resolve())
        output_dir_p = Path(output_dir).resolve()
        output_dir_p.mkdir(parents=True, exist_ok=True)

        # Backend 1: Windows COM
        if sys.platform.startswith("win") or sys.platform == "cygwin":
            try:
                return self._export_via_powerpoint_com(pptx_path, str(output_dir_p))
            except Exception as exc:
                logger.warning(f"PowerPoint COM export failed, trying LibreOffice fallback: {exc}")

        # Backend 2: LibreOffice + pypdfium2 (cross-platform / macOS)
        soffice = _find_soffice()
        if soffice is None:
            raise RuntimeError(
                "No screenshot backend available. Install LibreOffice (provides `soffice`) "
                "or run on Windows with PowerPoint + pywin32."
            )
        try:
            import pypdfium2  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "pypdfium2 is required for the LibreOffice screenshot backend. "
                "Install: pip install pypdfium2"
            ) from exc

        return self._export_via_libreoffice(pptx_path, str(output_dir_p), soffice)

    def _export_via_powerpoint_com(self, pptx_path: str, output_dir: str) -> List[str]:
        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()
        ppt = None
        presentation = None
        image_paths: List[str] = []
        try:
            ppt = win32com.client.Dispatch("PowerPoint.Application")
            try:
                ppt.Visible = False  # WPS may not support this; ignore.
            except Exception:
                pass
            ppt.DisplayAlerts = False

            logger.info(f"[COM backend] Opening presentation: {pptx_path}")
            presentation = ppt.Presentations.Open(pptx_path)
            slide_count = presentation.Slides.Count
            logger.info(f"[COM backend] Presentation has {slide_count} slides")

            for i in range(1, slide_count + 1):
                slide = presentation.Slides(i)
                output_path = os.path.join(output_dir, f"slide_{i}.png")
                slide.Export(output_path, "PNG", self.width, self.height)
                image_paths.append(output_path)
                logger.info(f"[COM backend] Exported slide {i} to {output_path}")
        finally:
            if presentation:
                try:
                    presentation.Close()
                except Exception:
                    pass
            if ppt:
                try:
                    ppt.Quit()
                except Exception:
                    pass
            pythoncom.CoUninitialize()

        return image_paths

    def _export_via_libreoffice(self, pptx_path: str, output_dir: str, soffice: str) -> List[str]:
        import pypdfium2 as pdfium
        from PIL import Image

        logger.info(f"[LO backend] soffice={soffice} pptx={pptx_path}")

        # soffice writes the PDF next to the source unless --outdir is given, and re-uses
        # (and locks) a user profile dir, so we hand it an isolated one.
        pdf_workdir = Path(output_dir) / "_pdf_workdir"
        pdf_workdir.mkdir(parents=True, exist_ok=True)
        user_profile = Path(output_dir) / "_lo_user_profile"
        user_profile.mkdir(parents=True, exist_ok=True)

        cmd = [
            soffice,
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            f"-env:UserInstallation=file://{user_profile}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(pdf_workdir),
            pptx_path,
        ]
        logger.info(f"[LO backend] running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(
                f"soffice PDF conversion failed (rc={result.returncode}). "
                f"stdout={result.stdout!r} stderr={result.stderr!r}"
            )

        pdf_path = pdf_workdir / (Path(pptx_path).stem + ".pdf")
        if not pdf_path.exists():
            pdfs = list(pdf_workdir.glob("*.pdf"))
            if not pdfs:
                raise RuntimeError(f"soffice produced no PDF in {pdf_workdir}")
            pdf_path = pdfs[0]
        logger.info(f"[LO backend] PDF written: {pdf_path}")

        image_paths: List[str] = []
        pdf = pdfium.PdfDocument(str(pdf_path))
        try:
            slide_count = len(pdf)
            logger.info(f"[LO backend] PDF has {slide_count} pages")
            target_w, target_h = self.width, self.height

            for i, page in enumerate(pdf):
                nat_w, nat_h = page.get_size()
                scale = max(target_w / nat_w, target_h / nat_h)
                img = page.render(scale=scale).to_pil()
                if img.size != (target_w, target_h):
                    img.thumbnail((target_w, target_h), Image.LANCZOS)
                    canvas = Image.new("RGB", (target_w, target_h), "white")
                    x = (target_w - img.width) // 2
                    y = (target_h - img.height) // 2
                    canvas.paste(img, (x, y))
                    img = canvas
                output_path = os.path.join(output_dir, f"slide_{i + 1}.png")
                img.save(output_path, "PNG")
                image_paths.append(output_path)
                logger.info(f"[LO backend] Exported slide {i + 1} to {output_path}")
        finally:
            pdf.close()

        try:
            shutil.rmtree(pdf_workdir, ignore_errors=True)
            shutil.rmtree(user_profile, ignore_errors=True)
        except Exception:
            pass

        return image_paths

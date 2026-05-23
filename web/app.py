"""
FastAPI Web UI for PPTX Agent

Provides interactive endpoints for each pipeline step.
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from fastapi import Body, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import BASE_DIR, OUTPUT_DIR, PREVIEW_DIR
from core.agent import PPTXAgent
from database.db import GenerationJobDAO, TemplateDAO, init_db
from models.schemas import ConfirmRequest, GenerationRequest, RenderRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="PPTX Agent")

# Static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Read index.html directly (Jinja2Templates disabled due to Python 3.14 caching issue)
_INDEX_HTML_PATH = BASE_DIR / "static" / "templates" / "index.html"
_INDEX_HTML = _INDEX_HTML_PATH.read_text(encoding="utf-8") if _INDEX_HTML_PATH.exists() else "<h1>PPTX Agent</h1>"

agent = PPTXAgent()


@app.on_event("startup")
def startup():
    init_db()
    logger.info("Database initialized.")


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(content=_INDEX_HTML)


def _resolve_template(template_id: int | None, template_name: str | None) -> dict | None:
    """POC home selector → DB template. Prefer explicit id; else newest *complete*
    (>=12 pages) template matching the chosen style name; else newest by-name match.
    Returns the template dict or None. Does NOT run any generation step.
    """
    if template_id:
        t = TemplateDAO.get_by_id(template_id)
        if t:
            return t
    if not template_name:
        return None
    matches = [t for t in TemplateDAO.get_all() if t.get("name") == template_name]
    if not matches:
        return None
    from database.db import TemplatePageDAO
    # Prefer the same-name template with the MOST analyzed pages (the complete one),
    # tie-break on newest id. Works for any page count (t5=12, t6=8).
    return max(matches, key=lambda t: (len(TemplatePageDAO.get_by_template(t["id"])), t["id"]))


# A template is usable for real generation once it has a meaningful number of
# analyzed pages (excludes 0/partial rows; admits 8-page and 12-page masters).
_MIN_USABLE_PAGES = 6


@app.post("/api/jobs")
def create_job(
    user_requirements: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    template_name: str = Form(default=None),
    template_key: str = Form(default=None),
    template_id: int = Form(default=None),
    input_mode: str = Form(default="manual"),
):
    saved_files = []
    upload_dir = BASE_DIR / "uploads"
    upload_dir.mkdir(exist_ok=True)

    for f in files:
        if f.filename:
            path = upload_dir / f.filename
            content = f.file.read()
            path.write_bytes(content)
            saved_files.append(str(path))

    job_id = agent.start_job(user_requirements, saved_files)

    # POC: persist the chosen template style so a later (human-triggered) pipeline
    # run maps to selected_template.json → t5.pptx. We do NOT run generation here.
    selected_template = _resolve_template(template_id, template_name)
    template_pages = 0
    if selected_template:
        from database.db import TemplatePageDAO
        GenerationJobDAO.update(job_id, selected_template_id=selected_template["id"])
        template_pages = len(TemplatePageDAO.get_by_template(selected_template["id"]))

    return {
        "job_id": job_id,
        "status": "created",
        "files": saved_files,
        "input_mode": input_mode,
        "template_name": template_name,
        "template_key": template_key,
        "resolved_template": (
            {"id": selected_template["id"], "name": selected_template["name"], "pages": template_pages}
            if selected_template else None
        ),
        "note": (
            "模板已就绪（>=12 页），可由人工触发后续生成步骤。"
            if template_pages >= 12 else
            "已记录所选模板风格；后续生成需人工先完成 t5.pptx 的完整 12 页分析（当前模板为 partial 或未入库）。"
        ),
    }


@app.post("/api/jobs/{job_id}/step/document")
def step_document(job_id: int):
    try:
        md = agent.step_process_documents(job_id)
        return {"job_id": job_id, "step": "document", "status": "ok", "markdown_length": len(md)}
    except Exception as e:
        logger.error(f"Step document failed: {e}")
        return JSONResponse({"job_id": job_id, "step": "document", "status": "error", "error": str(e)}, status_code=500)


@app.post("/api/jobs/{job_id}/step/template")
def step_template(job_id: int):
    try:
        job = GenerationJobDAO.get_by_id(job_id)
        doc_md = ""
        checkpoint_md = BASE_DIR / "logs" / f"job_{job_id}" / "document_markdown.md"
        if checkpoint_md.exists():
            doc_md = checkpoint_md.read_text(encoding="utf-8")
        template = agent.step_select_template(job_id, job["user_requirements"], doc_md)
        return {"job_id": job_id, "step": "template", "status": "ok", "template": template}
    except Exception as e:
        logger.error(f"Step template failed: {e}")
        return JSONResponse({"job_id": job_id, "step": "template", "status": "error", "error": str(e)}, status_code=500)


@app.post("/api/jobs/{job_id}/step/outline")
def step_outline(job_id: int):
    try:
        job = GenerationJobDAO.get_by_id(job_id)
        doc_md = ""
        checkpoint_md = BASE_DIR / "logs" / f"job_{job_id}" / "document_markdown.md"
        if checkpoint_md.exists():
            doc_md = checkpoint_md.read_text(encoding="utf-8")
        template = TemplateDAO.get_by_id(job["selected_template_id"]) if job.get("selected_template_id") else None
        if not template:
            return JSONResponse({"job_id": job_id, "step": "outline", "status": "error", "error": "No template selected"}, status_code=400)
        outline = agent.step_generate_outline(job_id, job["user_requirements"], doc_md, template)
        return {"job_id": job_id, "step": "outline", "status": "ok", "outline": outline}
    except Exception as e:
        logger.error(f"Step outline failed: {e}")
        return JSONResponse({"job_id": job_id, "step": "outline", "status": "error", "error": str(e)}, status_code=500)


@app.post("/api/jobs/{job_id}/step/content")
def step_content(job_id: int):
    try:
        job = GenerationJobDAO.get_by_id(job_id)
        doc_md = ""
        checkpoint_md = BASE_DIR / "logs" / f"job_{job_id}" / "document_markdown.md"
        if checkpoint_md.exists():
            doc_md = checkpoint_md.read_text(encoding="utf-8")
        template = TemplateDAO.get_by_id(job["selected_template_id"]) if job.get("selected_template_id") else None
        outline = job.get("outline_json") or {}
        slides_data = agent.step_generate_content_and_layout(job_id, outline, doc_md, template)
        return {"job_id": job_id, "step": "content", "status": "ok", "slides_count": len(slides_data)}
    except Exception as e:
        logger.error(f"Step content failed: {e}")
        return JSONResponse({"job_id": job_id, "step": "content", "status": "error", "error": str(e)}, status_code=500)


@app.post("/api/jobs/{job_id}/step/layout")
def step_layout(job_id: int):
    try:
        checkpoint = BASE_DIR / "logs" / f"job_{job_id}" / "slides_data.json"
        if not checkpoint.exists():
            return JSONResponse({"job_id": job_id, "step": "layout", "status": "error", "error": "No slides data found"}, status_code=400)
        slides_data = json.loads(checkpoint.read_text(encoding="utf-8"))
        layouts = agent.step_normalize_layouts(job_id, slides_data)
        return {"job_id": job_id, "step": "layout", "status": "ok", "layouts_count": len(layouts)}
    except Exception as e:
        logger.error(f"Step layout failed: {e}")
        return JSONResponse({"job_id": job_id, "step": "layout", "status": "error", "error": str(e)}, status_code=500)


@app.post("/api/jobs/{job_id}/step/render")
def step_render(job_id: int):
    try:
        checkpoint = BASE_DIR / "logs" / f"job_{job_id}" / "layouts.json"
        if not checkpoint.exists():
            return JSONResponse({"job_id": job_id, "step": "render", "status": "error", "error": "No layouts found"}, status_code=400)
        layouts = json.loads(checkpoint.read_text(encoding="utf-8"))
        preview_path = agent.step_render_preview(job_id, layouts)
        return {"job_id": job_id, "step": "render", "status": "ok", "preview_path": preview_path}
    except Exception as e:
        logger.error(f"Step render failed: {e}")
        return JSONResponse({"job_id": job_id, "step": "render", "status": "error", "error": str(e)}, status_code=500)


@app.post("/api/jobs/{job_id}/confirm/outline")
def confirm_outline(req: ConfirmRequest):
    log = {
        "step": "outline_confirmation",
        "time": datetime.now().isoformat(),
        "confirmed": req.confirmed,
        "feedback": req.feedback,
    }
    GenerationJobDAO.append_log(req.job_id, log)
    if req.confirmed:
        GenerationJobDAO.update(req.job_id, status="outline_confirmed")
        return {"job_id": req.job_id, "status": "outline_confirmed"}
    else:
        # Could trigger regeneration with feedback
        return {"job_id": req.job_id, "status": "outline_rejected", "message": "Please provide updated requirements or feedback."}


@app.post("/api/jobs/{job_id}/confirm/render")
def confirm_render(req: RenderRequest):
    log = {
        "step": "render_confirmation",
        "time": datetime.now().isoformat(),
        "confirmed": req.confirmed,
        "feedback": req.feedback,
    }
    GenerationJobDAO.append_log(req.job_id, log)
    if req.confirmed:
        checkpoint = BASE_DIR / "logs" / f"job_{req.job_id}" / "layouts.json"
        layouts = json.loads(checkpoint.read_text(encoding="utf-8"))
        final_path = agent.step_generate_final(req.job_id, layouts)
        return {"job_id": req.job_id, "status": "completed", "final_path": final_path}
    else:
        GenerationJobDAO.update(req.job_id, status="render_rejected")
        return {"job_id": req.job_id, "status": "render_rejected", "message": "Please provide feedback for adjustment."}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    job = GenerationJobDAO.get_by_id(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return job


@app.get("/api/jobs/{job_id}/download/{file_type}")
def download_file(job_id: int, file_type: str):
    job = GenerationJobDAO.get_by_id(job_id)
    if not job:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    path = job.get("rendered_pptx_path") if file_type == "preview" else job.get("final_pptx_path")
    if not path or not Path(path).exists():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(path, filename=Path(path).name)


@app.get("/api/templates")
def list_templates():
    return TemplateDAO.get_all()


# ----------------------------------------------------------------------------
# POC product flow: real outline (Kimi, template-bound) → user edits → confirm →
# real generation pipeline (background). Mock outline only as a fallback when the
# chosen template has no complete (>=12 page) data yet.
# ----------------------------------------------------------------------------
import threading

_EXAMPLE_DOC = BASE_DIR / "logs" / "job_62" / "document_markdown.md"
_AUDIENCE = {"management": "管理层", "client": "客户", "internal": "内部团队", "investor": "投资人"}
_SCENARIO = {"business_review": "经营分析", "project_report": "项目汇报", "solution": "解决方案", "training": "培训材料"}
_TONE = {"professional": "专业", "concise": "简洁", "formal": "正式"}
_LANG = {"zh-CN": "简体中文", "en": "English"}

# in-memory generation status (POC; reference -> state)
_GEN_STATUS: dict[int, dict] = {}


def _source_markdown(input_mode: str, source_name: str) -> str:
    """Resolve the source document text for the chosen input mode."""
    if input_mode == "example" and _EXAMPLE_DOC.exists():
        return _EXAMPLE_DOC.read_text(encoding="utf-8")
    return ""  # manual/text/upload(not wired): outline driven by the prompt only


def _compose_requirements(payload: dict) -> str:
    """Fold the product config into a single natural-language requirements string."""
    p = (payload.get("prompt") or "").strip() or "生成一份企业经营汇报 PPT"
    bits = [p, ""]
    bits.append(f"页数：约 {payload.get('page_count', 12)} 页")
    bits.append(f"受众：{_AUDIENCE.get(payload.get('audience'), '管理层')}")
    bits.append(f"场景：{_SCENARIO.get(payload.get('scenario'), '经营分析')}")
    bits.append(f"语气：{_TONE.get(payload.get('tone'), '专业')}")
    bits.append(f"语言：{_LANG.get(payload.get('language'), '简体中文')}")
    if (payload.get("template_key") or "").lower() == "tech_blue":
        bits.append("风格取向：科技蓝——侧重技术方案/数字化转型/架构与平台能力/数据驱动/智能化，"
                    "标题偏「能力建设·技术路径·应用场景·平台价值」，避免纯财务报表口吻，内容须有资料依据。")
    return "\n".join(bits)


def _outline_to_cards(outline: dict) -> list:
    """Kimi outline {slides:[...]} → editable frontend cards (carry type/page map)."""
    cards = []
    for s in outline.get("slides", []):
        cards.append({
            "page": s.get("slide_number"),
            "template_page_number": s.get("template_page_number", s.get("slide_number")),
            "section": s.get("title_section") or s.get("type") or "",
            "type": s.get("type") or "content",
            "title": s.get("title", ""),
            "points": list(s.get("key_points", []) or []),
        })
    return cards


def _cards_to_slides(cards: list, template_key: str = None) -> dict:
    """Confirmed cards → outline {slides:[...]} consumed verbatim by the pipeline."""
    total = len(cards)
    slides = []
    for i, c in enumerate(cards, start=1):
        slides.append({
            "slide_number": c.get("page", i),
            "template_page_number": c.get("template_page_number", c.get("page", i)),
            "type": c.get("type", "content"),
            "title": c.get("title", ""),
            "key_points": list(c.get("points", []) or []),
            "_total_pages": total,
            "_template_key": template_key,
            "notes": "",
        })
    return {"title": (cards[0].get("title") if cards else "企业经营汇报"), "slides": slides}


def _write_selected_template(job_id: int, template: dict, payload: dict, pages: int):
    """Persist selected_template.json so outline / slide / render reference one source."""
    tid = template["id"]
    record = {
        "template_key": payload.get("template_key") or "business",
        "template_name": template.get("name"),
        "file_path": template.get("file_path"),
        "page_count": pages,
        "overall_style": template.get("overall_style"),
        "screenshots_path": str(BASE_DIR / "logs" / f"template_screenshots_{tid}"),
        "blueprint_source": "template_pages",
        "frontend_selected": True,
    }
    agent._save_checkpoint(job_id, "selected_template.json", agent._json_dumps(record))
    return record


def _mock_outline_cards(payload: dict) -> list:
    base = [
        ("封面", "title", "{t}", ["公司名称与报告主题", "汇报对象与时间"]),
        ("目录", "section", "汇报内容概览", ["经营总览", "财务表现", "业务与能力", "风险与下一步"]),
        ("经营总览", "summary", "2025年度经营总体表现", ["全年经营总体情况", "核心成果与关键结论"]),
        ("财务表现", "chart", "核心财务数据概览", ["营收与利润总体表现", "盈利质量与现金流", "资产结构稳健性"]),
        ("财务表现", "chart", "主要财务指标与季度走势", ["每股收益与净资产收益率", "季度表现与节奏"]),
        ("经营成果", "chart", "2025年经营亮点", ["业绩亮点", "科技创新与产品突破", "运营效率提升"]),
        ("业务结构", "content", "主营业务与产品结构", ["收入与成本结构", "主要产销情况", "重点板块表现"]),
        ("核心能力", "section", "核心竞争力分析", ["产品与技术领先", "绿色低碳进展", "智慧制造"]),
        ("重点进展", "content", "重大投资与重点项目", ["重点投资方向", "重大项目进展"]),
        ("风险挑战", "content", "当前主要挑战", ["外部环境与行业压力", "经营层面的关键挑战"]),
        ("发展方向", "content", "下一阶段经营计划与重点", ["经营目标与方向", "重点举措与资源安排"]),
        ("结尾", "ending", "总结与展望", ["全年总结", "战略定力与未来展望"]),
    ]
    prompt = (payload.get("prompt") or "").strip()
    t = (prompt[:18] + "…") if len(prompt) > 18 else (prompt or "企业年度经营汇报")
    cards = []
    for i, (sec, ty, title, pts) in enumerate(base, start=1):
        cards.append({"page": i, "template_page_number": i, "section": sec, "type": ty,
                      "title": title.replace("{t}", t), "points": pts})
    return cards


@app.post("/api/poc/outline")
def poc_outline(payload: dict = Body(...)):
    """Generate an editable outline. Calls Kimi when the chosen template has
    complete (>=12 page) data; otherwise returns a structured fallback."""
    from database.db import TemplatePageDAO
    template = _resolve_template(payload.get("template_id"), payload.get("template_name"))
    pages = TemplatePageDAO.get_by_template(template["id"]) if template else []

    # Page-count guard: never exceed the template's own page count.
    req_pages = int(payload.get("page_count") or len(pages) or 12)
    if template and pages and req_pages > len(pages):
        return {"status": "error", "code": "page_count_exceeded",
                "message": f"该模板风格为 {len(pages)} 页，请选择不超过 {len(pages)} 页。",
                "template_pages": len(pages)}

    if template and len(pages) >= _MIN_USABLE_PAGES:
        requirements = _compose_requirements(payload)
        doc_md = _source_markdown(payload.get("input_mode"), payload.get("source_document_name"))
        job_id = agent.start_job(requirements, [])
        GenerationJobDAO.update(job_id, selected_template_id=template["id"])
        if doc_md:
            agent._save_checkpoint(job_id, "document_markdown.md", doc_md)
        _write_selected_template(job_id, template, payload, len(pages))
        try:
            outline = agent.content_generator.generate_outline(
                requirements, doc_md, template, pages, job_id=job_id)
            cards = _outline_to_cards(outline)
            if cards:
                return {"status": "ok", "source": "kimi", "job_id": job_id,
                        "template_name": template["name"], "page_count": len(cards), "outline": cards}
        except Exception as e:
            logger.error(f"Kimi outline failed, using fallback: {e}")

    cards = _mock_outline_cards(payload)
    return {"status": "ok", "source": "fallback", "job_id": None,
            "template_name": payload.get("template_name"),
            "page_count": len(cards), "outline": cards}


def _run_generation(job_id: int, outline: dict, doc_md: str, template: dict):
    """Background worker: real content → layout → render → final, using the
    user-confirmed outline verbatim (no silent rewrite)."""
    try:
        _GEN_STATUS[job_id] = {"state": "generating", "step": "content"}
        slides_data = agent.step_generate_content_and_layout(job_id, outline, doc_md, template)
        _GEN_STATUS[job_id]["step"] = "layout"
        layouts = agent.step_normalize_layouts(job_id, slides_data)
        _GEN_STATUS[job_id]["step"] = "render"
        agent.step_render_preview(job_id, layouts)
        final_path = agent.step_generate_final(job_id, layouts)
        _GEN_STATUS[job_id] = {"state": "done", "final_path": final_path}
    except Exception as e:
        logger.error(f"Generation failed for job {job_id}: {e}")
        _GEN_STATUS[job_id] = {"state": "failed", "error": str(e)}


@app.post("/api/poc/generate")
def poc_generate(payload: dict = Body(...)):
    """Accept the user-confirmed outline and start the real generation pipeline
    in the background. The confirmed outline is used verbatim."""
    from database.db import TemplatePageDAO
    cards = payload.get("outline") or []
    template = _resolve_template(payload.get("template_id"), payload.get("template_name"))
    pages = TemplatePageDAO.get_by_template(template["id"]) if template else []
    ready = bool(template) and len(pages) >= _MIN_USABLE_PAGES

    # Page-count guard: confirmed outline must not exceed the template's pages.
    if template and pages and len(cards) > len(pages):
        return {"status": "error", "code": "page_count_exceeded",
                "message": f"该模板风格为 {len(pages)} 页，请将大纲控制在 {len(pages)} 页以内。",
                "template_pages": len(pages)}

    requirements = _compose_requirements(payload)
    job_id = agent.start_job(requirements, [])
    outline = _cards_to_slides(cards, payload.get("template_key"))   # confirmed outline, verbatim
    if template:
        GenerationJobDAO.update(job_id, selected_template_id=template["id"],
                                outline_json=outline)
        _write_selected_template(job_id, template, payload, len(pages))
    doc_md = _source_markdown(payload.get("input_mode"), payload.get("source_document_name"))
    if doc_md:
        agent._save_checkpoint(job_id, "document_markdown.md", doc_md)
    agent._save_checkpoint(job_id, "confirmed_outline.json", agent._json_dumps(outline))

    if ready:
        _GEN_STATUS[job_id] = {"state": "generating", "step": "queued"}
        threading.Thread(target=_run_generation, args=(job_id, outline, doc_md, template), daemon=True).start()
        msg = "大纲已确认，正在按你的大纲生成 PPT，完成后可下载。"
    else:
        _GEN_STATUS[job_id] = {"state": "pending_template"}
        msg = "大纲已确认并保存。模板数据准备完成后即可生成正式 PPT。"

    return {"status": "submitted", "reference": f"PPT-{job_id:04d}", "job_id": job_id,
            "template_name": payload.get("template_name"), "outline_pages": len(cards),
            "ready": ready, "message": msg}


@app.get("/api/poc/status/{job_id}")
def poc_status(job_id: int):
    st = _GEN_STATUS.get(job_id, {"state": "unknown"})
    out = {"job_id": job_id, "reference": f"PPT-{job_id:04d}", **st}
    if st.get("state") == "done":
        out["download_url"] = f"/api/jobs/{job_id}/download/final"
    return out


# ============================================================================
# Custom Template Live Validation (separate flow from the main built-in POC).
# upload → analyze → index → outline → confirm → generate. Reuses the same
# analyzer / screenshot / TemplateStyleEngine / Kimi pipeline. NOT a marketplace.
# ============================================================================
import os
import sys
import uuid
import subprocess

from fastapi.responses import HTMLResponse as _HTMLResponse

_CUSTOM_HTML_PATH = BASE_DIR / "static" / "templates" / "custom.html"
_CUSTOM_UPLOADS: dict[str, dict] = {}   # token -> {file_path, page_count, template_name, analyze}
_POLLUTION_KW = ["穿透监管", "穿透式监管", "CMCC", "中国移动", "中移", "OneCity",
                 "是否模型", "指标规则", "模型场景", "司库", "VPN", "SD-WAN", "集团专网", "国资委"]


@app.get("/custom", response_class=_HTMLResponse)
def custom_page():
    if _CUSTOM_HTML_PATH.exists():
        return _HTMLResponse(_CUSTOM_HTML_PATH.read_text(encoding="utf-8"))
    return _HTMLResponse("<h1>自定义模板验证</h1><p>页面未就绪。</p>")


@app.post("/api/custom-template/upload")
def custom_upload(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pptx"):
        return JSONResponse({"status": "error", "message": "请上传 PPTX 母版文件。"}, status_code=400)
    token = uuid.uuid4().hex[:10]
    dest = BASE_DIR / "templates_storage" / f"custom_{token}.pptx"
    dest.parent.mkdir(exist_ok=True)
    dest.write_bytes(file.file.read())
    try:
        from pptx import Presentation
        pages = len(Presentation(str(dest)).slides)
    except Exception as e:
        dest.unlink(missing_ok=True)
        return JSONResponse({"status": "error", "message": f"无法解析该 PPTX：{e}"}, status_code=400)
    name = f"客户母版-{Path(file.filename).stem[:24]}-{token[:4]}"
    _CUSTOM_UPLOADS[token] = {"file_path": str(dest), "page_count": pages, "template_name": name}
    return {"status": "ok", "template_upload_id": token, "file_name": file.filename,
            "page_count": pages, "template_name": name}


def _run_custom_analyze(token: str):
    rec = _CUSTOM_UPLOADS.get(token)
    if not rec:
        return
    rec["analyze"] = {"state": "analyzing", "step": "解析与截图"}
    try:
        # Reuse the existing analyzer module exactly (screenshot + analyzer + DB insert).
        proc = subprocess.run(
            [sys.executable, "-m", "template_analyzer.analyze_template",
             "--input", rec["file_path"], "--name", rec["template_name"]],
            cwd=str(BASE_DIR), capture_output=True, text=True, timeout=3600,
        )
        if proc.returncode != 0:
            rec["analyze"] = {"state": "failed", "error": proc.stderr[-400:]}
            return
        from database.db import TemplatePageDAO
        tpl = _resolve_template(None, rec["template_name"])
        pages = TemplatePageDAO.get_by_template(tpl["id"]) if tpl else []
        rec["template_id"] = tpl["id"] if tpl else None
        rec["analyze"] = {"state": "ready" if len(pages) >= 1 else "failed",
                          "pages": len(pages)}
    except Exception as e:
        rec["analyze"] = {"state": "failed", "error": str(e)}


@app.post("/api/custom-template/analyze")
def custom_analyze(payload: dict = Body(...)):
    token = payload.get("template_upload_id")
    rec = _CUSTOM_UPLOADS.get(token)
    if not rec:
        return JSONResponse({"status": "error", "message": "上传记录不存在，请重新上传。"}, status_code=404)
    rec["analyze"] = {"state": "queued"}
    threading.Thread(target=_run_custom_analyze, args=(token,), daemon=True).start()
    return {"status": "started", "template_upload_id": token, "template_name": rec["template_name"]}


@app.get("/api/custom-template/status/{token}")
def custom_status(token: str):
    rec = _CUSTOM_UPLOADS.get(token)
    if not rec:
        return JSONResponse({"status": "error", "message": "记录不存在"}, status_code=404)
    a = rec.get("analyze", {"state": "uploaded"})
    out = {"template_upload_id": token, "template_name": rec["template_name"],
           "page_count": rec["page_count"], **a}
    if a.get("state") == "ready":
        out["index"] = _build_template_index(rec["template_name"])
    return out


def _build_template_index(template_name: str) -> list:
    """Slide index for a (custom) template: thumbnail/page_type/slot counts/warnings."""
    from database.db import TemplatePageDAO
    from core.template_style_engine import TemplateStyleEngine
    from core import page_type_prompt as ptp
    tpl = _resolve_template(None, template_name)
    if not tpl:
        return []
    pages = TemplatePageDAO.get_by_template(tpl["id"])
    total = len(pages)
    idx = []
    for p in pages:
        lj = json.loads(p["layout_json"]) if p.get("layout_json") else {}
        bp = TemplateStyleEngine({"layout_json": lj,
                                  "visual_json": json.loads(p.get("visual_json") or "{}")}).blueprint
        slots = bp.get("slots", {})
        shapes = lj.get("shapes", [])
        tables = sum(1 for s in shapes if "table" in s)
        pics = sum(1 for s in shapes if s.get("is_picture"))
        groups = sum(1 for s in shapes if "GROUP" in str(s.get("shape_type", "")))
        ptype = ptp.classify(p["page_number"], total, None, ptp.slot_summary(bp))
        md = p.get("markdown_content") or ""
        warns = []
        hit = [kw for kw in _POLLUTION_KW if kw in md]
        if hit:
            warns.append("含旧模板用词，建议清洗：" + "、".join(hit[:4]))
        if not slots.get("content") and not slots.get("labels") and not tables:
            warns.append("未检测到可填充区域")
        idx.append({
            "page": p["page_number"],
            "thumbnail": f"/api/custom-template/thumbnail/{tpl['id']}/{p['page_number']}",
            "page_type": ptp.describe(ptype),
            "content_slots": len(slots.get("content", [])),
            "label_slots": len(slots.get("labels", [])),
            "tables": tables, "pictures": pics, "groups": groups,
            "recommended_use": ptp.describe(ptype),
            "warnings": warns,
        })
    return idx


@app.get("/api/custom-template/thumbnail/{tid}/{n}")
def custom_thumbnail(tid: int, n: int):
    p = BASE_DIR / "logs" / f"template_screenshots_{tid}" / f"slide_{n}.png"
    if not p.exists():
        return JSONResponse({"error": "no thumbnail"}, status_code=404)
    return FileResponse(str(p))


@app.post("/api/custom-template/outline")
def custom_outline(payload: dict = Body(...)):
    # Reuse the same Kimi outline path, bound to the custom template by name.
    return poc_outline(payload)


@app.post("/api/custom-template/generate")
def custom_generate(payload: dict = Body(...)):
    return poc_generate(payload)

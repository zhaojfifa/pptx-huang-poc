"""
Page-type prompt router.

Different template pages play different roles (cover / agenda / summary / content
/ table / dense-label / closing). A single generic prompt under-serves them. This
module classifies a page from its outline hint + slot composition and provides
per-type guidance that the content generator injects into the slide prompt.

Pure functions, no LLM, no DB — safe to unit-test and call from anywhere.
"""

from __future__ import annotations

COVER = "cover"
AGENDA = "agenda"
SUMMARY = "summary"
CONTENT = "content"
TABLE = "table"
DENSE_LABELS = "dense_labels"
CLOSING = "closing"


def slot_summary(blueprint: dict) -> dict:
    """Reduce a TemplateStyleEngine blueprint to counts used for classification."""
    slots = (blueprint or {}).get("slots", {}) or {}
    return {
        "title": 1 if slots.get("title") else 0,
        "subtitle": 1 if slots.get("subtitle") else 0,
        "content": len(slots.get("content", []) or []),
        "labels": len(slots.get("labels", []) or []),
        "tables": len(slots.get("tables", []) or []),
    }


def classify(slide_index: int, total_pages: int, outline_type: str | None, slots: dict) -> str:
    """Return a page_type. slots = slot_summary() dict.

    Order matters: structural signals (table) win over positional ones.
    """
    t = (outline_type or "").lower()
    content = slots.get("content", 0)
    labels = slots.get("labels", 0)
    tables = slots.get("tables", 0)

    if tables > 0:
        return TABLE
    if slide_index == 1 or t in ("title", "cover"):
        return COVER
    if slide_index == total_pages or t in ("ending", "closing", "thanks"):
        return CLOSING
    if t in ("section", "agenda", "toc") or (slide_index == 2 and content <= max(1, labels)):
        return AGENDA
    # heavy label grids (e.g. dashboards) with little prose
    if labels >= 12 and content <= max(2, labels // 4):
        return DENSE_LABELS
    # early content-light, conclusion-style page
    if slide_index in (3,) and content <= 6 and t in ("chart", "content", "summary"):
        return SUMMARY
    return CONTENT


# Per-type guidance injected into the slide content prompt. Kept concise; the
# strict slot-count / capacity rules are still enforced by the caller.
_GUIDANCE = {
    COVER: (
        "【页面类型：封面】只产出一句概括性主标题 + 一句副标题（报告对象/时间/性质）。"
        "不要堆要点，不要 bullet 列表，正式、庄重、简洁。"
    ),
    AGENDA: (
        "【页面类型：目录/章节】输出结构清晰的章节导航：标题短、平行、可读，"
        "是全篇结构的总领，不是正文摘要。每个条目为简短章节名，禁止长句。"
    ),
    SUMMARY: (
        "【页面类型：经营总览】结论先行：先给最值得管理层关注的核心结论与关键数字，"
        "再给支撑要点。管理层应能一眼读懂，避免抽象套话。"
    ),
    CONTENT: (
        "【页面类型：正文】每个 block 都要有明确角色，紧扣本页主题与相关文档摘录，"
        "信息密集、数据驱动；不留空条、不堆抽象词。"
    ),
    TABLE: (
        "【页面类型：表格】必须输出 table_data（headers + rows），与表头结构、行数对齐；"
        "列建议覆盖指标/数据/含义/管理动作；数据必须有文档依据，不要把表格拆成普通碎片。"
    ),
    DENSE_LABELS: (
        "【页面类型：高密度标签】产出短标签（多为 2-8 字），不写长句；"
        "贴合本页主题，禁止引入旧模板的业务用词。"
    ),
    CLOSING: (
        "【页面类型：尾页】简短收束：总结语 + 后续行动/展望；"
        "不重复正文，不写复杂业务段落。"
    ),
}


# Style overlays keyed by template_key. Appended after the page-type guidance so
# the same page role reads differently per template style.
_STYLE_OVERLAY = {
    "tech_blue": (
        "【风格：科技蓝】强调技术方案、数字化转型、架构与平台能力、数据驱动与智能化，"
        "保持企业汇报专业口吻。标题更偏「能力建设 / 技术路径 / 应用场景 / 平台价值」，"
        "避免纯财务报表口吻；多用架构/平台/能力/场景/路径/闭环/价值，少用空泛科技营销词；"
        "所有内容必须 grounded 于输入资料。表格页仍需指标/数据/业务含义/管理动作，"
        "不得变成空泛技术表。首页/目录/尾页仍遵守各自规则。"
    ),
    "business": (
        "【风格：商务】经营汇报口吻：结论先行、数据驱动、稳健正式；"
        "突出经营成果、财务指标、风险与下一步重点。"
    ),
}


def content_guidance(page_type: str, template_key: str | None = None) -> str:
    base = _GUIDANCE.get(page_type, _GUIDANCE[CONTENT])
    overlay = _STYLE_OVERLAY.get((template_key or "").lower())
    return base + ("\n" + overlay if overlay else "")


def describe(page_type: str) -> str:
    """Short human-readable label (for logs / traces)."""
    return {
        COVER: "封面", AGENDA: "目录/章节", SUMMARY: "经营总览", CONTENT: "正文",
        TABLE: "表格", DENSE_LABELS: "高密度标签", CLOSING: "尾页",
    }.get(page_type, page_type)

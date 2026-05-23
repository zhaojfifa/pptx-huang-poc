from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class TemplateInfo(BaseModel):
    id: int
    name: str
    file_path: str
    overall_style: Optional[dict] = None


class TemplatePageInfo(BaseModel):
    id: int
    template_id: int
    page_number: int
    markdown_content: Optional[str] = None
    layout_json: Optional[dict] = None
    visual_json: Optional[dict] = None
    generation_hints: Optional[dict] = None


class PageLayout(BaseModel):
    page_number: int
    width: float
    height: float
    background_color: Optional[str] = None
    background_image: Optional[str] = None
    shapes: List[Dict[str, Any]] = []


class SlideOutline(BaseModel):
    title: str
    slides: List[Dict[str, Any]]


class GenerationRequest(BaseModel):
    user_requirements: str
    input_files: Optional[List[str]] = []


class ConfirmRequest(BaseModel):
    job_id: int
    confirmed: bool
    feedback: Optional[str] = None


class RenderRequest(BaseModel):
    job_id: int
    confirmed: bool
    feedback: Optional[str] = None

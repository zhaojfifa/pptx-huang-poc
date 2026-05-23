#!/usr/bin/env python3
"""
CLI entry point for PPTX Agent.

Usage:
    python main.py --requirements "年度汇报PPT，商务风格" --files report.docx data.xlsx
"""

import argparse
import logging
import sys
from pathlib import Path

from config.settings import LOGS_DIR
from core.agent import PPTXAgent
from database.db import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / "agent_cli.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def run_cli(requirements: str, files: list, auto_confirm: bool = False):
    init_db()
    agent = PPTXAgent()

    job_id = agent.start_job(requirements, files)
    logger.info(f"Job started: {job_id}")

    # Step 1: documents
    doc_md = agent.step_process_documents(job_id)
    print(f"[1/7] Documents processed. Markdown length: {len(doc_md)}")

    # Step 2: template
    template = agent.step_select_template(job_id, requirements, doc_md)
    print(f"[2/7] Template selected: {template['name']} (ID={template['id']})")

    # Step 3: outline
    outline = agent.step_generate_outline(job_id, requirements, doc_md, template)
    print(f"[3/7] Outline generated with {len(outline.get('slides', []))} slides.")
    print("\n--- Outline Preview ---")
    for s in outline.get("slides", []):
        print(f"  Slide {s.get('slide_number')}: {s.get('title')}")
    print("-----------------------\n")

    if auto_confirm:
        print("[Auto-confirm] Outline approved.")
    else:
        confirm = input("Confirm outline? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Aborted.")
            return

    # Step 4-5: content & layout
    slides_data = agent.step_generate_content_and_layout(job_id, outline, doc_md, template)
    print(f"[4/7] Content generated for {len(slides_data)} slides.")

    layouts = agent.step_normalize_layouts(job_id, slides_data)
    print(f"[5/7] Layouts normalized.")

    # Step 6: render preview
    preview_path = agent.step_render_preview(job_id, layouts)
    print(f"[6/7] Preview rendered: {preview_path}")

    if auto_confirm:
        print("[Auto-confirm] Preview approved, generating final.")
    else:
        confirm = input("Confirm preview and generate final? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Aborted.")
            return

    # Step 7: final
    final_path = agent.step_generate_final(job_id, layouts)
    print(f"[7/7] Final PPTX saved: {final_path}")


def main():
    parser = argparse.ArgumentParser(description="PPTX Agent CLI")
    parser.add_argument("--requirements", required=True, help="User requirements text")
    parser.add_argument("--files", nargs="*", default=[], help="Input document files")
    parser.add_argument("--auto-confirm", action="store_true", help="Auto-confirm all steps without interactive prompts")
    args = parser.parse_args()

    run_cli(args.requirements, args.files, auto_confirm=args.auto_confirm)


if __name__ == "__main__":
    main()

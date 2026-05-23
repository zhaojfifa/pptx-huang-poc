# pptx-huang-poc

Huang-based PPT Agent POC production path.

This repository is the independent POC baseline for the Huang generation service.

## Current Scope

- Main POC page: built-in templates only
  - business / t5 / 商务风格
  - tech_blue / t6 / 科技蓝
- Custom Template Live Validation page: `/custom`
- Main flow: upload business document, choose template style, generate outline, confirm outline, generate PPT.
- Custom flow: upload customer PPTX master in `/custom`, analyze template, show slide index, generate PPT.

## Local Start

```bash
cd /Users/tylerzhao/Code/pptx-huang-poc
.venv_huang/bin/uvicorn web.app:app --host 0.0.0.0 --port 8000
```

If `.venv_huang` is not present, recreate the Python environment before starting:

```bash
python3.13 -m venv .venv_huang
.venv_huang/bin/pip install -r requirements.txt
```

A running MySQL is required (see `config/settings.py` for connection env vars), plus
LibreOffice (`soffice`) and `pypdfium2` for the macOS screenshot backend.

## URLs

- Main POC page: http://localhost:8000/
- Custom Template Live Validation: http://localhost:8000/custom

## Not In Scope

- Not a template marketplace
- No public deployment yet
- No user account / permission system
- No payment
- No multi-tenant storage
- No old mainline PR-F2/F3 integration

## Migration Note

- Migrated from: `/Users/tylerzhao/Code/ppt-agent-poc/data/pptx_agent_20260521/`
- Source branch: `feature/huang-dual-template-baseline`
- Source baseline commit: `4fd3cdb`
- Strategy: the Huang independent POC path is the source of truth; old main architecture
  fusion is deferred until after POC validation.

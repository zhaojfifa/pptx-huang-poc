# Runbook

## Start Service

```bash
cd /Users/tylerzhao/Code/pptx-huang-poc
.venv_huang/bin/uvicorn web.app:app --host 0.0.0.0 --port 8000
```

If `.venv_huang` is not present, recreate the virtual environment:

```bash
python3.13 -m venv .venv_huang
.venv_huang/bin/pip install -r requirements.txt
```

A running MySQL is required; LibreOffice (`soffice`) + `pypdfium2` are required for the
macOS screenshot backend.

## Open Pages

- Main POC page: http://localhost:8000/
- Custom template page: http://localhost:8000/custom

## Manual Checks

Main page:

- exposes only business/t5 and tech_blue/t6
- business upload is for source documents, not PPTX templates
- links to `/custom`

Custom page:

- `/custom` opens
- PPTX upload works
- non-PPTX upload is rejected
- analyze starts
- status polling works
- slide index appears after ready
- outline generation works
- generate starts
- download link appears after completion

## Known Issues

- analyze may take 10–25 minutes
- upload state is in-memory and lost after restart
- strict integrity gate is not implemented yet
- template cleaning is not automatic yet
- trend / line chart capability is not implemented yet
- not public deployment

## Local Environment Setup

```bash
cd /Users/tylerzhao/Code/pptx-huang-poc
python3 -m venv .venv_huang
.venv_huang/bin/pip install --upgrade pip
.venv_huang/bin/pip install -r requirements.txt
```

Then start:

```bash
.venv_huang/bin/uvicorn web.app:app --host 0.0.0.0 --port 8000
```

Notes:

- `.env` is required for real Kimi / model calls.
- Do not commit `.env`.
- MySQL / template DB state may be required for full generation.
- For UI smoke test, route import can be checked before full generation.

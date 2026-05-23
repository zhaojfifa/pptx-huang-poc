# Template Asset Policy

## 1. Current Decision / 当前裁决

- Do not commit `templates_storage/*.pptx` yet.
- Do not commit customer uploaded templates.
- Do not commit generated PPTX/PNG.
- Approved source templates may later be placed under `data/templates/`.

## 2. Current Known Local Assets / 当前已知本地资产

- `templates_storage/t1.pptx` – `templates_storage/t6.pptx`
- `templates_storage/test_template.pptx`
- `static/previews/` (generated preview renders)
- `test.mmd`
- `test_diag.mmd`
- `test_template.pptx`
- `test_with_chart.pptx`

## 3. Classification / 分类

| Asset | Classification | Action |
|---|---|---|
| `t5.pptx`, `t6.pptx` | Required built-in source templates | Approval needed before tracking |
| `t1.pptx` – `t4.pptx` | Legacy / optional | Do not track now |
| `test_template.pptx`, `test_with_chart.pptx`, `test*.mmd` | Scratch | Do not track |
| `static/previews/` | Generated preview assets | Do not track |

## 4. Recommended Future Policy / 推荐未来策略

- **Option A:** keep templates local-only and document setup.
- **Option B:** commit approved small templates under `data/templates/`.
- **Option C:** use Git LFS for approved templates.
- **Recommended current default:** local-only until manual validation confirms final t5/t6 assets.

## 5. Fresh Clone Risk / 全新克隆风险

- A fresh clone may not fully run built-in template generation until approved t5/t6 templates and external DB state are restored.
- This is acceptable for the current baseline but must be resolved before deployment.

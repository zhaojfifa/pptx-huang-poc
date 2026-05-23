# Skill: markitdown

Convert various document formats (pptx, docx, txt, pdf) to Markdown text.

## Usage

```python
from skills.skill_markitdown.markitdown_skill import MarkItDownSkill

skill = MarkItDownSkill()
markdown_text = skill.convert("path/to/file.pptx")
```

## Dependencies

- `markitdown`

Install via: `pip install markitdown`

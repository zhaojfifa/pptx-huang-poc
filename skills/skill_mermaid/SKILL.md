# Skill: Mermaid CLI

Generate diagrams from Mermaid text definitions using mermaid-cli (`mmdc`).

## Usage

```python
from skills.skill_mermaid.mermaid_skill import MermaidSkill

skill = MermaidSkill()
output_path = skill.render("graph TD; A-->B", "output.png")
```

## Dependencies

- `mermaid-cli` (`mmdc`)

Install via: `npm install -g @mermaid-js/mermaid-cli`

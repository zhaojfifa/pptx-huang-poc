# Project Status

## Current Strategy

The Huang independent POC path is now the source of truth for the PPT Agent POC.

## Short-term Goal

Reach POC 4.5+ demo quality.

## Main Flow

Business document + built-in template → outline → confirm → generate.

Built-in templates:

- business / t5 / 商务风格
- tech_blue / t6 / 科技蓝

## Custom Flow

Upload customer PPTX template → analyze → slide index → outline → confirm → generate.

## Current Baseline

Custom Template Live Validation MVP.

Baseline source:

- source path: `/Users/tylerzhao/Code/ppt-agent-poc/data/pptx_agent_20260521/`
- source branch: `feature/huang-dual-template-baseline`
- source commit: `4fd3cdb`

## Deferred Items

- strict integrity gate
- template cleaning
- trend / line chart capability
- upload persistence
- security hardening
- deployment evaluation

## Deployment Note

Public deployment is deferred. 阿里云 (Aliyun) can be evaluated later after POC quality
is validated.

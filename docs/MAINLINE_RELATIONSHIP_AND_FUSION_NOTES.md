# Mainline Relationship and Fusion Notes

## 1. Current Decision / 当前裁决

- `pptx-huang-poc` is the current independent Huang POC production path.
- `ppt-agent-poc` remains the historical main architecture and future capability reference.
- Deep fusion is deferred until after POC validation.
- Current goal is POC 4.5+ demo quality.

## 2. Why Independent Repo / 为什么独立

- Faster POC iteration without legacy coordination overhead.
- Cleaner deployment boundary for the Huang POC path.
- Reduced legacy architecture drag.
- Easier GitHub sync and future 阿里云 deployment evaluation.
- Clearer manual validation path.

## 3. Source Relationship / 来源关系

Old source path:

```
/Users/tylerzhao/Code/ppt-agent-poc/data/pptx_agent_20260521/
```

New repo path:

```
/Users/tylerzhao/Code/pptx-huang-poc/
```

Old source branch:

```
feature/huang-dual-template-baseline
```

Old source commit:

```
4fd3cdb
```

New repo baseline commit:

```
20a3413
```

## 4. Capabilities to Potentially Migrate from Old Mainline / 未来可迁移能力

Future candidates only:

- Source Discipline Guard
- forbidden_terms hard fail
- package scan for notes/docProps/comments/commentAuthors
- final PPTX text scan
- regression anchor concept
- human review rubric
- stable production rules
- contract / registry design ideas
- table / chart expression rules
- deployment / service hardening lessons

## 5. Capabilities Not to Migrate Now / 当前不迁移

- old backend/expression pipeline
- PR-F2/F3 worktree code
- full contract unification
- long-term rules platform
- template marketplace
- large-scale multi-template management backend
- public deployment stack

## 6. Future Fusion Criteria / 未来融合条件

Fusion may be considered after:

- Huang POC reaches stable 4.5+ quality
- business/t5 flow is clean
- custom template validation passes manual test
- strict integrity gate is added
- template cleaning is available
- trend / line chart capability is clarified
- deployment path is decided
- CodexL reviews architecture readiness

## 7. Current Next Steps / 当前下一步

- push independent repo to GitHub
- run manual validation on `/` and `/custom`
- decide template asset policy
- add strict integrity gate later
- add template cleaning later
- add trend / line chart later
- evaluate 阿里云 deployment later

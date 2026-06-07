# Skill Modularization Policy

ForgeFlow skills are runtime contracts, not dumping grounds. A large `SKILL.md` is allowed only when it remains navigable and delegates reusable detail to references.

## Rules

1. **Keep SKILL.md focused on stage contracts**: inputs, outputs, exit conditions, hard gates, and the shortest executable procedure belong inline.
2. **Move repeated policy into skills/_shared/**: discipline, isolation, preflight, automation, and resume behavior must be centralized when more than one skill needs them.
3. **Move adapter-specific behavior into references/**: CLI quirks, standalone fetch behavior, subagent prompts, role rubrics, and long checklists belong under `skills/<skill>/references/`.
4. **Declare dependencies in frontmatter**: shared policy files must appear in `dependencies:` so plugin importers and reviewers can see the contract surface without reading the whole body.
5. **Declare a Reference inventory**: each large workflow skill must include a `## Reference inventory` section with Markdown links to the references it relies on.
6. **Prefer links over copy-paste**: if the same paragraph would appear in two skills, put it in `_shared` or a skill reference and link it.

## Validation

Run:

```sh
make validate-skill-modularity
```

The target is also part of `make validate`. It checks that the high-churn workflow skills (`clarify`, `ff-plan`, `execute`, `ff-review`) stay under their inline size budgets, declare shared dependencies, and link required reference files.

This guard is intentionally boring. Boring is good here; entropy is the enemy, not insufficient creativity.

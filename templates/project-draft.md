---
schema: project-draft/v1
generated: <!-- ISO date -->
repo_type: <!-- auto-detected: node|python|rust|go|other -->
adapter_preset: <!-- recommended adapter -->
---

# Project Architecture Draft

## Purpose

This artifact is the reusable project context for ForgeFlow tasks. It summarizes stable project knowledge and points to source documents so future `clarify`, `plan`, and `execute` stages can avoid repeated discovery.

## Detected Context
- **Language/Framework**: <!-- from package.json/pyproject.toml/Cargo.toml/go.mod -->
- **Structure**: <!-- monorepo|single-package|library|CLI -->
- **Test Framework**: <!-- jest|pytest|cargo test|go test -->

## Team Structure
- **Roles**: <!-- from CONTRIBUTING.md or repo analysis -->
- **Review Policy**: <!-- based on route defaults -->
- **Merge Strategy**: <!-- squash|merge|rebase -->

## Agent Configuration
- **Recommended Adapter**: <!-- claude|codex|gemini|cursor — based on repo type -->
- **Skill Overrides**: <!-- project-specific tuning -->
- **Specialist Presets**: <!-- security|ux|perf — based on detected patterns -->

## Reusable Project Context
- **Product/Planning Docs**: <!-- repo-relative paths to PRD/spec/planning docs; summarize only stable decisions -->
- **Architecture Docs**: <!-- repo-relative paths to architecture diagrams/docs and key invariants -->
- **Roadmap/WBS**: <!-- repo-relative paths to roadmap, WBS, milestone, or task breakdown docs -->
- **Decision Records**: <!-- repo-relative paths to ADRs/decision logs; include short decision labels -->
- **Cross-Module Contracts**: <!-- stable interfaces, data shapes, integration boundaries, compatibility constraints -->
- **Verification Conventions**: <!-- build/lint/type_check/test commands and route-specific gates -->
- **Sensitive Context Policy**: <!-- record where secrets are documented, never copy token/API key/credential values here -->

## Context Usage Rules
- Treat this artifact as a summary and pointer index, not the source of truth.
- Prefer repo-relative document pointers over copying long source documents into task artifacts.
- During task work, copy only the specific decisions, constraints, and verification gates needed by the current task.
- If a referenced document conflicts with this draft, the referenced document wins and this draft should be refreshed.

## Custom Skill Outlines
### <!-- skill name -->
- **Trigger**: <!-- when to use -->
- **Scope**: <!-- what it covers -->
- **Output**: <!-- expected artifact -->

## Documentation Pointers
- **README**: <!-- path -->
- **Contributing**: <!-- path -->
- **API Docs**: <!-- path -->
- **Changelog**: <!-- path -->

## Init Checklist
- [ ] Defaults configured (.forgeflow/defaults.md)
- [ ] Adapter selected and configured
- [ ] Product/planning document pointers reviewed
- [ ] Architecture and contract pointers reviewed
- [ ] Roadmap/WBS pointers reviewed
- [ ] Custom skills reviewed
- [ ] Documentation pointers verified
- [ ] First task ready

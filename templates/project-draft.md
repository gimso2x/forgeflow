---
schema: project-draft/v1
generated: <!-- ISO date -->
repo_type: <!-- auto-detected: node|python|rust|go|other -->
adapter_preset: <!-- recommended adapter -->
---

# Project Architecture Draft

## Purpose

This artifact is generated at the target project root as `.forgeflow/project-draft.md` by `/forgeflow:config init --mode=full`. It is reusable project context for ForgeFlow tasks: a stable summary and repo-relative pointer index that lets future `clarify`, `plan`, and `execute` stages avoid repeated discovery without copying long source documents.

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
- **Product/Planning Docs**: <!-- repo-relative paths to PRD/spec/planning docs; summarize only stable decisions and non-goals -->
- **Architecture Docs**: <!-- repo-relative paths to architecture diagrams/docs and key invariants -->
- **Roadmap/WBS**: <!-- repo-relative paths to roadmap, WBS, milestone, or task breakdown docs -->
- **Decision Records**: <!-- repo-relative paths to ADRs/decision logs; include short decision labels -->
- **Cross-Module Contracts**: <!-- stable interfaces, data shapes, integration boundaries, compatibility constraints -->
- **Verification Conventions**: <!-- exact build/lint/type_check/test commands and route-specific gates -->
- **Sensitive Context Policy**: <!-- record policy/doc/env var names only; never copy token/API key/credential/private key values here -->

## Context Usage Rules
- Treat this artifact as shared context only, not the task-specific source of truth.
- `brief.md`, `plan.md`, `run-ledger.md`, and `implementation-notes.md` remain the source of truth for a specific task.
- Prefer repo-relative document pointers and short decision labels over copying long source documents into task artifacts.
- `clarify`, `plan`, and `execute` should read only task-relevant sections and referenced source paths.
- Before changing behavior, verify task-critical facts against the referenced source documents or code.
- If a referenced document conflicts with this draft, the referenced document wins and this draft should be refreshed.

## Custom Skill Outlines
### <!-- skill name -->
- **Trigger**: <!-- when to use -->
- **Scope**: <!-- what it covers -->
- **Output**: <!-- expected artifact -->

## Documentation Pointers
- **README**: <!-- repo-relative path and the sections downstream skills should consult -->
- **Contributing**: <!-- repo-relative path for contribution/review conventions, if present -->
- **API Docs**: <!-- repo-relative path or n/a; include contract sections, not copied API bodies -->
- **Changelog**: <!-- repo-relative path for release/version context, if present -->

## Init Checklist
- [ ] Defaults configured (.forgeflow/defaults.md)
- [ ] Adapter selected and configured
- [ ] Product/planning document pointers reviewed
- [ ] Architecture and contract pointers reviewed
- [ ] Roadmap/WBS pointers reviewed
- [ ] Custom skills reviewed
- [ ] Documentation pointers verified
- [ ] First task ready

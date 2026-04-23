# Gate surface

This directory reserves the gate-enforcement surface for the runtime.

Canonical source of truth remains:
- `policy/canonical/gates.yaml`
- `policy/canonical/stages.yaml`

Runtime responsibilities:
- block stage transitions when required artifacts are missing
- require review approval flags before `finalize`
- preserve the invariant that `spec-review` gates `quality-review`

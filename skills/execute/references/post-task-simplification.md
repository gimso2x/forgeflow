# Post-task Simplification Loop

Use this reference from `skills/execute/SKILL.md` after each plan step passes verification.

Run an iterative refinement loop on the **changed code** (`git diff` against the step's starting point) until the delta converges to zero.

## Principles

- **Phase 1 - Identification**: Focus exclusively on the diff. Ignore unrelated files.
- **Phase 2 - Triple-Lens Analysis**:
  - **Lens 1 (Code Reuse)**: Replace new logic with existing utils, constants, or types.
  - **Lens 2 (Code Quality)**: Eliminate stringly-typed code, redundant wrappers, and abstraction boundary violations.
  - **Lens 3 (Efficiency)**: Optimize hot paths, remove redundant resource reads, improve concurrency.
- **Phase 3 - Iterative Refinement**:
  - **Converge to Zero**: Repeat the refinement cycle until no further meaningful improvements are identified.
  - **Comment Preservation**: **절대 주석을 삭제하지 마라.** 주석은 "왜"를 설명하는 핵심 신호다.
  - **False Positive Filtering**: Only apply changes with clear present value. Avoid over-engineering.

## Verification

- Run focused tests after each refinement cycle.
- If a simplification breaks a test, immediately revert (`git restore`) and skip that change.
- Record each applied simplification in `implementation-notes.md` Evidence as `simplify:PASS lens=<1|2|3> desc="<change>"`.

## Scope

- **small / medium**: Run once after the final step only.
- **high / epic**: Run after every step.

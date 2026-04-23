# Skill: specify

## Purpose

Derive a structured, machine-verifiable **requirements.md** from the Context Brief through a decision interview. This is hoyeon's "requirements-first" layer adapted to ForgeFlow's artifact chain.

## Trigger

- After `clarify` completes with a brief.
- User says: `"specify this"`, `"write requirements"`, or any trigger that implies formalizing scope.

## Input

- `brief.json`
- Codebase context

## Output Artifacts

| Artifact | Schema | Description |
|----------|--------|-------------|
| `requirements.md` | Markdown (structured) | Decision chain + requirements + sub-requirements + behavioral statements. |

## Execution

Derive downward through a strict layer chain. Each layer references the one above it.

```
L0: Goal              ← from brief.json
L1: Context           ← codebase analysis, UX review, docs research
L2: Decisions         ← decision interview → implications derivation
L3: Requirements      ← R1, R2, ... with sub-requirements
L4: Sub-requirements  ← behavioral statements (testable)
```

### Decision interview (L2)

Ask the user forced-choice questions to expose assumptions. Examples:
- "System preference or manual toggle?"
- "Which components need theme variants?"
- "Persist where? localStorage, cookie, or backend?"

Every decision must have a **rationale** and a list of **implications**.

### Requirements format (L3)

Each requirement:
- `ID`: R1, R2, ...
- `Statement`: One sentence, active voice.
- `Priority`: must / should / could
- `Source`: Which decision(s) it derives from.

### Sub-requirements format (L4)

Each sub-requirement is a **behavioral statement** that can be verified automatically or manually:
- `ID`: R1.1, R1.2, ...
- `Behavior`: Given X, when Y, then Z.
- `Verification`: How to check (test, inspection, demo).

## Constraints

- Sub-requirements must be testable. If you can't write a test for it, it's not a sub-requirement.
- No placeholders. Every requirement traces back to a decision or the goal.
- Do not derive tasks here. Tasks come in `plan`.

## Example `requirements.md` fragment

```markdown
## Decisions

| ID | Decision | Rationale | Implications |
|----|----------|-----------|--------------|
| D1 | Manual toggle + system preference | Covers both power users and defaults | Needs 3-state logic: light, dark, system |

## Requirements

### R1: Theme Toggle
- **Statement**: The user can switch between light, dark, and system themes.
- **Priority**: must
- **Source**: D1

#### R1.1: Toggle Component
- **Behavior**: Given the user is on the settings page, when they click the theme toggle, then the theme changes immediately without a page reload.
- **Verification**: UI test
```

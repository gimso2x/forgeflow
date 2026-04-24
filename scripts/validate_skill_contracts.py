#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILLS = [
    'skills/clarify/SKILL.md',
    'skills/specify/SKILL.md',
    'skills/plan/SKILL.md',
    'skills/run/SKILL.md',
    'skills/review/SKILL.md',
    'skills/ship/SKILL.md',
    'skills/finish/SKILL.md',
    'skills/verify/SKILL.md',
    'skills/x-debug.md',
    'skills/x-deslop.md',
    'skills/x-qa.md',
    'skills/x-learn.md',
    'skills/x-spec-review.md',
    'skills/x-resume.md',
    'skills/x-office-hours.md',
    'skills/x-tdd.md',
]
MODAL_WORDS = ('must', 'requires', 'forbid', 'never', 'only')


def extract_frontmatter(text: str) -> str | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == '---':
            return '\n'.join(lines[1:index])
    return None


def extract_block_scalar(frontmatter: str, key: str) -> str | None:
    lines = frontmatter.splitlines()
    prefix = f'{key}:'
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            rest = line[len(prefix):].strip()
            if rest not in {'|', '>'}:
                return rest or None
            block: list[str] = []
            for next_line in lines[index + 1:]:
                if next_line and not next_line.startswith((' ', '\t')):
                    break
                block.append(next_line[2:] if next_line.startswith('  ') else next_line.lstrip())
            return '\n'.join(block).strip()
    return None


def validate_skill(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding='utf-8')
    frontmatter = extract_frontmatter(text)
    if frontmatter is None:
        return ['missing frontmatter']
    contract = extract_block_scalar(frontmatter, 'validate_prompt')
    if contract is None:
        return ['missing validate_prompt frontmatter field']
    non_empty_lines = [line.strip() for line in contract.splitlines() if line.strip()]
    if len(non_empty_lines) < 2:
        errors.append('validate_prompt must contain at least two non-empty lines')
    lowered = contract.lower()
    if not any(word in lowered for word in MODAL_WORDS):
        errors.append(f"validate_prompt must include one modal word: {', '.join(MODAL_WORDS)}")
    if len(contract) < 80:
        errors.append('validate_prompt is too short to be a useful output contract')
    return errors


def main() -> int:
    errors: list[str] = []
    checked = 0
    for rel in CANONICAL_SKILLS:
        path = ROOT / rel
        if not path.is_file():
            errors.append(f'{rel}: missing skill file')
            continue
        skill_errors = validate_skill(path)
        if skill_errors:
            errors.extend(f'{rel}: {error}' for error in skill_errors)
        checked += 1

    if errors:
        print('SKILL CONTRACT VALIDATION: FAIL')
        for error in errors:
            print(f'- {error}')
        return 1
    print('SKILL CONTRACT VALIDATION: PASS')
    print(f'- checked skills: {checked}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

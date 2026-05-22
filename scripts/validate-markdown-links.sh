#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
import pathlib
import re
import sys
import urllib.parse

root = pathlib.Path('.')
failures = []
anchor_cache = {}


def markdown_anchors(path: pathlib.Path) -> set[str]:
    if path in anchor_cache:
        return anchor_cache[path]
    anchors = {''}
    counts = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped.startswith('#'):
            continue
        heading = stripped.lstrip('#').strip().rstrip('#').strip()
        if not heading:
            continue
        slug = re.sub(r'<[^>]+>', '', heading).lower()
        slug = re.sub('[' + chr(96) + r'*_~]', '', slug)
        slug = re.sub(r'[^\w\s\-가-힣]', '', slug)
        slug = re.sub(r'\s+', '-', slug.strip())
        if not slug:
            continue
        suffix = counts.get(slug, 0)
        counts[slug] = suffix + 1
        anchors.add(slug if suffix == 0 else f'{slug}-{suffix}')
    anchor_cache[path] = anchors
    return anchors


for path in sorted(root.rglob('*.md')):
    if '.git' in path.parts or '.venv' in path.parts:
        continue
    text = path.read_text(encoding='utf-8')
    line_starts = [0]
    for index, char in enumerate(text):
        if char == chr(10):
            line_starts.append(index + 1)

    def location(offset: int) -> str:
        line_no = 1
        for index, start in enumerate(line_starts):
            if start > offset:
                break
            line_no = index + 1
        column = offset - line_starts[line_no - 1] + 1
        return f'{path}:{line_no}:{column}'

    for match in re.finditer(r'(?<!!)\[[^\]]+\]\(([^)]+)\)', text):
        raw = match.group(1).strip()
        target, _, anchor = raw.partition('#')
        target = target.strip()
        if not target or '://' in target or target.startswith(('mailto:', 'tel:')):
            continue
        parsed = urllib.parse.urlparse(target)
        if parsed.scheme:
            continue
        candidate = (path.parent / urllib.parse.unquote(target)).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            failures.append(f'{location(match.start(1))} markdown link escapes repo -> {raw}')
            continue
        if not candidate.exists():
            failures.append(f'{location(match.start(1))} broken markdown link -> {raw}')
            continue
        if anchor and urllib.parse.unquote(anchor) not in markdown_anchors(candidate):
            failures.append(f'{location(match.start(1))} broken markdown anchor -> {raw}')

if failures:
    print('ERROR: Broken markdown links found')
    for failure in failures:
        print(f'- {failure}')
    sys.exit(1)
print('OK: Markdown relative links and anchors resolve')
PY

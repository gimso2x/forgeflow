#!/usr/bin/env bash
set -euo pipefail

"${PYTHON:-python3}" - <<'PY'
import pathlib
import re
import sys
import urllib.parse

root = pathlib.Path('.')
failures = []
anchor_cache = {}


def normalize_anchor(raw: str) -> str:
    anchor = urllib.parse.unquote(raw).strip().lower()
    anchor = re.sub(r'<[^>]+>', '', anchor)
    anchor = re.sub('[' + chr(96) + r'*_~]', '', anchor)
    anchor = re.sub(r'[^\w\s\-가-힣]', '', anchor)
    return re.sub(r'\s+', '-', anchor.strip())


if normalize_anchor('Local checks') != 'local-checks':
    failures.append('markdown anchor normalizer must preserve Latin heading text')
if normalize_anchor('첫 성공 데모') != '첫-성공-데모':
    failures.append('markdown anchor normalizer must preserve Korean heading text')


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
        slug = normalize_anchor(heading)
        # GitHub-style anchors collapse duplicate headings by appending
        # numeric suffixes. Preserve the full normalized slug so Latin
        # heading anchors (for example #local-checks) are checked exactly,
        # not reduced to incidental letters by an over-escaped regex.
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

    fenced_ranges = []
    fence_start = None
    cursor = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(('```', '~~~')):
            if fence_start is None:
                fence_start = cursor
            else:
                fenced_ranges.append((fence_start, cursor + len(line)))
                fence_start = None
        cursor += len(line)
    if fence_start is not None:
        fenced_ranges.append((fence_start, len(text)))

    inline_code_ranges = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        line_end = cursor + len(line)
        index = 0
        while index < len(line):
            if line[index] != '`':
                index += 1
                continue
            tick_end = index + 1
            while tick_end < len(line) and line[tick_end] == '`':
                tick_end += 1
            fence = line[index:tick_end]
            close = line.find(fence, tick_end)
            if close == -1:
                index = tick_end
                continue
            start = cursor + index
            end = min(cursor + close + len(fence), line_end)
            if not any(f_start <= start < f_end for f_start, f_end in fenced_ranges):
                inline_code_ranges.append((start, end))
            index = close + len(fence)
        cursor = line_end

    def in_fenced_code(offset: int) -> bool:
        return any(start <= offset < end for start, end in fenced_ranges)

    def in_inline_code(offset: int) -> bool:
        return any(start <= offset < end for start, end in inline_code_ranges)

    def in_code(offset: int) -> bool:
        return in_fenced_code(offset) or in_inline_code(offset)

    def location(offset: int) -> str:
        line_no = 1
        for index, start in enumerate(line_starts):
            if start > offset:
                break
            line_no = index + 1
        column = offset - line_starts[line_no - 1] + 1
        return f'{path}:{line_no}:{column}'

    def link_destination(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith('<') and '>' in raw:
            return raw[1:raw.index('>')].strip()
        for index, char in enumerate(raw):
            if char.isspace():
                return raw[:index].strip()
        return raw

    def check_target(raw: str, offset: int, kind: str) -> None:
        destination = link_destination(raw)
        target, _, anchor = destination.partition('#')
        target = target.strip()
        if not target and anchor:
            candidate = path.resolve()
        elif not target or '://' in target or target.startswith(('mailto:', 'tel:')):
            return
        else:
            parsed = urllib.parse.urlparse(target)
            if parsed.scheme:
                return
            candidate = (path.parent / urllib.parse.unquote(target)).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            failures.append(f'{location(offset)} {kind} escapes repo -> {raw}')
            return
        if not candidate.exists():
            failures.append(f'{location(offset)} broken {kind} -> {raw}')
            return
        if anchor and normalize_anchor(anchor) not in markdown_anchors(candidate):
            failures.append(f'{location(offset)} broken {kind} anchor -> {raw}')

    for match in re.finditer(r'(?<!\\)(!?)\[[^\]]+\]\(([^)]+)\)', text):
        if in_code(match.start()):
            continue
        raw = match.group(2).strip()
        kind = 'markdown image' if match.group(1) else 'markdown link'
        check_target(raw, match.start(2), kind)

    reference_defs = set()
    for match in re.finditer(r'^\s{0,3}\[([^\]]+)\]:\s+(\S+)', text, re.M):
        if in_code(match.start()):
            continue
        label = match.group(1).strip().casefold()
        if label in reference_defs:
            failures.append(f'{location(match.start(1))} duplicate markdown reference definition -> [{match.group(1)}]')
        reference_defs.add(label)
        raw = match.group(2).strip().strip('<>')
        check_target(raw, match.start(2), 'markdown reference link')

    for match in re.finditer(r'!?(?<!\\)\[([^\]\n]+)\]\[([^\]\n]*)\]', text):
        if in_code(match.start()):
            continue
        label = (match.group(2) or match.group(1)).strip().casefold()
        if label and label not in reference_defs:
            failures.append(f'{location(match.start())} missing markdown reference definition -> [{match.group(1)}][{match.group(2)}]')

    for match in re.finditer(r'<([^<>\s]+)>', text):
        if in_code(match.start()):
            continue
        raw = match.group(1).strip()
        parsed = urllib.parse.urlparse(raw)
        if parsed.scheme or raw.startswith(('#', 'mailto:', 'tel:')):
            continue
        # Treat concrete repository markdown paths in angle brackets as links,
        # while leaving placeholders such as <task-id> or <branch-name> alone.
        target, _, _anchor = raw.partition('#')
        if pathlib.PurePosixPath(urllib.parse.unquote(target)).suffix == '.md':
            check_target(raw, match.start(1), 'markdown autolink')

    for match in re.finditer(r'''<a\s+[^>]*href=["']([^"']+)["']''', text, re.I):
        if in_code(match.start()):
            continue
        check_target(match.group(1).strip(), match.start(1), 'HTML href')

    for match in re.finditer(r'''<img\s+[^>]*src=["']([^"']+)["']''', text, re.I):
        if in_code(match.start()):
            continue
        check_target(match.group(1).strip(), match.start(1), 'HTML img src')

if failures:
    print('ERROR: Broken markdown links found')
    for failure in failures:
        print(f'- {failure}')
    sys.exit(1)
print('OK: Markdown inline/reference/collapsed-reference/autolink relative links, images, HTML href/src, anchors, and unique reference definitions resolve outside code spans')
PY

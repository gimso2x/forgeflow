#!/usr/bin/env python3
"""Extracted from Makefile target: validate-changelog-links"""
import pathlib, re, sys

version = pathlib.Path('VERSION').read_text(encoding='utf-8').strip()
text = pathlib.Path('CHANGELOG.md').read_text(encoding='utf-8')
failures = []
if f'[Unreleased]: https://github.com/gimso2x/forgeflow/compare/v{version}...HEAD' not in text:
    failures.append(f'CHANGELOG.md: [Unreleased] compare link must start at v{version}')
pattern = rf'^\[{re.escape(version)}\]: https://github\.com/gimso2x/forgeflow/compare/.+\.\.\.v{re.escape(version)}$$'
if not re.search(pattern, text, re.M):
    failures.append(f'CHANGELOG.md: missing compare link for {version}')

release_heading = re.compile(r'^## \[(Unreleased|[^\]]+)\].*$', re.M)
section_heading = re.compile(r'^### (Added|Changed|Deprecated|Removed|Fixed|Security)$')
matches = list(release_heading.finditer(text))
for index, match in enumerate(matches):
    section_name = match.group(1)
    section_start = match.end()
    section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
    seen = set()
    duplicates = []
    for line in text[section_start:section_end].splitlines():
        subsection = section_heading.match(line)
        if not subsection:
            continue
        name = subsection.group(1)
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    if duplicates:
        failures.append(
            f"CHANGELOG.md: [{section_name}] has duplicate subsection headings: {', '.join(duplicates)}"
        )
if failures:
    print('ERROR: Changelog link check failed')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: Changelog release compare links are current')


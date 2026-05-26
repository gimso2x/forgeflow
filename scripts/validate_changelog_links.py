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
if failures:
    print('ERROR: Changelog link check failed')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: Changelog release compare links are current')


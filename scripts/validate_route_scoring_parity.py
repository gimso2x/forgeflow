#!/usr/bin/env python3
"""Extracted from Makefile target: validate-route-scoring-parity"""
import pathlib, sys
snippet = 'raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0'
docs = ['README.md', 'SKILL.md', 'skills/forgeflow/SKILL.md', 'skills/clarify/SKILL.md']
failures = [doc for doc in docs if snippet not in pathlib.Path(doc).read_text(encoding='utf-8')]
if failures:
    print('ERROR: Route scoring formula missing in:')
    [print(f'- {failure}') for failure in failures]
    sys.exit(1)
print('OK: Route scoring formula present in core docs')


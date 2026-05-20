.PHONY: validate validate-json validate-no-python validate-skills validate-templates validate-template-refs validate-versions validate-changelog-links validate-gemini-imports validate-plugin-prompts validate-evals-json validate-eval-files validate-workflow-vocab validate-adapter-config validate-markdown-links

PYTHON ?= python3

PLUGIN_JSON := \
	.claude-plugin/plugin.json \
	.claude-plugin/marketplace.json \
	.codex-plugin/plugin.json \
	.cursor-plugin/plugin.json \
	gemini-extension.json

TEMPLATES := \
	brief.md \
	plan.md \
	review-report.md \
	implementation-notes.md \
	eval-record.md \
	roadmap.md \
	checkpoint.md \
	run-ledger.md \
	evolution-rule.md \
	ship-summary.md

validate: validate-no-python validate-json validate-versions validate-changelog-links validate-skills validate-templates validate-template-refs validate-gemini-imports validate-plugin-prompts validate-evals-json validate-eval-files validate-workflow-vocab validate-adapter-config validate-markdown-links
	@echo "OK: local validation passed"

validate-no-python:
	@count=$$(find . -name '*.py' -not -path './.git/*' -not -path './.venv/*' | wc -l); \
	if [ "$$count" -gt 0 ]; then \
		echo "ERROR: Found $$count Python files (should be 0)"; \
		find . -name '*.py' -not -path './.git/*' -not -path './.venv/*'; \
		exit 1; \
	fi
	@echo "OK: No Python files found"

validate-json:
	@for f in $(PLUGIN_JSON); do \
		$(PYTHON) -m json.tool "$$f" >/dev/null || exit 1; \
	done
	@echo "OK: Plugin configs are valid JSON"

validate-versions:
	@expected="$$(tr -d '\n' < VERSION)"; \
	failures=""; \
	check() { \
		label="$$1"; actual="$$2"; \
		if [ "$$actual" != "$$expected" ]; then \
			failures="$${failures}- $$label: expected $$expected, got $${actual:-<missing>}\n"; \
		fi; \
	}; \
	check "SKILL.md" "$$($(PYTHON) -c 'import pathlib; print(next((line.split(":", 1)[1].strip().strip("\"'"'"'") for line in pathlib.Path("SKILL.md").read_text(encoding="utf-8").splitlines() if line.startswith("version:")), ""))')"; \
	for f in .claude-plugin/plugin.json .codex-plugin/plugin.json .cursor-plugin/plugin.json gemini-extension.json; do \
		check "$$f" "$$($(PYTHON) -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("version", ""))' "$$f")"; \
	done; \
	check ".claude-plugin/marketplace.json metadata.version" "$$($(PYTHON) -c 'import json; print(json.load(open(".claude-plugin/marketplace.json", encoding="utf-8")).get("metadata", {}).get("version", ""))')"; \
	grep -F "## [$$expected]" CHANGELOG.md >/dev/null || failures="$${failures}- CHANGELOG.md: missing ## [$$expected] section\n"; \
	if grep -F "현재 릴리즈:" README.md >/dev/null; then failures="$${failures}- README.md: remove hardcoded current release line\n"; fi; \
	grep -F "VERSION" README.md >/dev/null || failures="$${failures}- README.md: release policy must reference VERSION\n"; \
	if [ -n "$$failures" ]; then \
		printf 'ERROR: Version consistency check failed\n%b' "$$failures"; \
		exit 1; \
	fi; \
	printf 'OK: Release versions match VERSION=%s\n' "$$expected"

validate-changelog-links:
	@$(PYTHON) -c "exec("'"'"import pathlib, re, sys\nversion = pathlib.Path('VERSION').read_text(encoding='utf-8').strip()\ntext = pathlib.Path('CHANGELOG.md').read_text(encoding='utf-8')\nfailures = []\nif f'[Unreleased]: https://github.com/gimso2x/forgeflow/compare/v{version}...HEAD' not in text:\n    failures.append(f'CHANGELOG.md: [Unreleased] compare link must start at v{version}')\npattern = rf'^\\[{re.escape(version)}\\]: https://github\\.com/gimso2x/forgeflow/compare/.+\\.\\.\\.v{re.escape(version)}$$'\nif not re.search(pattern, text, re.M):\n    failures.append(f'CHANGELOG.md: missing compare link for {version}')\nif failures:\n    print('ERROR: Changelog link check failed')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: Changelog release compare links are current')\n"'"'")"

validate-skills:
	@for dir in skills/*/; do \
		name=$$(basename "$$dir"); \
		case "$$name" in _*) continue ;; esac; \
		skill_file="$${dir}SKILL.md"; \
		if [ ! -f "$$skill_file" ]; then \
			echo "ERROR: Missing SKILL.md in $$dir"; \
			exit 1; \
		fi; \
		actual="$$( $(PYTHON) -c 'import pathlib, sys; lines=pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines(); print(next((line.split(":", 1)[1].strip().strip("\"'"'"'") for line in lines if line.startswith("name:")), ""))' "$$skill_file" )"; \
		if [ "$$actual" != "$$name" ]; then \
			echo "ERROR: $$skill_file name must be $$name (got $${actual:-<missing>})"; \
			exit 1; \
		fi; \
		if ! grep -Eq '^description: .+' "$$skill_file"; then \
			echo "ERROR: $$skill_file must define a non-empty description in frontmatter"; \
			exit 1; \
		fi; \
		if ! grep -Fxq 'validate_prompt: |' "$$skill_file"; then \
			echo "ERROR: $$skill_file must define validate_prompt: | in frontmatter"; \
			exit 1; \
		fi; \
	done
	@$(PYTHON) -c 'import pathlib, re, sys; root = pathlib.Path("skills"); inventory = (root / "SKILLS.md").read_text(encoding="utf-8"); active = sorted(d.name for d in root.iterdir() if d.is_dir() and not d.name.startswith("_")); targets = re.findall(r"\(([^)]+/SKILL\.md)\)", inventory); linked_names = sorted(pathlib.PurePosixPath(target).parts[0] for target in targets if (root / target).exists()); missing = sorted(set(active) - set(linked_names)); stale = sorted(target for target in targets if not (root / target).exists() or pathlib.PurePosixPath(target).parts[0] not in active); (print("ERROR: skills/SKILLS.md inventory drift") or print(f"- missing active skills: {missing}") or print(f"- stale skill links: {stale}") or sys.exit(1)) if (missing or stale) else print(f"OK: skills/SKILLS.md lists {len(active)} active skills")'
	@echo "OK: All public skills have SKILL.md with name, description, validate_prompt, and inventory coverage"

validate-templates:
	@for t in $(TEMPLATES); do \
		if [ ! -f "templates/$$t" ]; then \
			echo "ERROR: Missing template templates/$$t"; \
			exit 1; \
		fi; \
	done
	@echo "OK: All templates exist"

validate-template-refs:
	@$(PYTHON) -c "exec("'"'"import pathlib, re, sys\nroot = pathlib.Path('.')\nrefs = set()\nfor skill_md in (root / 'skills').glob('*/SKILL.md'):\n    text = skill_md.read_text(encoding='utf-8')\n    for match in re.finditer(r'templates/([a-zA-Z0-9_-]+\\.md)', text):\n        refs.add(match.group(1))\nmissing = sorted(t for t in refs if not (root / 'templates' / t).exists())\nif missing:\n    print('ERROR: Missing template files referenced by skills:')\n    [print(f'- {item}') for item in missing]\n    sys.exit(1)\nprint(f'OK: {len(refs)} template references resolve')\n"'"'")"

validate-gemini-imports:
	@$(PYTHON) -c "exec("'"'"import json, pathlib, re, sys\nroot = pathlib.Path('.')\ngemini = (root / 'GEMINI.md').read_text(encoding='utf-8')\nimports = re.findall(r'@(\\./skills/[^\\s]+)', gemini)\nimported_paths = set(imports)\nfailures = []\nmanifest = json.loads((root / 'gemini-extension.json').read_text(encoding='utf-8'))\nif manifest.get('contextFileName') != 'GEMINI.md':\n    failures.append('gemini-extension.json: contextFileName must be GEMINI.md')\nif './skills/SKILLS.md' not in imported_paths:\n    failures.append('GEMINI.md: missing @./skills/SKILLS.md inventory import')\nactive_skills = {d.name for d in (root / 'skills').iterdir() if d.is_dir() and not d.name.startswith('_')}\nexpected_imports = {f'./skills/{name}/SKILL.md' for name in active_skills}\nmissing_active = sorted(expected_imports - imported_paths)\nstale_active = sorted(p for p in imported_paths if p.startswith('./skills/') and p.endswith('/SKILL.md') and p not in expected_imports)\nmissing_files = [p for p in imports if not (root / p.lstrip('./')).exists()]\nif missing_active:\n    failures.append(f'GEMINI.md: missing active skill imports {missing_active}')\nif stale_active:\n    failures.append(f'GEMINI.md: imports stale skill paths {stale_active}')\nfor item in missing_files:\n    failures.append(f'GEMINI.md: broken import {item}')\nif failures:\n    print('ERROR: Gemini extension import contract failed')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint(f'OK: GEMINI.md imports inventory and {len(active_skills)} active skills')\n"'"'")"

validate-plugin-prompts:
	@$(PYTHON) -c "exec("'"'"import json, pathlib, sys\nroot = pathlib.Path('.')\nactive = {p.name for p in (root / 'skills').iterdir() if p.is_dir() and not p.name.startswith('_')}\nfiles = [root / '.codex-plugin/plugin.json', root / '.cursor-plugin/plugin.json']\nfailures = []\nfor path in files:\n    data = json.loads(path.read_text(encoding='utf-8'))\n    prompts = data.get('interface', {}).get('defaultPrompt', [])\n    if not isinstance(prompts, list) or not prompts:\n        failures.append(f'{path}: interface.defaultPrompt must be a non-empty list')\n        continue\n    seen = set()\n    for prompt in prompts:\n        if not isinstance(prompt, str) or not prompt.startswith('/'):\n            failures.append(f'{path}: defaultPrompt entry must be a slash command: {prompt!r}')\n            continue\n        command = prompt.split()[0].split(':')[-1].lstrip('/')\n        if command == 'init':\n            failures.append(f'{path}: use /forgeflow-init, not /init')\n        if command not in active:\n            failures.append(f'{path}: defaultPrompt {prompt!r} does not map to an active skill')\n        if command in seen:\n            failures.append(f'{path}: duplicate defaultPrompt command {command!r}')\n        seen.add(command)\nif failures:\n    print('ERROR: Plugin defaultPrompt contract failed')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: Plugin defaultPrompt entries map to active skills')\n"'"'")"

validate-evals-json:
	@$(PYTHON) -c "exec("'"'"import json, pathlib, sys\ndata = json.loads(pathlib.Path('evals/evals.json').read_text(encoding='utf-8'))\nfailures = []\nallowed_assertion_types = {'contains', 'contains_all', 'contains_any', 'not_contains', 'not_contains_any'}\nif not isinstance(data.get('skill_name'), str):\n    failures.append('skill_name missing')\nevals = data.get('evals')\nif not isinstance(evals, list) or not evals:\n    failures.append('evals must be non-empty list')\nelse:\n    ids = [item.get('id') for item in evals if isinstance(item, dict)]\n    names = [item.get('name') for item in evals if isinstance(item, dict)]\n    expected_ids = list(range(len(evals)))\n    if not all(isinstance(item.get('id'), int) and not isinstance(item.get('id'), bool) for item in evals if isinstance(item, dict)):\n        failures.append('eval ids must be integers, not strings or booleans')\n    if ids != expected_ids:\n        failures.append(f'eval ids must be sequential starting at 0: expected {expected_ids}, got {ids}')\n    duplicate_names = sorted({name for name in names if isinstance(name, str) and names.count(name) > 1})\n    if duplicate_names:\n        failures.append(f'eval names must be unique: duplicates {duplicate_names}')\n    for i, item in enumerate(evals):\n        if not isinstance(item, dict):\n            failures.append(f'eval[{i}] must be object')\n            continue\n        for key in ('id', 'name', 'prompt', 'expected_output', 'files', 'assertions'):\n            if key not in item:\n                failures.append(f'eval[{i}] missing {key}')\n        for key in ('name', 'prompt', 'expected_output'):\n            if key in item and (not isinstance(item.get(key), str) or not item.get(key).strip()):\n                failures.append(f'eval[{i}] {key} must be a non-empty string')\n        files = item.get('files')\n        if not isinstance(files, list) or not all(isinstance(path, str) for path in files):\n            failures.append(f'eval[{i}] files must be a list of strings')\n        assertions = item.get('assertions')\n        if not isinstance(assertions, list) or not assertions:\n            failures.append(f'eval[{i}] assertions must be non-empty list')\n            continue\n        for j, assertion in enumerate(assertions):\n            if not isinstance(assertion, dict):\n                failures.append(f'eval[{i}].assertions[{j}] must be object')\n                continue\n            assertion_type = assertion.get('type')\n            if not isinstance(assertion.get('text'), str) or not assertion.get('text', '').strip():\n                failures.append(f'eval[{i}].assertions[{j}] must include non-empty text')\n            if assertion_type not in allowed_assertion_types:\n                failures.append(f'eval[{i}].assertions[{j}] unknown type {assertion_type!r}')\n            if assertion_type in {'contains', 'not_contains'}:\n                if 'values' in assertion:\n                    failures.append(f'eval[{i}].assertions[{j}] uses value, not values, for {assertion_type}')\n                if not isinstance(assertion.get('value'), str) or not assertion.get('value'):\n                    failures.append(f'eval[{i}].assertions[{j}] must include non-empty string value')\n            elif assertion_type in {'contains_all', 'contains_any', 'not_contains_any'}:\n                if 'value' in assertion:\n                    failures.append(f'eval[{i}].assertions[{j}] uses values, not value, for {assertion_type}')\n                values = assertion.get('values')\n                if not isinstance(values, list) or not values or not all(isinstance(v, str) and v for v in values):\n                    failures.append(f'eval[{i}].assertions[{j}] must include non-empty string values')\nif failures:\n    print('ERROR: evals/evals.json schema invalid')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint(f'OK: evals/evals.json schema valid ({len(evals)} cases)')\n"'"'")"

validate-eval-files:
	@$(PYTHON) -c "exec("'"'"import json, pathlib, sys\nroot = pathlib.Path('.')\ndata = json.loads((root / 'evals/evals.json').read_text(encoding='utf-8'))\nfailures = []\nfor i, item in enumerate(data.get('evals', [])):\n    name = item.get('name', f'#{i}') if isinstance(item, dict) else f'#{i}'\n    entries = item.get('files', []) if isinstance(item, dict) else []\n    for raw in entries:\n        path = pathlib.PurePosixPath(raw)\n        if path.is_absolute() or '..' in path.parts:\n            failures.append(f'eval[{i}] {name}: files entry must be repo-relative and stay inside repo: {raw}')\n            continue\n        if not (root / raw).is_file():\n            failures.append(f'eval[{i}] {name}: referenced file does not exist: {raw}')\nif failures:\n    print('ERROR: eval file references failed')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: eval file references are repo-relative and resolvable')\n"'"'")"

validate-workflow-vocab:
	@$(PYTHON) -c "exec("'"'"import pathlib, sys\nfailures = []\nchecks = {pathlib.Path('skills/SKILLS.md'): ['→ init             → task workspace']}\nfor path, stale_terms in checks.items():\n    text = path.read_text(encoding='utf-8')\n    for stale in stale_terms:\n        if stale in text:\n            failures.append(f'{path}: use forgeflow-init for user-facing workflow bootstrap, not init')\nreadme = pathlib.Path('README.md').read_text(encoding='utf-8')\nfirst_run_marker = '## 첫 실행 예시'\nfirst_run = readme.split(first_run_marker, 1)[1] if first_run_marker in readme else ''\nif '> /forgeflow-init' not in first_run:\n    failures.append('README.md: first-run example must start with /forgeflow-init before clarify')\nfor needle in ('plugin cache', '--task-dir'):\n    if needle not in first_run:\n        failures.append(f'README.md: first-run example must warn about plugin cache safety and explicit task dirs (missing {needle!r})')\nfor needle in ('대상 프로젝트 루트', 'Codex plugin cache'):\n    if needle not in readme:\n        failures.append(f'README.md: Codex quickstart must warn about project-root execution and plugin-cache safety (missing {needle!r})')\nstale_route_terms = ('large_high_risk', 'medium/large')\nscan_roots = [pathlib.Path('README.md'), pathlib.Path('GEMINI.md'), pathlib.Path('SKILL.md'), pathlib.Path('AGENTS.md'), pathlib.Path('docs'), pathlib.Path('skills'), pathlib.Path('templates')]\nfor root in scan_roots:\n    paths = [root] if root.is_file() else sorted(root.rglob('*.md'))\n    for path in paths:\n        text = path.read_text(encoding='utf-8')\n        for stale in stale_route_terms:\n            if stale in text:\n                failures.append(f'{path}: stale route vocabulary {stale!r}; use small/medium/high/epic')\nif failures:\n    print('ERROR: Workflow vocabulary drift found')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: Workflow examples use forgeflow-init and current route vocabulary')\n"'"'")"

validate-adapter-config:
	@$(PYTHON) -c "exec("'"'"import pathlib, sys\ntext = pathlib.Path('docs/adapter-config.md').read_text(encoding='utf-8')\nrequired = {\n    'Claude Code': ['claude -p', '--dangerously-skip-permissions', 'CLAUDE_CODE_SESSION=1'],\n    'Codex CLI': ['codex exec', 'danger-full-access', 'CODEX_SESSION=1'],\n    'Gemini CLI': ['gemini -p', '--yolo', '--skip-trust', 'GEMINI_CLI=1'],\n    'Cursor': ['~/.cursor/plugins/local/forgeflow', '/clarify', '<workspace>/.forgeflow/tasks/<task-id>/'],\n}\nfailures = []\nfor adapter, needles in required.items():\n    if f'### {adapter}' not in text:\n        failures.append(f'docs/adapter-config.md: missing section ### {adapter}')\n    for needle in needles:\n        if needle not in text:\n            failures.append(f'docs/adapter-config.md: {adapter} missing {needle!r}')\nroute_labels = ('small', 'medium', 'high', 'epic')\nfor label in route_labels:\n    if f'| {label} |' not in text:\n        failures.append(f'docs/adapter-config.md: timeout table missing route {label!r}')\nif failures:\n    print('ERROR: Adapter config contract failed')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: Adapter config covers CLI flags, env signals, and route timeouts')\n"'"'")"

validate-markdown-links:
	@$(PYTHON) -c "exec("'"'"import pathlib, re, sys, urllib.parse\nroot = pathlib.Path('.')\nfailures = []\nfor path in sorted(root.rglob('*.md')):\n    if '.git' in path.parts or '.venv' in path.parts:\n        continue\n    text = path.read_text(encoding='utf-8')\n    for match in re.finditer(r'(?<!!)\\[[^\\]]+\\]\\(([^)]+)\\)', text):\n        raw = match.group(1).strip()\n        target = raw.split('#', 1)[0].strip()\n        if not target or '://' in target or target.startswith(('mailto:', 'tel:')):\n            continue\n        parsed = urllib.parse.urlparse(target)\n        if parsed.scheme:\n            continue\n        candidate = (path.parent / urllib.parse.unquote(target)).resolve()\n        try:\n            candidate.relative_to(root.resolve())\n        except ValueError:\n            pass\n        if not candidate.exists():\n            failures.append(f'{path}:{match.start(1)} broken markdown link -> {raw}')\nif failures:\n    print('ERROR: Broken markdown links found')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: Markdown relative links resolve')\n"'"'")"

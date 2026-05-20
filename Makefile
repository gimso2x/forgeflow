.PHONY: validate demo validate-demo validate-json validate-no-python validate-skills validate-agent-docs validate-templates validate-template-refs validate-versions validate-changelog-links validate-route-scoring-parity validate-gemini-imports validate-plugin-prompts validate-evals-json validate-eval-files validate-workflow-vocab validate-finish-safety validate-adapter-config validate-oh-my-agent-contract validate-markdown-links

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

validate: validate-no-python validate-json validate-versions validate-changelog-links validate-route-scoring-parity validate-skills validate-agent-docs validate-templates validate-template-refs validate-demo validate-gemini-imports validate-plugin-prompts validate-evals-json validate-eval-files validate-workflow-vocab validate-finish-safety validate-adapter-config validate-oh-my-agent-contract validate-markdown-links
	@echo "OK: local validation passed"

demo:
	@tmp="$$(mktemp -d)"; \
	task_dir="$$tmp/.forgeflow/tasks/demo-small"; \
	mkdir -p "$$task_dir"; \
	cp templates/brief.md "$$task_dir/brief.md"; \
	cp templates/plan.md "$$task_dir/plan.md"; \
	cp templates/run-ledger.md "$$task_dir/run-ledger.md"; \
	cp templates/checkpoint.md "$$task_dir/checkpoint.md"; \
	cp templates/implementation-notes.md "$$task_dir/implementation-notes.md"; \
	cp templates/review-report.md "$$task_dir/review-report.md"; \
	cp templates/ship-summary.md "$$task_dir/ship-summary.md"; \
	printf 'ForgeFlow demo workspace: %s\n' "$$tmp"; \
	printf 'Mode: local template/artifact smoke only (not provider/plugin E2E).\n'; \
	printf 'Task artifacts:\n'; \
	find "$$task_dir" -maxdepth 1 -type f | sort; \
	printf '\nNext: open the temp workspace and run /forgeflow-init, then /forgeflow:clarify for a real task.\n'

validate-demo:
	@tmp="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmp"' EXIT; \
	task_dir="$$tmp/.forgeflow/tasks/demo-small"; \
	mkdir -p "$$task_dir"; \
	for artifact in brief.md plan.md run-ledger.md checkpoint.md implementation-notes.md review-report.md ship-summary.md; do \
		cp "templates/$$artifact" "$$task_dir/$$artifact"; \
		test -s "$$task_dir/$$artifact" || { echo "ERROR: demo artifact missing or empty: $$artifact"; exit 1; }; \
		grep -Fq "$$artifact" README.md || { echo "ERROR: README first-run demo docs must mention $$artifact"; exit 1; }; \
	done; \
	grep -Fq "make demo" README.md || { echo "ERROR: README must document make demo"; exit 1; }; \
	grep -Fq ".forgeflow/tasks/demo-small/" README.md || { echo "ERROR: README must document demo task path"; exit 1; }; \
	grep -Fq "not provider/plugin E2E" Makefile || { echo "ERROR: make demo output must not overclaim provider/plugin E2E"; exit 1; }; \
	count="$$(find "$$task_dir" -maxdepth 1 -type f | wc -l)"; \
	if [ "$$count" -ne 7 ]; then \
		echo "ERROR: demo workspace expected 7 artifacts, got $$count"; \
		exit 1; \
	fi
	@echo "OK: demo workspace creates and documents first-run artifacts"

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

validate-route-scoring-parity:
	@$(PYTHON) -c "exec("'"'"import pathlib, sys\nsnippet = 'raw_score = file_count*1.0 + estimated_lines*0.1 + requirement_count*2.0 + dependency_count*1.5 + risk_keywords*3.0'\ndocs = ['README.md', 'SKILL.md', 'skills/forgeflow/SKILL.md', 'skills/clarify/SKILL.md']\nfailures = [doc for doc in docs if snippet not in pathlib.Path(doc).read_text(encoding='utf-8')]\nif failures:\n    print('ERROR: Route scoring formula missing in:')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: Route scoring formula present in core docs')\n"'"'")"

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

validate-agent-docs:
	@$(PYTHON) -c "exec("'"'"import pathlib, re, sys\nroot = pathlib.Path('.')\nagents = (root / 'AGENTS.md').read_text(encoding='utf-8')\nactive = sorted(d.name for d in (root / 'skills').iterdir() if d.is_dir() and not d.name.startswith('_'))\nlisted = sorted(set(re.findall(r'^  ([a-z0-9-]+)/\\s+#', agents, re.M)))\nmissing = sorted(set(active) - set(listed))\nstale = sorted(set(listed) - set(active))\nfailures = []\nif missing:\n    failures.append(f'AGENTS.md: missing active skill directories {missing}')\nif stale:\n    failures.append(f'AGENTS.md: lists stale skill directories {stale}')\nfor required in ('외부 의존성 추가 금지', 'Review는 읽기 전용'):\n    if required not in agents:\n        failures.append(f'AGENTS.md: missing maintainer guardrail {required!r}')\nif 'VERSION' not in agents or '단일 소스' not in agents:\n    failures.append('AGENTS.md: missing maintainer guardrail for VERSION single source')\nif failures:\n    print('ERROR: AGENTS.md contract drift')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint(f'OK: AGENTS.md lists {len(active)} active skills and maintainer guardrails')\n"'"'")"
	@grep -Fq ".gemini/extensions" skills/_shared/discipline.md || { echo "ERROR: shared discipline must protect Gemini extension cache paths"; exit 1; }
	@grep -Fq ".gemini/extensions" skills/forgeflow-init/SKILL.md || { echo "ERROR: forgeflow-init must protect Gemini extension cache paths"; exit 1; }

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
	@$(PYTHON) -c "exec("'"'"import json, pathlib, subprocess, sys\nroot = pathlib.Path('.')\ntracked = set(subprocess.check_output(['git', 'ls-files'], text=True).splitlines())\ndata = json.loads((root / 'evals/evals.json').read_text(encoding='utf-8'))\nfailures = []\nfor i, item in enumerate(data.get('evals', [])):\n    name = item.get('name', f'#{i}') if isinstance(item, dict) else f'#{i}'\n    entries = item.get('files', []) if isinstance(item, dict) else []\n    for raw in entries:\n        path = pathlib.PurePosixPath(raw)\n        if path.is_absolute() or '..' in path.parts:\n            failures.append(f'eval[{i}] {name}: files entry must be repo-relative and stay inside repo: {raw}')\n            continue\n        if not (root / raw).is_file():\n            failures.append(f'eval[{i}] {name}: referenced file does not exist: {raw}')\n            continue\n        if raw not in tracked:\n            failures.append(f'eval[{i}] {name}: referenced file must be tracked by git: {raw}')\nfor report in sorted((root / 'evals' / 'results').glob('**/review-report.md')):\n    text = report.read_text(encoding='utf-8')\n    if '<!--' in text or '-->' in text:\n        failures.append(f'{report}: persisted eval review reports must be concrete audit output, not unresolved template placeholders')\n    for heading in ('## Verdict', '## Evidence Classification', '## Next Action'):\n        if heading not in text:\n            failures.append(f'{report}: missing required concrete review heading {heading}')\nif failures:\n    print('ERROR: eval file references failed')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: eval file references are repo-relative, tracked, and resolvable')\n"'"'")"

validate-workflow-vocab:
	@$(PYTHON) -c "exec("'"'"import pathlib, sys\nfailures = []\nchecks = {pathlib.Path('skills/SKILLS.md'): ['→ init             → task workspace']}\nfor path, stale_terms in checks.items():\n    text = path.read_text(encoding='utf-8')\n    for stale in stale_terms:\n        if stale in text:\n            failures.append(f'{path}: use forgeflow-init for user-facing workflow bootstrap, not init')\nactive_docs = [path for path in pathlib.Path('.').rglob('*.md') if '.git' not in path.parts and '.venv' not in path.parts and path.parts[0] not in {'CHANGELOG.md', 'evals'}]\nfor path in active_docs:\n    text = path.read_text(encoding='utf-8')\n    if 'large_high_risk' in text:\n        failures.append(f'{path}: active docs must use canonical route labels small/medium/high/epic, not large_high_risk')\nreadme = pathlib.Path('README.md').read_text(encoding='utf-8')\nworkflow_marker = '## 기본 워크플로우'\nworkflow = readme.split(workflow_marker, 1)[1].split('## Routes', 1)[0] if workflow_marker in readme and '## Routes' in readme else ''\nif '/forgeflow-init' not in workflow:\n    failures.append('README.md: basic workflow must include /forgeflow-init before clarify')\nroute_section = readme.split('## Routes', 1)[1].split('### Route scoring', 1)[0] if '## Routes' in readme and '### Route scoring' in readme else ''\nfor label in ('small', 'medium', 'high', 'epic'):\n    if f'| {label}' not in route_section:\n        failures.append(f'README.md: Routes table must document canonical route {label!r}')\nfor stale in ('large_high_risk', '| low ', '| critical '):\n    if stale in route_section:\n        failures.append(f'README.md: Routes table contains stale/non-route label {stale!r}')\nfirst_run_marker = '## 첫 실행 예시'\nfirst_run = readme.split(first_run_marker, 1)[1] if first_run_marker in readme else ''\nif '> /forgeflow-init' not in first_run:\n    failures.append('README.md: first-run example must start with /forgeflow-init before clarify')\nif '> /forgeflow:plan' in first_run and 'route: small' in first_run:\n    failures.append('README.md: first-run example must not route small and then run plan; small route skips plan')\nfor needle in ('plugin cache', '--task-dir'):\n    if needle not in first_run:\n        failures.append(f'README.md: first-run example must warn about plugin cache safety and explicit task dirs (missing {needle!r})')\nfor needle in ('대상 프로젝트 루트', 'Codex plugin cache'):\n    if needle not in readme:\n        failures.append(f'README.md: Codex quickstart must warn about project-root execution and plugin-cache safety (missing {needle!r})')\nfinish = pathlib.Path('skills/finish/SKILL.md').read_text(encoding='utf-8')\nfor forbidden in ('Worktree cleanup (before verification)', 'After successful merge (or if user chose "discard")'):\n    if forbidden in finish:\n        failures.append(f'skills/finish/SKILL.md: worktree finish preflight must not imply destructive cleanup before option confirmation ({forbidden!r})')\nfor required in ('Worktree preflight (before verification)', 'Do not remove or discard yet', 'option-specific confirmation'):\n    if required not in finish:\n        failures.append(f'skills/finish/SKILL.md: missing conservative worktree finish guardrail {required!r}')\nstale_route_terms = ('large_high_risk', 'medium/large')\nstale_schema_terms = {\n    'selected_architecture': 'brief artifacts no longer expose selected_architecture',\n    'success_criteria': 'brief artifacts use acceptance_criteria',\n    'progress.percentage': 'run-state progress uses progress.percent',\n}\nscan_roots = [pathlib.Path('README.md'), pathlib.Path('GEMINI.md'), pathlib.Path('SKILL.md'), pathlib.Path('AGENTS.md'), pathlib.Path('docs'), pathlib.Path('skills'), pathlib.Path('templates')]\nfor root in scan_roots:\n    paths = [root] if root.is_file() else sorted(root.rglob('*.md'))\n    for path in paths:\n        text = path.read_text(encoding='utf-8')\n        for stale in stale_route_terms:\n            if stale in text:\n                failures.append(f'{path}: stale route vocabulary {stale!r}; use small/medium/high/epic')\n        for stale, guidance in stale_schema_terms.items():\n            if stale in text:\n                failures.append(f'{path}: stale schema vocabulary {stale!r}; {guidance}')\nif failures:\n    print('ERROR: Workflow/schema vocabulary drift found')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: Workflow examples use forgeflow-init, current route vocabulary, and current schema field names')\n"'"'")"

validate-finish-safety:
	@grep -Fq "Do not remove or discard yet" skills/finish/SKILL.md || { echo "ERROR: finish skill must preserve worktrees before option-specific confirmation"; exit 1; }
	@grep -Fq "Type 'discard' to confirm." skills/finish/SKILL.md || { echo "ERROR: finish skill must require exact discard confirmation"; exit 1; }
	@grep -Fq "Never delete unrelated dirty working tree files" skills/finish/SKILL.md || { echo "ERROR: finish skill must protect unrelated dirty working tree files"; exit 1; }
	@echo "OK: Finish skill protects worktrees and destructive cleanup"

validate-adapter-config:
	@$(PYTHON) -c "exec("'"'"import pathlib, sys\ntext = pathlib.Path('docs/adapter-config.md').read_text(encoding='utf-8')\nreadme = pathlib.Path('README.md').read_text(encoding='utf-8')\nrequired = {\n    'Claude Code': ['claude -p', '--dangerously-skip-permissions', 'CLAUDE_CODE_SESSION=1'],\n    'Codex CLI': ['codex exec', 'danger-full-access', 'CODEX_SESSION=1', '대상 프로젝트 루트', 'plugin cache'],\n    'Gemini CLI': ['gemini -p', '--yolo', '--skip-trust', 'GEMINI_CLI=1', 'gemini extensions install', 'Extension 업데이트', 'gemini extensions update forgeflow', 'gemini extensions list', 'gemini extensions validate .', 'gemini extensions link .'],\n    'Cursor': ['~/.cursor/plugins/local/forgeflow', '/clarify', '<workspace>/.forgeflow/tasks/<task-id>/'],\n}\nfailures = []\nfor adapter, needles in required.items():\n    if f'### {adapter}' not in text:\n        failures.append(f'docs/adapter-config.md: missing section ### {adapter}')\n    for needle in needles:\n        if needle not in text:\n            failures.append(f'docs/adapter-config.md: {adapter} missing {needle!r}')\nroute_labels = ('small', 'medium', 'high', 'epic')\nfor label in route_labels:\n    if f'| {label} |' not in text:\n        failures.append(f'docs/adapter-config.md: timeout table missing route {label!r}')\ngemini_update = 'printf ' + chr(39) + 'Y' + chr(92) + 'n' + chr(39) + ' ' + chr(124) + ' gemini extensions update forgeflow'\nif gemini_update not in readme:\n    failures.append('README.md: Gemini automated update example must pipe explicit Y confirmation')\nif 'gemini extensions list' not in readme:\n    failures.append('README.md: Gemini quickstart must verify extension visibility with gemini extensions list')\nfor needle in ('대상 프로젝트 루트', '.codex/plugins/forgeflow', '.codex-plugin/plugin.json', '/path/to/forgeflow/skills', '/path/to/forgeflow/templates'):\n    if needle not in readme:\n        failures.append(f'README.md: Codex quickstart must document {needle!r}')\nfor needle in ('대상 프로젝트 루트', 'plugin cache'):\n    if needle not in text:\n        failures.append(f'docs/adapter-config.md: Codex section must warn about {needle!r}')\nfor path, body in ((pathlib.Path('README.md'), readme), (pathlib.Path('docs/adapter-config.md'), text)):\n    if '--consent' in body:\n        failures.append(f'{path}: Gemini extensions update currently has no --consent flag; pipe explicit Y instead')\nif failures:\n    print('ERROR: Adapter config contract failed')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: Adapter config covers CLI flags, env signals, route timeouts, Gemini update confirmation, and extension list verification')\n"'"'")"

validate-oh-my-agent-contract:
	@$(PYTHON) -c "exec("'"'"import pathlib, re, sys\nroot = pathlib.Path('.')\nchecks = {\n    'skills/forgeflow/SKILL.md': ['intent:', 'inputs:', 'outputs:', 'dependencies:', 'docs/advisory-guidelines.md'],\n    'skills/clarify/SKILL.md': ['intent:', 'inputs:', 'outputs:', 'dependencies:', '리뷰해줘', '계획 세워', 'suggested_next_skill', 'Keyword hints are advisory'],\n    'templates/brief.md': ['## Route Rationale', '## Budget Note', '## Suggested Next Skill', 'Suggested specialists'],\n    'templates/plan.md': ['## Execution Pattern', '## Applied Evolution Rules'],\n    'docs/advisory-guidelines.md': ['Route Budget Guide', 'small:', 'medium:', 'high:', 'epic:', 'Non-goals'],\n    'docs/oh-my-agent-forgeflow-handoff.md': ['docs/advisory-guidelines.md', 'advisory only'],\n}\nfailures = []\nfor raw_path, needles in checks.items():\n    path = root / raw_path\n    if not path.is_file():\n        failures.append(f'{raw_path}: missing required file')\n        continue\n    text = path.read_text(encoding='utf-8')\n    for needle in needles:\n        if needle not in text:\n            failures.append(f'{raw_path}: missing {needle!r}')\nclarify = (root / 'skills/clarify/SKILL.md').read_text(encoding='utf-8')\nif 'auto-invoke' in clarify.lower() and 'Do not auto-invoke' not in clarify:\n    failures.append('skills/clarify/SKILL.md: alias hints must stay non-invoking/advisory')\n# \u2500\u2500 YAML frontmatter integrity \u2500\u2500\nfor sf in ['skills/forgeflow/SKILL.md', 'skills/clarify/SKILL.md']:\n    text = (root / sf).read_text(encoding='utf-8')\n    m = re.search(r'^---\\\\s*\\\\n(.*?\\\\n)---\\\\s*\\\\n', text, re.DOTALL)\n    if not m:\n        failures.append(f'{sf}: YAML frontmatter block not found')\n        continue\n    yaml_block = m.group(1)\n    for field in ('intent:', 'inputs:', 'outputs:', 'dependencies:'):\n        if field not in yaml_block:\n            failures.append(f'{sf}: field {field!r} missing inside frontmatter')\n    try:\n        {k: v for k, v in [line.split(':', 1) for line in yaml_block.strip().splitlines() if ':' in line and not line.strip().startswith('-')]}\n    except Exception as exc:\n        failures.append(f'{sf}: frontmatter parse error: {exc}')\nif failures:\n    print('ERROR: oh-my-agent absorption contract drift')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: oh-my-agent absorption metadata, alias hints, advisory docs, and YAML frontmatter integrity')\n"'"'")" 
validate-markdown-links:
	@$(PYTHON) -c "exec("'"'"import pathlib, re, sys, urllib.parse\nroot = pathlib.Path('.')\nfailures = []\nfor path in sorted(root.rglob('*.md')):\n    if '.git' in path.parts or '.venv' in path.parts:\n        continue\n    text = path.read_text(encoding='utf-8')\n    line_starts = [0]\n    for index, char in enumerate(text):\n        if char == chr(10):\n            line_starts.append(index + 1)\n    def location(offset):\n        line_no = 1\n        for index, start in enumerate(line_starts):\n            if start > offset:\n                break\n            line_no = index + 1\n        column = offset - line_starts[line_no - 1] + 1\n        return f'{path}:{line_no}:{column}'\n    for match in re.finditer(r'(?<!!)\\[[^\\]]+\\]\\(([^)]+)\\)', text):\n        raw = match.group(1).strip()\n        target = raw.split('#', 1)[0].strip()\n        if not target or '://' in target or target.startswith(('mailto:', 'tel:')):\n            continue\n        parsed = urllib.parse.urlparse(target)\n        if parsed.scheme:\n            continue\n        candidate = (path.parent / urllib.parse.unquote(target)).resolve()\n        try:\n            candidate.relative_to(root.resolve())\n        except ValueError:\n            failures.append(f'{location(match.start(1))} markdown link escapes repo -> {raw}')\n            continue\n        if not candidate.exists():\n            failures.append(f'{location(match.start(1))} broken markdown link -> {raw}')\nif failures:\n    print('ERROR: Broken markdown links found')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint('OK: Markdown relative links resolve')\n"'"'")"

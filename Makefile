.PHONY: validate validate-json validate-no-python validate-skills validate-templates validate-versions validate-gemini-imports

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

validate: validate-no-python validate-json validate-versions validate-skills validate-templates validate-gemini-imports
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
	@echo "OK: All public skills have SKILL.md with name, description, and validate_prompt"

validate-templates:
	@for t in $(TEMPLATES); do \
		if [ ! -f "templates/$$t" ]; then \
			echo "ERROR: Missing template templates/$$t"; \
			exit 1; \
		fi; \
	done
	@echo "OK: All templates exist"

validate-gemini-imports:
	@$(PYTHON) -c "exec("'"'"import json, pathlib, re, sys\nroot = pathlib.Path('.')\ngemini = (root / 'GEMINI.md').read_text(encoding='utf-8')\nimports = re.findall(r'@(\\./skills/[^\\s]+)', gemini)\nimported_paths = set(imports)\nfailures = []\nmanifest = json.loads((root / 'gemini-extension.json').read_text(encoding='utf-8'))\nif manifest.get('contextFileName') != 'GEMINI.md':\n    failures.append('gemini-extension.json: contextFileName must be GEMINI.md')\nif './skills/SKILLS.md' not in imported_paths:\n    failures.append('GEMINI.md: missing @./skills/SKILLS.md inventory import')\nactive_skills = {d.name for d in (root / 'skills').iterdir() if d.is_dir() and not d.name.startswith('_')}\nexpected_imports = {f'./skills/{name}/SKILL.md' for name in active_skills}\nmissing_active = sorted(expected_imports - imported_paths)\nstale_active = sorted(p for p in imported_paths if p.startswith('./skills/') and p.endswith('/SKILL.md') and p not in expected_imports)\nmissing_files = [p for p in imports if not (root / p.lstrip('./')).exists()]\nif missing_active:\n    failures.append(f'GEMINI.md: missing active skill imports {missing_active}')\nif stale_active:\n    failures.append(f'GEMINI.md: imports stale skill paths {stale_active}')\nfor item in missing_files:\n    failures.append(f'GEMINI.md: broken import {item}')\nif failures:\n    print('ERROR: Gemini extension import contract failed')\n    [print(f'- {failure}') for failure in failures]\n    sys.exit(1)\nprint(f'OK: GEMINI.md imports inventory and {len(active_skills)} active skills')\n"'"'")"

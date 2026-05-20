.PHONY: validate validate-json validate-no-python validate-skills validate-templates validate-versions

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

validate: validate-no-python validate-json validate-versions validate-skills validate-templates
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
	done
	@echo "OK: All public skills have SKILL.md with matching names"

validate-templates:
	@for t in $(TEMPLATES); do \
		if [ ! -f "templates/$$t" ]; then \
			echo "ERROR: Missing template templates/$$t"; \
			exit 1; \
		fi; \
	done
	@echo "OK: All templates exist"

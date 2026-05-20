.PHONY: validate validate-json validate-no-python validate-skills validate-templates

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

validate: validate-no-python validate-json validate-skills validate-templates
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

validate-skills:
	@for dir in skills/*/; do \
		name=$$(basename "$$dir"); \
		case "$$name" in _*) continue ;; esac; \
		if [ ! -f "$${dir}SKILL.md" ]; then \
			echo "ERROR: Missing SKILL.md in $$dir"; \
			exit 1; \
		fi; \
	done
	@echo "OK: All public skills have SKILL.md"

validate-templates:
	@for t in $(TEMPLATES); do \
		if [ ! -f "templates/$$t" ]; then \
			echo "ERROR: Missing template templates/$$t"; \
			exit 1; \
		fi; \
	done
	@echo "OK: All templates exist"

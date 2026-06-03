.PHONY: validate demo validate-demo install-codex-local validate-behavior-guardrails validate-json validate-no-python validate-slim-surface validate-ci-workflows validate-english-readme validate-skills validate-skill-frontmatter validate-agent-docs validate-templates validate-template-refs validate-versions validate-changelog-links validate-route-scoring-parity validate-route-policy validate-gemini-imports validate-plugin-prompts validate-evals validate-evals-json validate-eval-files validate-evals-fixtures validate-workflow-vocab validate-ship-safety validate-dogfooding-docs validate-context-resume validate-stage-tool-boundaries validate-adapter-config validate-advisory-contract validate-markdown-links telemetry telemetry-collect telemetry-aggregate usage-audit

PYTHON ?= python3

PLUGIN_JSON := \
	.agents/plugins/marketplace.json \
	.claude-plugin/plugin.json \
	.claude-plugin/marketplace.json \
	.codex-plugin/plugin.json \
	.cursor-plugin/plugin.json \
	gemini-extension.json

TEMPLATES := \
	brief.md \
	project-draft.md \
	plan.md \
	review-report.md \
	implementation-notes.md \
	input-source.md \
	normalized-input.md \
	eval-record.md \
	roadmap.md \
	checkpoint.md \
	run-state.json \
	ledger.md \
	evolution-rule.md \
	ship-summary.md \
	fact-extraction.md \
	telemetry-event.md \
	metrics-dashboard.md \
	evidence-manifest.md \
	re-execution-conditions.md

validate: validate-no-python validate-slim-surface validate-ci-workflows validate-english-readme validate-json validate-versions validate-changelog-links validate-route-scoring-parity validate-route-policy validate-skills validate-agent-docs validate-templates validate-template-refs validate-demo validate-gemini-imports validate-plugin-prompts validate-evals validate-workflow-vocab validate-ship-safety validate-dogfooding-docs validate-context-resume validate-stage-tool-boundaries validate-adapter-config validate-advisory-contract validate-behavior-guardrails validate-markdown-links
	@echo "OK: local validation passed"

validate-evals: validate-evals-json validate-eval-files validate-evals-fixtures
	@echo "OK: eval fixture validation bundle passed"

CODEX_LOCAL_PLUGIN_DIR ?= .codex/plugins/forgeflow

install-codex-local:
	@set -eu; \
	dest="$${CODEX_LOCAL_PLUGIN_DIR:-$(CODEX_LOCAL_PLUGIN_DIR)}"; \
	rm -rf "$$dest"; \
	mkdir -p "$$dest"; \
	cp -a .codex-plugin/plugin.json skills templates "$$dest"; \
	printf 'Installed ForgeFlow Codex local plugin to %s\n' "$$dest"; \
	printf 'Run from the target project root, then restart Codex App/CLI session if needed.\n'

demo:
	@tmp="$$(mktemp -d)"; \
	task_dir="$$tmp/.forgeflow/tasks/demo-small"; \
	mkdir -p "$$task_dir"; \
	cp templates/brief.md "$$task_dir/brief.md"; \
	cp templates/plan.md "$$task_dir/plan.md"; \
	cp templates/ledger.md "$$task_dir/ledger.md"; \
	cp templates/checkpoint.md "$$task_dir/checkpoint.md"; \
	cp templates/run-state.json "$$task_dir/run-state.json"; \
	cp templates/implementation-notes.md "$$task_dir/implementation-notes.md"; \
	cp templates/review-report.md "$$task_dir/review-report.md"; \
	cp templates/ship-summary.md "$$task_dir/ship-summary.md"; \
	printf 'ForgeFlow demo workspace: %s\n' "$$tmp"; \
	printf 'Mode: local template/artifact smoke only (not provider/plugin E2E).\n'; \
	printf 'Task artifacts:\n'; \
	find "$$task_dir" -maxdepth 1 -type f | sort; \
	printf '\nNext: open the temp workspace and run /forgeflow:clarify for a real task.\n'

validate-demo:
	@tmp="$$(mktemp -d)"; \
	trap 'rm -rf "$$tmp"' EXIT; \
	task_dir="$$tmp/.forgeflow/tasks/demo-small"; \
	mkdir -p "$$task_dir"; \
	for artifact in brief.md plan.md ledger.md checkpoint.md run-state.json implementation-notes.md review-report.md ship-summary.md; do \
		cp "templates/$$artifact" "$$task_dir/$$artifact"; \
		test -s "$$task_dir/$$artifact" || { echo "ERROR: demo artifact missing or empty: $$artifact"; exit 1; }; \
		grep -Fq "$$artifact" README.md || { echo "ERROR: README first-run demo docs must mention $$artifact"; exit 1; }; \
	done; \
	grep -Fq "make demo" README.md || { echo "ERROR: README must document make demo"; exit 1; }; \
	grep -Fq "make validate-demo" README.md || { echo "ERROR: README must document focused demo validation target"; exit 1; }; \
	grep -Fq ".forgeflow/tasks/demo-small/" README.md || { echo "ERROR: README must document demo task path"; exit 1; }; \
	grep -Fq "실제 provider/plugin E2E가 아니라" README.md || { echo "ERROR: README first-run demo docs must not overclaim provider/plugin E2E"; exit 1; }; \
	grep -Fq "live provider/plugin E2E를 실행하지 않습니다" README.md || { echo "ERROR: README local validation docs must not overclaim provider/plugin E2E"; exit 1; }; \
	grep -Fq "추적 파일을 수정하지 않으므로" README.md || { echo "ERROR: README demo docs must state repo-local artifacts are not mutated"; exit 1; }; \
	grep -Fq "not provider/plugin E2E" Makefile || { echo "ERROR: make demo output must not overclaim provider/plugin E2E"; exit 1; }; \
	count="$$(find "$$task_dir" -maxdepth 1 -type f | wc -l)"; \
	if [ "$$count" -ne 8 ]; then \
		echo "ERROR: demo workspace expected 8 artifacts, got $$count"; \
		exit 1; \
	fi
	@echo "OK: demo workspace creates and documents first-run artifacts"

validate-no-python:
	@count=$$(find . -name '*.py' -not -path './.git/*' -not -path './.venv/*' -not -path './scripts/*' | wc -l); \
	if [ "$$count" -gt 0 ]; then \
		echo "ERROR: Found $$count Python files outside scripts/ (should be 0)"; \
		find . -name '*.py' -not -path './.git/*' -not -path './.venv/*' -not -path './scripts/*'; \
		exit 1; \
	fi
	@echo "OK: No Python files found outside scripts/"


validate-slim-surface:
	@tracked_legacy="$$(git ls-files 'forgeflow_runtime/**' 'schemas/**' 'tests/**')"; \
	if [ -n "$$tracked_legacy" ]; then \
		echo "ERROR: v1.x slim surface must not track legacy runtime/schema/test paths"; \
		printf '%s\n' "$$tracked_legacy"; \
		exit 1; \
	fi
	@matches="$$(git grep -nE 'forgeflow_runtime/|schemas/|tests/runtime|`tests/`' -- '*.md' ':!AGENTS.md' ':!CHANGELOG.md' || true)"; \
	if [ -n "$$matches" ]; then \
		echo "ERROR: Active v1.x docs must not reference removed runtime/schema/test trees"; \
		printf '%s\n' "$$matches"; \
		exit 1; \
	fi
	@grep -Fq "make validate-slim-surface" README.md || { echo "ERROR: README local validation docs must include focused slim-surface validation"; exit 1; }
	@grep -Fq "tracked legacy runtime/schema/test directories are absent" README.md || { echo "ERROR: README local validation docs must mention slim-surface tracked directory absence"; exit 1; }
	@echo "OK: Slim surface has no legacy runtime/schema/test directories or active-doc references"

validate-ci-workflows:
	@grep -Fq "run: make validate" .github/workflows/validate.yml || { echo "ERROR: validate workflow must run make validate"; exit 1; }
	@grep -Fq "run: make validate-evals" .github/workflows/evals.yml || { echo "ERROR: evals workflow must run the documented eval fixture bundle"; exit 1; }
	@grep -Fq "permissions:" .github/workflows/validate.yml || { echo "ERROR: validate workflow must declare minimal permissions"; exit 1; }
	@grep -Fq "permissions:" .github/workflows/evals.yml || { echo "ERROR: evals workflow must declare minimal permissions"; exit 1; }
	@grep -Fq "contents: read" .github/workflows/validate.yml || { echo "ERROR: validate workflow must use read-only contents permission"; exit 1; }
	@grep -Fq "contents: read" .github/workflows/evals.yml || { echo "ERROR: evals workflow must use read-only contents permission"; exit 1; }
	@grep -Fq ".github/workflows/validate.yml" README.md || { echo "ERROR: README must document validate workflow location"; exit 1; }
	@grep -Fq ".github/workflows/evals.yml" README.md || { echo "ERROR: README must document evals workflow location"; exit 1; }
	@grep -Fq "read-only \`contents: read\` permissions" README.md || { echo "ERROR: README must document CI workflows use minimal read-only permissions"; exit 1; }
	@grep -Fq "make validate-evals" README.md || { echo "ERROR: README must document the eval validation bundle target"; exit 1; }
	@grep -Fq "make validate-evals" evals/README.md || { echo "ERROR: eval README must document the eval validation bundle target"; exit 1; }
	@echo "OK: CI workflows invoke documented local validation bundles"

validate-english-readme:
	@grep -Fq "The canonical detailed README is [README.md](README.md)" README_en.md || { echo "ERROR: README_en must point to the canonical detailed README"; exit 1; }
	@grep -Fq "Claude Code, Codex, Gemini CLI, and Cursor" README_en.md || { echo "ERROR: README_en must name the supported adapters"; exit 1; }
	@grep -Fq "gemini extensions install https://github.com/gimso2x/forgeflow" README_en.md || { echo "ERROR: README_en must document Gemini CLI install"; exit 1; }
	@grep -Fq "codex plugin add forgeflow@forgeflow" README_en.md || { echo "ERROR: README_en must document Codex marketplace install"; exit 1; }
	@grep -Fq "make -C /path/to/forgeflow install-codex-local" README_en.md || { echo "ERROR: README_en must document Codex local install target"; exit 1; }
	@grep -Fq "~/.forgeflow/projects/<project-slug>/tasks/<task-id>/" README_en.md || { echo "ERROR: README_en must document the default global artifact path"; exit 1; }
	@grep -Fq "make validate" README_en.md || { echo "ERROR: README_en must document make validate"; exit 1; }
	@grep -Fq "make validate-evals" README_en.md || { echo "ERROR: README_en must document make validate-evals"; exit 1; }
	@grep -Fq "make validate-behavior-guardrails" README_en.md || { echo "ERROR: README_en must document focused behavior guardrail validation"; exit 1; }
	@grep -Fq "assumption-risk" README_en.md || { echo "ERROR: README_en must document behavior guardrail review findings"; exit 1; }
	@grep -Fq "read-only \`contents: read\` permissions" README_en.md || { echo "ERROR: README_en must document read-only CI permissions"; exit 1; }
	@grep -Fq "make validate-english-readme" README.md || { echo "ERROR: README local validation docs must include focused English README validation"; exit 1; }
	@echo "OK: English README mirrors core install, artifact, and validation surfaces"

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
	if grep -E "^(현재 릴리즈|Current release):" README.md >/dev/null; then failures="$${failures}- README.md: remove hardcoded current release line\n"; fi; \
	grep -F "VERSION" README.md >/dev/null || failures="$${failures}- README.md: release policy must reference VERSION\n"; \
	if [ -n "$$failures" ]; then \
		printf 'ERROR: Version consistency check failed\n%b' "$$failures"; \
		exit 1; \
	fi; \
	printf 'OK: Release versions match VERSION=%s\n' "$$expected"

validate-changelog-links:
	@$(PYTHON) scripts/validate_changelog_links.py
	@grep -Fq "make validate-versions validate-changelog-links" README.md || { echo "ERROR: README local validation docs must include focused release/version validation bundle"; exit 1; }

validate-route-scoring-parity:
	@$(PYTHON) scripts/validate_route_scoring_parity.py
	@grep -Fq "make validate-route-scoring-parity" README.md || { echo "ERROR: README local validation docs must include focused route-scoring parity validation"; exit 1; }

validate-route-policy:
	@$(PYTHON) scripts/validate_route_policy.py

validate-skill-frontmatter:
	@bash scripts/validate-skill-frontmatter.sh

validate-skills: validate-skill-frontmatter
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
	@grep -Fq "skills/forgeflow/SKILL.md" SKILL.md || { echo "ERROR: root SKILL.md must point to the canonical forgeflow skill"; exit 1; }
	@grep -Fq "Claude marketplace entry" SKILL.md || { echo "ERROR: root SKILL.md must stay a marketplace summary, not the canonical contract"; exit 1; }
	@grep -Fq "make validate-skills" README.md || { echo "ERROR: README local validation docs must include focused skills validation"; exit 1; }
	@grep -Fq "root SKILL.md marketplace summary" README.md || { echo "ERROR: README local validation docs must mention root SKILL marketplace summary coverage"; exit 1; }
	@echo "OK: All public skills have SKILL.md with name, description, validate_prompt, inventory coverage, and root marketplace summary linkage"

validate-agent-docs:
	@$(PYTHON) scripts/validate_agent_docs.py
	@grep -Fq ".gemini/extensions" skills/_shared/discipline.md || { echo "ERROR: shared discipline must protect Gemini extension cache paths"; exit 1; }
	@grep -Fq ".gemini/extensions" skills/clarify/SKILL.md || { echo "ERROR: clarify must protect Gemini extension cache paths"; exit 1; }
	@grep -Fq "git status --short --branch" skills/_shared/preflight.md || { echo "ERROR: preflight must inspect git branch/ahead-behind status before maintainer mutations"; exit 1; }
	@grep -Fq "git branch --show-current" skills/_shared/preflight.md || { echo "ERROR: preflight must use an explicit branch command before maintainer mutations"; exit 1; }
	@grep -Fq "confirm the current branch is the expected target branch" skills/_shared/preflight.md || { echo "ERROR: preflight must confirm the expected target branch before maintainer mutations"; exit 1; }
	@grep -Fq "If the branch is not the configured target branch" skills/_shared/preflight.md || { echo "ERROR: preflight must stop on wrong branch before pull/edit/commit/push"; exit 1; }
	@grep -Fq "git pull --ff-only" skills/_shared/preflight.md || { echo "ERROR: preflight must document ff-only refresh after clean status"; exit 1; }
	@grep -Fq "Re-read \`AGENTS.md\` after the pull" skills/_shared/preflight.md || { echo "ERROR: preflight must re-read AGENTS.md after ff-only refresh"; exit 1; }
	@grep -Fq "Shared preflight procedure for maintainer automation" skills/_shared/preflight.md || { echo "ERROR: preflight overview must cover maintainer automation"; exit 1; }
	@grep -Fq "then immediately rerun \`git status --short\`" skills/_shared/preflight.md || { echo "ERROR: preflight must re-check dirty status after ff-only refresh"; exit 1; }
	@grep -Fq "Report the dirty paths as user/unknown changes" skills/_shared/preflight.md || { echo "ERROR: preflight must stop and report unknown dirty paths"; exit 1; }
	@grep -Fq "rerun \`git status --short\` before staging" skills/_shared/preflight.md || { echo "ERROR: preflight must re-check dirty status before staging intentional files"; exit 1; }
	@grep -Fq "Stage only the files you intentionally changed in this run" skills/_shared/preflight.md || { echo "ERROR: preflight must stage only intentional current-run files"; exit 1; }
	@grep -Fq "After commit and push, rerun \`git status --short\`" skills/_shared/preflight.md || { echo "ERROR: preflight must re-check dirty status after push before reporting clean"; exit 1; }
	@grep -Fq "git push origin HEAD:refs/heads/main" skills/_shared/preflight.md || { echo "ERROR: preflight must document explicit branch push to avoid branch/tag collisions"; exit 1; }
	@grep -Fq "Do not schedule jobs, modify cron/crontab, or change external automation" skills/_shared/preflight.md || { echo "ERROR: preflight must keep scheduled-run cadence changes operator-owned"; exit 1; }
	@grep -Fq "Never run broad cleanup commands such as \`git clean -fdX\`" skills/_shared/preflight.md || { echo "ERROR: preflight must forbid broad destructive cleanup in scheduled maintainer runs"; exit 1; }
	@grep -Fq "inspect \`git status --short --ignored\` first" skills/_shared/preflight.md || { echo "ERROR: preflight must require ignored-status inspection before any targeted cleanup"; exit 1; }
	@grep -Fq "Do not call separate message-delivery tools" skills/_shared/preflight.md || { echo "ERROR: preflight must keep scheduled-run delivery in final response only"; exit 1; }
	@grep -Fq "Use the headings \`요약\`, \`변경한 것\`, \`검증\`, \`커밋/푸시\`, \`다음 후보\`, and \`블로커\`" skills/_shared/preflight.md || { echo "ERROR: preflight must document scheduled-run report headings"; exit 1; }
	@grep -Fq 'use exactly `[SILENT]` only when there is genuinely nothing new to report' skills/_shared/preflight.md || { echo "ERROR: preflight must document exact scheduled-run silent suppression"; exit 1; }
	@grep -Fq "make validate-agent-docs" README.md || { echo "ERROR: README local validation docs must include focused AGENTS/preflight validation"; exit 1; }
	@grep -Fq "shared discipline/automation linkage" README.md || { echo "ERROR: README local validation docs must mention shared discipline/automation linkage"; exit 1; }
	@for f in skills/*/SKILL.md; do \
		grep -Fq "_shared/discipline.md" "$$f" || { echo "ERROR: $$f must reference shared discipline rules"; exit 1; }; \
	done
	@for f in skills/forgeflow/SKILL.md skills/clarify/SKILL.md skills/ff-plan/SKILL.md skills/execute/SKILL.md skills/ff-review/SKILL.md skills/ship/SKILL.md; do \
		grep -Fq "_shared/automation.md" "$$f" || { echo "ERROR: $$f must reference shared automation rules"; exit 1; }; \
	done
	@echo "OK: AGENTS/preflight docs and shared discipline/automation links are covered by focused validation"

validate-templates:
	@for t in $(TEMPLATES); do \
		if [ ! -f "templates/$$t" ]; then \
			echo "ERROR: Missing template templates/$$t"; \
			exit 1; \
		fi; \
		grep -Fq "$$t" README.md || { echo "ERROR: README must document template $$t"; exit 1; }; \
	done
	@echo "OK: All templates exist and are documented in README"
	@grep -Fq "make validate-templates validate-template-refs" README.md || { echo "ERROR: README local validation docs must include focused template validation bundle"; exit 1; }

validate-template-refs:
	@$(PYTHON) scripts/validate_template_refs.py

validate-gemini-imports:
	@$(PYTHON) scripts/validate_gemini_imports.py

validate-plugin-prompts:
	@$(PYTHON) scripts/validate_plugin_prompts.py

validate-evals-json:
	@$(PYTHON) scripts/validate_evals_json.py

validate-eval-files:
	@$(PYTHON) scripts/validate_eval_files.py

validate-workflow-vocab:
	@$(PYTHON) scripts/validate_workflow_vocab.py
	@grep -Fq "같은 \`/forgeflow:ff-review\`" README.md || { echo "ERROR: README must clarify high/epic spec/quality passes use the same review command"; exit 1; }
	@grep -Fq "observe" README.md || { echo "ERROR: README evolution lifecycle must describe ship-based observe stage"; exit 1; }
	@grep -Fq "extract" README.md || { echo "ERROR: README evolution lifecycle must describe ship-based extract stage"; exit 1; }
	@if grep -Fq 'proposed' README.md; then grep -Fq '별도 `proposed`' README.md || { echo "ERROR: README evolution lifecycle must not reference old proposed stage without explaining it was replaced"; exit 1; }; fi

validate-ship-safety:
	@grep -Fq "Do not remove or discard yet" skills/ship/SKILL.md || { echo "ERROR: ship skill must preserve worktrees before option-specific confirmation"; exit 1; }
	@grep -Fq "Type 'discard' to confirm." skills/ship/SKILL.md || { echo "ERROR: ship skill must require exact discard confirmation"; exit 1; }
	@grep -Fq "Never delete unrelated dirty working tree files" skills/ship/SKILL.md || { echo "ERROR: ship skill must protect unrelated dirty working tree files"; exit 1; }
	@echo "OK: Ship skill protects worktrees and destructive cleanup"

validate-dogfooding-docs:
	@grep -Fq "[docs/dogfooding.md](docs/dogfooding.md)" README.md || { echo "ERROR: README must link tracked .forgeflow fixture guidance"; exit 1; }
	@grep -Fq "intentionally tracked" docs/dogfooding.md || { echo "ERROR: dogfooding docs must say tracked task folders are intentional"; exit 1; }
	@grep -Fq "Normal consumer projects should keep" docs/dogfooding.md || { echo "ERROR: dogfooding docs must distinguish consumer project behavior"; exit 1; }
	@grep -Fq "Do not run broad cleanup commands such as \`git clean -fdX\`" docs/dogfooding.md || { echo "ERROR: dogfooding docs must forbid broad destructive cleanup"; exit 1; }
	@grep -Fq "inspect \`git status --short --ignored\` first" docs/dogfooding.md || { echo "ERROR: dogfooding docs must require ignored-status inspection before cleanup"; exit 1; }
	@echo "OK: Dogfooding fixture docs are linked and guarded"

validate-context-resume:
	@grep -Fq "skills/_shared/context-resume.md" README.md || { echo "ERROR: README must document context refresh/resume rules"; exit 1; }
	@for f in skills/forgeflow/SKILL.md skills/clarify/SKILL.md skills/ff-plan/SKILL.md skills/execute/SKILL.md skills/ff-review/SKILL.md skills/ship/SKILL.md; do \
		grep -Fq "_shared/context-resume.md" "$$f" || { echo "ERROR: $$f must reference shared context refresh/resume rules"; exit 1; }; \
	done
	@grep -Fq "Checkpoint-first" skills/_shared/context-resume.md || { echo "ERROR: context-resume rules must keep checkpoint-first guidance"; exit 1; }
	@grep -Fq "No default full re-read" skills/_shared/context-resume.md || { echo "ERROR: context-resume rules must guard against full artifact rereads"; exit 1; }
	@grep -Fq "Minimum Read Set" templates/checkpoint.md || { echo "ERROR: checkpoint template must expose a Minimum Read Set for context refresh resume"; exit 1; }
	@grep -Fq "Handoff Boundary" templates/checkpoint.md || { echo "ERROR: checkpoint template must expose stage handoff boundary ownership"; exit 1; }
	@grep -Fq "Handoff Boundary" skills/_shared/automation.md || { echo "ERROR: automation rules must require checkpoint handoff boundary ownership"; exit 1; }
	@for stage in clarify plan execute review ship; do \
		grep -Fq -- "- **$$stage** — owns" skills/_shared/automation.md || { echo "ERROR: automation stage catalog must define owned artifacts for $$stage"; exit 1; }; \
	done
	@grep -Fq "Allowed posture:" skills/_shared/automation.md || { echo "ERROR: automation stage catalog must define allowed tool posture"; exit 1; }
	@grep -Fq "Forbidden:" skills/_shared/automation.md || { echo "ERROR: automation stage catalog must define forbidden tool posture"; exit 1; }
	@grep -Fq "If a stage needs an action listed as forbidden" skills/_shared/automation.md || { echo "ERROR: automation stage catalog must define forbidden-action handoff behavior"; exit 1; }
	@grep -Fq "forbidden-action delegation" README.md || { echo "ERROR: README context refresh docs must mention checkpoint handoff boundary ownership"; exit 1; }
	@echo "OK: Context refresh/resume guidance is wired into core skills, checkpoint template, and stage boundary catalog"

validate-stage-tool-boundaries:
	@for stage in clarify plan execute ff-review ship; do \
		grep -Fq "| $$stage |" docs/stage-tool-boundaries.md || { echo "ERROR: stage tool boundaries must catalog $$stage"; exit 1; }; \
	done
	@grep -Fq "Stage artifacts are the handoff boundary" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must keep artifact handoff as the boundary"; exit 1; }
	@grep -Fq "Use the smallest tool surface" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must require minimal tool surface"; exit 1; }
	@grep -Fq "record the need in the current artifact and hand off to the stage that owns it" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must require forbidden-action handoff"; exit 1; }
	@grep -Fq "current owner" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must name current owner for escalations"; exit 1; }
	@grep -Fq "next owner" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must name next owner for escalations"; exit 1; }
	@grep -Fq "requested/forbidden action" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must name requested/forbidden action for escalations"; exit 1; }
	@grep -Fq "evidence or artifact trigger" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must name evidence/artifact trigger for escalations"; exit 1; }
	@grep -Fq "explicit stop condition" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must require explicit stop condition for escalations"; exit 1; }
	@grep -Fq "exact artifact update location" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must require exact artifact update location for escalations"; exit 1; }
	@grep -Fq "same escalation field set as the checkpoint boundary" skills/_shared/automation.md || { echo "ERROR: automation stage catalog must mirror escalation handoff fields"; exit 1; }
	@grep -Fq "must not change artifact names, route semantics, review verdicts, or human-gate rules" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must keep adapter exceptions from changing canonical semantics"; exit 1; }
	@grep -Fq "review-report.md" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must require review-report.md for ff-review"; exit 1; }
	@grep -Fq "input-source.md" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must include standalone review provenance artifacts"; exit 1; }
	@grep -Fq "normalized-input.md" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must include standalone review normalized input artifacts"; exit 1; }
	@grep -Fq "mutate PR/issues/CI/deploys" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must forbid review-side external mutations"; exit 1; }
	@grep -Fq "approve from implementer self-report only" docs/stage-tool-boundaries.md || { echo "ERROR: stage boundary docs must forbid self-report-only review approval"; exit 1; }
	@grep -Fq "make validate-stage-tool-boundaries" README.md || { echo "ERROR: README local validation docs must include focused stage boundary validation"; exit 1; }
	@echo "OK: Stage tool boundary catalog preserves adapter-neutral artifact ownership and review read-only posture"

validate-adapter-config:
	@$(PYTHON) scripts/validate_adapter_config.py
	@grep -Fq "historical reference" docs/adapter-config.md || { echo "ERROR: adapter performance docs must not overclaim current live provider SLA"; exit 1; }
	@grep -Fq "설치 위치와 작업 위치를 분리하세요" README.md || { echo "ERROR: README quickstart must separate plugin/extension install location from target project workflow location"; exit 1; }
	@grep -Fq "make validate-adapter-config" README.md || { echo "ERROR: README local validation docs must include focused adapter config validation"; exit 1; }
	@grep -Fq "**작업 위치 원칙:**" docs/adapter-config.md || { echo "ERROR: adapter config must state the shared workflow location principle"; exit 1; }
	@grep -Fq "\`<task-dir>/brief.md\`, \`plan.md\`, \`implementation-notes.md\`, \`review-report.md\`, \`ledger.md\`, \`checkpoint.md\`, \`run-state.json\`" README.md || { echo "ERROR: README installed plugin smoke criteria must include the plan.md artifact"; exit 1; }
	@grep -Fq "plugin/extension 설치·cache 위치" docs/adapter-config.md || { echo "ERROR: adapter config must distinguish plugin/extension cache from target projects"; exit 1; }
	@grep -Fq -- "--task-dir ~/.forgeflow/projects/<project-slug>/tasks/<task-id>" docs/adapter-config.md || { echo "ERROR: adapter config must document explicit global task-dir fallback from cache contexts"; exit 1; }
	@grep -Fq "Multi-harness routing invariants" docs/adapter-config.md || { echo "ERROR: adapter config must document multi-harness routing invariants"; exit 1; }
	@grep -Fq "Canonical stage contract first" docs/adapter-config.md || { echo "ERROR: adapter config must keep canonical stage contract ahead of adapter exceptions"; exit 1; }
	@grep -Fq "Harness-specific code paths stay shallow" docs/adapter-config.md || { echo "ERROR: adapter config must keep harness-specific code paths shallow"; exit 1; }
	@grep -Fq "Artifact handoff is the boundary" docs/adapter-config.md || { echo "ERROR: adapter config must require markdown artifact handoff boundaries"; exit 1; }
	@grep -Fq "Review adapters normalize before judging" docs/adapter-config.md || { echo "ERROR: adapter config must require review adapters to normalize before judging"; exit 1; }
	@grep -Fq "Multi-harness 원칙" README.md || { echo "ERROR: README must expose multi-harness invariants to users"; exit 1; }
	@grep -Fq "adapter-neutral core contract" README.md || { echo "ERROR: README must state adapter-neutral core contract boundaries"; exit 1; }
	@grep -Fq "역할 경계 원칙" README.md || { echo "ERROR: README must expose stage-owned role boundary principles"; exit 1; }
	@grep -Fq "Stage-owned role boundaries" docs/stage-tool-boundaries.md || { echo "ERROR: stage tool boundary docs must document role boundaries"; exit 1; }
	@grep -Fq "not a license to create a parallel runtime" docs/stage-tool-boundaries.md || { echo "ERROR: role boundary docs must prevent parallel runtime drift"; exit 1; }
	@grep -Fq "Members must not spawn unmanaged child work" docs/stage-tool-boundaries.md || { echo "ERROR: role boundary docs must block unmanaged member child-work"; exit 1; }
	@grep -Fq "lead-owned artifact update before work continues" docs/stage-tool-boundaries.md || { echo "ERROR: role boundary docs must require lead-owned artifact updates for member scope changes"; exit 1; }
	@grep -Fq "Disposable 또는 untrusted repo에서 headless smoke" docs/adapter-config.md || { echo "ERROR: Gemini adapter docs must mention --skip-trust for disposable/untrusted headless smoke"; exit 1; }

validate-evals-fixtures:
	@$(PYTHON) scripts/validate_evals_fixtures.py
	@grep -Fq "not a live provider benchmark" evals/README.md || { echo "ERROR: evals README must not overclaim live provider benchmarking"; exit 1; }
	@grep -Fq "make validate-evals-json validate-eval-files validate-evals-fixtures" evals/README.md || { echo "ERROR: evals README must document the local eval validation bundle"; exit 1; }
	@grep -Fq "next sequential" evals/README.md || { echo "ERROR: evals README must document sequential fixture IDs"; exit 1; }
	@grep -Fq "fixture text avoids stale workflow vocabulary" evals/README.md || { echo "ERROR: evals README must document stale-vocabulary fixture guard"; exit 1; }
	@grep -Fq "remains the public bootstrap skill" evals/README.md || { echo "ERROR: evals README must clarify forgeflow-init is bootstrap, not removed workflow stage"; exit 1; }
	@grep -Fq "ship-stage fixture names use \`ship-*\` slugs" evals/README.md || { echo "ERROR: evals README must document ship-stage fixture slug naming"; exit 1; }
	@! grep -Fq '"name": "finish-' evals/evals.json || { echo "ERROR: ship-stage eval fixture names must not use removed finish-stage slugs"; exit 1; }
	@grep -Fq "These are benchmark fixture sizes, not ForgeFlow route labels" skills/benchmark/SKILL.md || { echo "ERROR: benchmark skill must distinguish benchmark sizes from workflow route labels"; exit 1; }
	@grep -Fq "Do not report \`large\` as a workflow route" skills/benchmark/SKILL.md || { echo "ERROR: benchmark skill must forbid treating large as a workflow route"; exit 1; }
	@grep -Fq "Benchmark output lives under a disposable benchmark root" skills/benchmark/SKILL.md || { echo "ERROR: benchmark skill must keep reports/logs under disposable benchmark root"; exit 1; }
	@grep -Fq "Do not write benchmark reports, logs, metrics, prompts, or generated app projects into this ForgeFlow source checkout" skills/benchmark/SKILL.md || { echo "ERROR: benchmark skill must protect the ForgeFlow source checkout during benchmarks"; exit 1; }
	@grep -Fq "eval names use kebab-case" evals/README.md || { echo "ERROR: evals README must document kebab-case eval names"; exit 1; }
	@grep -Fq "is not duplicated within the same eval case" evals/README.md || { echo "ERROR: evals README must document unique file reference rules"; exit 1; }
	@grep -Fq "assertion \`value\` / \`values\` entries are non-blank strings" evals/README.md || { echo "ERROR: evals README must document non-blank assertion value rules"; exit 1; }
	@grep -Fq "multi-value assertion \`values\` entries are unique" evals/README.md || { echo "ERROR: evals README must document unique multi-value assertion rules"; exit 1; }
	@grep -Fq "assertion \`text\` entries are unique within each eval case" evals/README.md || { echo "ERROR: evals README must document per-case unique assertion text rules"; exit 1; }
	@grep -Fq "every machine-checkable requirement must be mirrored in \`assertions\`" evals/README.md || { echo "ERROR: evals README must document expected_output/assertions separation"; exit 1; }
	@grep -Fq "benchmark fixtures must use \`/forgeflow:benchmark\`" evals/README.md || { echo "ERROR: evals README must document benchmark fixture command scope"; exit 1; }
	@grep -Fq "long-run evolution fixtures record candidate notes" evals/README.md || { echo "ERROR: evals README must document long-run candidate-note scope"; exit 1; }
	@grep -Fq "git push origin HEAD:refs/heads/main" evals/README.md || { echo "ERROR: evals README must document explicit branch push for autonomous maintainer fixtures"; exit 1; }
	@grep -Fq "without writing .forgeflow/evolution/proposed/ files directly" evals/evals.json || { echo "ERROR: long-run eval fixture must not ask long-run to write evolution-rule files directly"; exit 1; }
	@grep -Fq "Evolution rule materialization is handled by the **ship** stage" skills/long-run/SKILL.md || { echo "ERROR: long-run skill must leave evolution rule materialization to ship"; exit 1; }
	@grep -Fq "별도 \`proposed\`" README.md || { echo "ERROR: README evolution lifecycle must state proposed/review intermediate steps were removed"; exit 1; }
	@grep -Fq "evolution rule 생성은 ship 단계에서 직접" README.md || { echo "ERROR: README must say ship creates evolution rules directly"; exit 1; }
	@grep -Fq "\`.github/workflows/evals.yml\`" README.md || { echo "ERROR: README must name the evals workflow file for eval fixture checks"; exit 1; }
	@grep -Fq "make validate-markdown-links" README.md || { echo "ERROR: README local validation docs must include focused markdown link validation"; exit 1; }
	@grep -Fq "HTML href/src" README.md || { echo "ERROR: README local validation docs must mention HTML href/src link coverage"; exit 1; }
	@echo "OK: eval README documents deterministic scope and local validation"

validate-advisory-contract:
	@$(PYTHON) scripts/validate_advisory_contract.py
	@grep -Fq "Evidence requirements by role" skills/ff-review/references/role-checklists.md || { echo "ERROR: review role checklists must document evidence requirements by role"; exit 1; }
	@grep -Fq "normalization gate" skills/ff-review/SKILL.md || { echo "ERROR: review skill must require a standalone normalization gate before role passes"; exit 1; }
	@grep -Fq "normalization gate" skills/ff-review/references/role-checklists.md || { echo "ERROR: role checklists must block on incomplete normalized input"; exit 1; }
	@grep -Fq "normalization gate" templates/normalized-input.md || { echo "ERROR: normalized input template must expose a reviewer preflight gate"; exit 1; }
	@grep -Fq "Normalization Gate" templates/review-report.md || { echo "ERROR: review report template must surface standalone normalization gate status"; exit 1; }
	@grep -Fq "Evidence requirements source" templates/review-report.md || { echo "ERROR: review report template must point to role evidence requirements"; exit 1; }
	@grep -Fq "Role capability hints" templates/review-report.md || { echo "ERROR: review report template must expose advisory role capability hints"; exit 1; }
	@grep -Fq "must not affect routing, evidence IDs, evidence levels, verdict enums, approval rules, or Human Review Gate" templates/review-report.md || { echo "ERROR: review report role capability hints must stay advisory-only"; exit 1; }
	@grep -Fq "Review tool posture" skills/ff-review/SKILL.md || { echo "ERROR: review skill must document inspection-only tool posture"; exit 1; }
	@grep -Fq "role_reassignment_policy" templates/normalized-input.md || { echo "ERROR: normalized input template must guard delegated reviewer role reassignment"; exit 1; }
	@grep -Fq "members cannot create additional reviewer roles" skills/ff-review/SKILL.md || { echo "ERROR: review skill must keep delegated reviewer role creation lead-only"; exit 1; }
	@grep -Fq "fetching declared review input through read-only commands" skills/ff-review/SKILL.md || { echo "ERROR: review skill must keep external evidence fetches read-only"; exit 1; }
	@grep -Fq "issue comments, PR reviews, approvals, labels, CI dispatch, deploys" skills/ff-review/SKILL.md || { echo "ERROR: review skill must forbid remote review-side mutations"; exit 1; }
	@grep -Fq "hand it back to execute" skills/ff-review/SKILL.md || { echo "ERROR: review skill must hand code/product fixes back to execute"; exit 1; }
	@grep -Fq "role별 evidence requirement" README.md || { echo "ERROR: README standalone review docs must mention role-specific evidence requirements"; exit 1; }
	@grep -Fq "external-system access to read-only evidence fetching" README.md || { echo "ERROR: README standalone review docs must expose read-only external-system posture"; exit 1; }
	@grep -Fq "Evidence Gap Register" docs/review-runtime-contract.md || { echo "ERROR: review runtime contract must require standalone evidence gap registration"; exit 1; }
	@grep -Fq "scope_source_map" docs/review-runtime-contract.md || { echo "ERROR: review runtime contract must require scope-to-evidence mapping"; exit 1; }
	@grep -Fq "Evidence Gap Register" templates/normalized-input.md || { echo "ERROR: normalized input template must expose evidence gap registration"; exit 1; }
	@grep -Fq "scope_source_map" templates/normalized-input.md || { echo "ERROR: normalized input template must expose scope-to-evidence mapping"; exit 1; }
	@grep -Fq "Evidence Gap Register" templates/review-report.md || { echo "ERROR: review report template must cite standalone evidence gap registration"; exit 1; }

validate-behavior-guardrails:
	@$(PYTHON) scripts/validate_behavior_guardrails.py

validate-markdown-links:
	@PYTHON="$(PYTHON)" bash scripts/validate-markdown-links.sh

# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------
telemetry: telemetry-collect telemetry-aggregate

telemetry-collect:
	@$(PYTHON) scripts/telemetry_collect.py

telemetry-aggregate:
	@$(PYTHON) scripts/telemetry_aggregate.py

usage-audit:
	@$(PYTHON) scripts/surface_usage_audit.py --days 28

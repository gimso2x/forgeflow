PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

.PHONY: setup check-env validate generate regen clean validate-samples runtime-sample adherence-evals smoke-claude-plugin validate-upstream-import validate-hoyeon-import validate-skill-contracts validate-claude-hooks plan-cli-smoke learn-smoke claude-hook-smoke codex-recovery-smoke cursor-recovery-smoke shared-recovery-smoke

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt

check-env:
	$(PYTHON) scripts/check_environment.py

validate:
	$(PYTHON) scripts/validate_structure.py
	$(PYTHON) scripts/validate_policy.py
	$(PYTHON) scripts/validate_generated.py
	$(PYTHON) scripts/validate_sample_artifacts.py
	$(PYTHON) scripts/run_adherence_evals.py
	$(PYTHON) scripts/validate_upstream_import.py
	$(PYTHON) scripts/validate_hoyeon_import.py
	$(PYTHON) scripts/validate_skill_contracts.py
	$(PYTHON) scripts/validate_claude_hooks.py
	$(PYTHON) scripts/smoke_plan_cli.py
	pytest tests/test_forgeflow_learn.py -q
	pytest tests/test_claude_recovery_hooks.py -q
	pytest tests/test_codex_recovery_guidance.py -q
	pytest tests/test_cursor_recovery_guidance.py -q
	pytest tests/test_shared_recovery_contract.py -q

runtime-sample:
	$(PYTHON) scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small

adherence-evals:
	$(PYTHON) scripts/run_adherence_evals.py

validate-upstream-import:
	$(PYTHON) scripts/validate_upstream_import.py

validate-hoyeon-import:
	$(PYTHON) scripts/validate_hoyeon_import.py

validate-skill-contracts:
	$(PYTHON) scripts/validate_skill_contracts.py

validate-claude-hooks:
	$(PYTHON) scripts/validate_claude_hooks.py

plan-cli-smoke:
	$(PYTHON) scripts/smoke_plan_cli.py

learn-smoke:
	pytest tests/test_forgeflow_learn.py -q

claude-hook-smoke:
	pytest tests/test_claude_recovery_hooks.py -q

codex-recovery-smoke:
	pytest tests/test_codex_recovery_guidance.py -q

cursor-recovery-smoke:
	pytest tests/test_cursor_recovery_guidance.py -q

shared-recovery-smoke:
	pytest tests/test_shared_recovery_contract.py -q

smoke-claude-plugin:
	$(PYTHON) scripts/smoke_claude_plugin.py

generate:
	$(PYTHON) scripts/generate_adapters.py

validate-samples:
	$(PYTHON) scripts/validate_sample_artifacts.py

regen: generate validate

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

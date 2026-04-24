PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

.PHONY: setup check-env validate generate regen clean validate-samples runtime-sample adherence-evals smoke-claude-plugin validate-upstream-import validate-hoyeon-import validate-skill-contracts validate-claude-hooks plan-cli-smoke evolution-policy-smoke learn-smoke claude-hook-smoke shared-recovery-smoke team-pattern-smoke agent-preset-smoke claude-agent-preset-smoke release-script-smoke verify-skill-smoke finish-skill-smoke plugin-manifest-smoke

setup:
	$(PYTHON) scripts/check_environment.py --require-venv-support --skip-modules
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PYTHON) -m pip install -r requirements.txt

check-env:
	$(VENV_PYTHON) scripts/check_environment.py

validate:
	$(VENV_PYTHON) scripts/validate_structure.py
	$(VENV_PYTHON) scripts/validate_policy.py
	$(VENV_PYTHON) scripts/validate_generated.py
	$(VENV_PYTHON) scripts/validate_sample_artifacts.py
	$(VENV_PYTHON) scripts/run_adherence_evals.py
	$(VENV_PYTHON) scripts/validate_upstream_import.py
	$(VENV_PYTHON) scripts/validate_hoyeon_import.py
	$(VENV_PYTHON) scripts/validate_skill_contracts.py
	$(VENV_PYTHON) scripts/validate_claude_hooks.py
	$(VENV_PYTHON) scripts/smoke_plan_cli.py
	$(VENV_PYTHON) -m pytest tests/test_evolution_policy.py -q
	$(VENV_PYTHON) -m pytest tests/test_forgeflow_ux_contract.py -q
	$(VENV_PYTHON) -m pytest tests/test_forgeflow_learn.py -q
	$(VENV_PYTHON) -m pytest tests/test_claude_recovery_hooks.py -q
	$(VENV_PYTHON) -m pytest tests/test_shared_recovery_contract.py -q
	$(VENV_PYTHON) -m pytest tests/test_team_pattern_contract.py -q
	$(VENV_PYTHON) -m pytest tests/test_agent_preset_install.py -q
	$(VENV_PYTHON) -m pytest tests/test_claude_agent_preset_install.py -q
	$(VENV_PYTHON) -m pytest tests/test_first_clone_setup.py -q
	$(VENV_PYTHON) -m pytest tests/test_release_script.py -q
	$(VENV_PYTHON) -m pytest tests/test_verify_skill_contract.py -q
	$(VENV_PYTHON) -m pytest tests/test_finish_skill_contract.py -q
	$(VENV_PYTHON) -m pytest tests/test_plugin_manifests.py -q

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

evolution-policy-smoke:
	pytest tests/test_evolution_policy.py -q

learn-smoke:
	pytest tests/test_forgeflow_learn.py -q

claude-hook-smoke:
	pytest tests/test_claude_recovery_hooks.py -q

shared-recovery-smoke:
	pytest tests/test_shared_recovery_contract.py -q

team-pattern-smoke:
	pytest tests/test_team_pattern_contract.py -q

agent-preset-smoke:
	pytest tests/test_agent_preset_install.py -q

claude-agent-preset-smoke:
	pytest tests/test_claude_agent_preset_install.py -q

release-script-smoke:
	pytest tests/test_release_script.py -q

verify-skill-smoke:
	pytest tests/test_verify_skill_contract.py -q

finish-skill-smoke:
	pytest tests/test_finish_skill_contract.py -q

plugin-manifest-smoke:
	pytest tests/test_plugin_manifests.py -q

smoke-claude-plugin:
	$(PYTHON) scripts/smoke_claude_plugin.py

generate:
	$(PYTHON) scripts/generate_adapters.py

validate-samples:
	$(PYTHON) scripts/validate_sample_artifacts.py

regen: generate validate

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

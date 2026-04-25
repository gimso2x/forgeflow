PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

.PHONY: setup check-env validate generate regen clean validate-samples runtime-sample adherence-evals monitor-summary monitor-summary-json orchestrator-help orchestrator-status smoke-claude-plugin validate-upstream-import validate-hoyeon-import validate-skill-contracts validate-claude-hooks plan-cli-smoke evolution-policy-smoke learn-smoke claude-hook-smoke shared-recovery-smoke team-pattern-smoke agent-preset-smoke claude-agent-preset-smoke release-script-smoke verify-skill-smoke finish-skill-smoke plugin-manifest-smoke

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
	$(VENV_PYTHON) -m pytest tests/evolution -q
	$(VENV_PYTHON) -m pytest tests/runtime -q
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
	$(VENV_PYTHON) scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small

adherence-evals:
	$(VENV_PYTHON) scripts/run_adherence_evals.py

monitor-summary:
	$(VENV_PYTHON) scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10 --format md

monitor-summary-json:
	@$(VENV_PYTHON) scripts/forgeflow_monitor.py --tasks .forgeflow/tasks --recent 10 --format json

orchestrator-help:
	$(VENV_PYTHON) scripts/run_orchestrator.py --help
	$(VENV_PYTHON) scripts/run_orchestrator.py run --help
	$(VENV_PYTHON) scripts/run_orchestrator.py advance --help
	$(VENV_PYTHON) scripts/run_orchestrator.py execute --help

orchestrator-status:
	$(VENV_PYTHON) scripts/run_orchestrator.py status --task-dir examples/runtime-fixtures/small-doc-task

validate-upstream-import:
	$(VENV_PYTHON) scripts/validate_upstream_import.py

validate-hoyeon-import:
	$(VENV_PYTHON) scripts/validate_hoyeon_import.py

validate-skill-contracts:
	$(VENV_PYTHON) scripts/validate_skill_contracts.py

validate-claude-hooks:
	$(VENV_PYTHON) scripts/validate_claude_hooks.py

plan-cli-smoke:
	$(VENV_PYTHON) scripts/smoke_plan_cli.py

evolution-policy-smoke:
	$(VENV_PYTHON) -m pytest tests/evolution -q

learn-smoke:
	$(VENV_PYTHON) -m pytest tests/test_forgeflow_learn.py -q

claude-hook-smoke:
	$(VENV_PYTHON) -m pytest tests/test_claude_recovery_hooks.py -q

shared-recovery-smoke:
	$(VENV_PYTHON) -m pytest tests/test_shared_recovery_contract.py -q

team-pattern-smoke:
	$(VENV_PYTHON) -m pytest tests/test_team_pattern_contract.py -q

agent-preset-smoke:
	$(VENV_PYTHON) -m pytest tests/test_agent_preset_install.py -q

claude-agent-preset-smoke:
	$(VENV_PYTHON) -m pytest tests/test_claude_agent_preset_install.py -q

release-script-smoke:
	$(VENV_PYTHON) -m pytest tests/test_release_script.py -q

verify-skill-smoke:
	$(VENV_PYTHON) -m pytest tests/test_verify_skill_contract.py -q

finish-skill-smoke:
	$(VENV_PYTHON) -m pytest tests/test_finish_skill_contract.py -q

plugin-manifest-smoke:
	$(VENV_PYTHON) -m pytest tests/test_plugin_manifests.py -q

smoke-claude-plugin:
	$(VENV_PYTHON) scripts/smoke_claude_plugin.py

generate:
	$(VENV_PYTHON) scripts/generate_adapters.py

validate-samples:
	$(VENV_PYTHON) scripts/validate_sample_artifacts.py

regen: generate validate

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

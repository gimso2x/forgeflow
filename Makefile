PYTHON ?= python3

.PHONY: validate generate regen clean validate-samples runtime-sample adherence-evals

validate:
	$(PYTHON) scripts/validate_structure.py
	$(PYTHON) scripts/validate_policy.py
	$(PYTHON) scripts/validate_generated.py
	$(PYTHON) scripts/validate_sample_artifacts.py
	$(PYTHON) scripts/run_adherence_evals.py

runtime-sample:
	$(PYTHON) scripts/run_orchestrator.py run --task-dir examples/runtime-fixtures/small-doc-task --route small

adherence-evals:
	$(PYTHON) scripts/run_adherence_evals.py

generate:
	$(PYTHON) scripts/generate_adapters.py

validate-samples:
	$(PYTHON) scripts/validate_sample_artifacts.py

regen: generate validate

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

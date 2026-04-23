PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip

.PHONY: setup check-env validate generate regen clean validate-samples runtime-sample adherence-evals

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

runtime-sample:
	$(PYTHON) scripts/run_runtime_sample.py --fixture-dir examples/runtime-fixtures/small-doc-task --route small

adherence-evals:
	$(PYTHON) scripts/run_adherence_evals.py

generate:
	$(PYTHON) scripts/generate_adapters.py

validate-samples:
	$(PYTHON) scripts/validate_sample_artifacts.py

regen: generate validate

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

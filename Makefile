PYTHON ?= python3

.PHONY: validate generate regen clean validate-samples

validate:
	$(PYTHON) scripts/validate_structure.py
	$(PYTHON) scripts/validate_policy.py
	$(PYTHON) scripts/validate_generated.py
	$(PYTHON) scripts/validate_sample_artifacts.py

generate:
	$(PYTHON) scripts/generate_adapters.py

validate-samples:
	$(PYTHON) scripts/validate_sample_artifacts.py

regen: generate validate

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

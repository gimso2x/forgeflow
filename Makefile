PYTHON ?= python3

.PHONY: validate generate regen clean

validate:
	$(PYTHON) scripts/validate_structure.py
	$(PYTHON) scripts/validate_policy.py
	$(PYTHON) scripts/validate_generated.py

generate:
	$(PYTHON) scripts/generate_adapters.py

regen: generate validate

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

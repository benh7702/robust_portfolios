.PHONY: test research report all clean

PYTHON ?= python

test:
	PYTHONPATH=src $(PYTHON) -m pytest -q

research:
	PYTHONPATH=src $(PYTHON) scripts/run_research.py --bootstrap-reps 2000

report:
	$(PYTHON) report/build_empirical_report.py

all: test research report

clean:
	rm -rf .pytest_cache src/robust_portfolio/__pycache__ tests/__pycache__

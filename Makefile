PYTHON3		= python3
ENVVARS		= PYTHONPATH=.
SCRIPT		= roff2xml/tests/troff.py

test check:
	$(ENVVARS) $(PYTHON3) $(SCRIPT)

vtest vcheck test-v:
	$(ENVVARS) $(PYTHON3) $(SCRIPT) -v

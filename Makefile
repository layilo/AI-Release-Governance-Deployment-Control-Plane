PYTHON ?= python

.PHONY: install lint test demo blocked rollback clean

install:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

lint:
	ruff check src tests

test:
	pytest

demo:
	$(PYTHON) -m ai_release_control_plane.cli demo-run --scenario success --profile local-demo

blocked:
	$(PYTHON) -m ai_release_control_plane.cli demo-run --scenario blocked_offline --profile local-demo

rollback:
	$(PYTHON) -m ai_release_control_plane.cli demo-run --scenario rollback_canary --profile local-demo

clean:
	rm -rf state reports *.egg-info

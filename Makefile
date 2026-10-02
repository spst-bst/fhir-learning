.PHONY: install up down reset-data load-data test test-01 test-02 test-03 test-04 test-05 test-06 test-07

install:
	uv sync

up:
	./scripts/start_stack.sh

down:
	./scripts/stop_stack.sh

reset-data:
	./scripts/stop_stack.sh -v
	./scripts/start_stack.sh
	uv run python scripts/load_synthea_data.py

load-data:
	uv run python scripts/load_synthea_data.py

test: test-01 test-02 test-03 test-04 test-05 test-06 test-07

test-01:
	uv run pytest modules/01-setup/exercises -v

test-02:
	uv run pytest modules/02-fhir-resources/exercises -v

test-03:
	uv run pytest modules/03-code-systems-data-quality/exercises -v

test-04:
	uv run pytest modules/04-hl7v2/exercises -v

test-05:
	uv run pytest modules/05-bulk-fhir/exercises -v

test-06:
	uv run pytest modules/06-smart-on-fhir/exercises -v

test-07:
	uv run pytest modules/07-capstone/exercises -v

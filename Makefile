# =============================================================================
# Swiss Reality Check — Hack Apertus, Track 1B
#
#   make run     spin the project up in Docker  (this is what judges run)
#   make verify  run the verification suite locally, no Docker, no model
#   make test    every automated check
#   make shell   a container with the project mounted, for poking around
#   make clean   remove build artefacts
#
# `make run` must work on a clean checkout with no configuration at all, so it
# runs OFFLINE by default: the benchmark's model-free checks (dataset integrity,
# retrieval recall, scoring, statistics, charts) all execute without an LLM.
# Set LLM_BASE_URL to additionally run a live smoke test against a real model.
#
# Track 1B environment variables (the three the template requires):
#   LLM_NAME      model name/version, e.g. Apertus-v1.5-8B-Instruct-Q4_K_M
#   LLM_BASE_URL  endpoint base URL, e.g. http://127.0.0.1:8080/v1
#   LLM_API_KEY   API key
#
# These are aliases. The harness's own variables (APERTUS_8B_*) take precedence
# when set, so an existing local setup is never silently overridden.
# =============================================================================

.PHONY: help run build verify test verify-test shell clean docker-check

DOCKER       ?= docker
COMPOSE      ?= $(DOCKER) compose
PYTHON       ?= python3

help:
	@echo "Swiss Reality Check — available targets:"
	@echo "  make run        spin up in Docker (offline; add LLM_BASE_URL for live)"
	@echo "  make build      build the image without running"
	@echo "  make verify     offline verification, no Docker, no model"
	@echo "  make test       every automated check (13 suites)"
	@echo "  make shell      container with the project mounted"
	@echo "  make clean      remove build artefacts"

# ---------------------------------------------------------------- the target
run:
	$(COMPOSE) run --rm app

build:
	$(COMPOSE) build

shell:
	$(COMPOSE) run --rm app /bin/bash

docker-check:
	@command -v $(DOCKER) >/dev/null 2>&1 \
		|| { echo "docker not found on PATH."; \
		     echo "If Docker is unavailable, run: make verify"; exit 1; }
	@$(DOCKER) --version

# ------------------------------------------------------- no-Docker fallback
# The judges have Docker. A contributor may not. These targets exist so the
# project is runnable either way, and `make verify` is what CI can call.
verify:
	$(PYTHON) src/run.py --offline

test:
	@set -e; \
	for f in src/fix/test_error_taxonomy.py \
	         src/fix/test_select_target.py \
	         src/fix/test_improvement.py \
	         src/fix/test_validation.py \
	         src/fix/test_phase4.py \
	         src/fix/test_statistics.py \
	         src/fix/test_charts.py \
	         src/fix/test_narrative.py \
	         src/eval/test_knowledge_scoring.py \
	         src/eval/test_judge.py \
	         src/eval/test_dialect.py \
	         src/eval/test_baseline_report.py \
	         src/eval/smoke_test.py; do \
	  printf '  %-40s ' "$$f"; \
	  if $(PYTHON) "$$f" >/dev/null 2>&1; then echo PASS; else echo FAIL; exit 1; fi; \
	done; \
	echo; echo "all suites passed"

clean:
	rm -rf .pytest_cache **/__pycache__ __pycache__
	find . -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete 2>/dev/null || true

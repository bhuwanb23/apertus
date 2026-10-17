# =============================================================================
# Swiss Reality Check — Hack Apertus, Track 1B
#
#   make run         spin the project up in Docker  (this is what judges run)
#   make verify      run the verification suite locally, no Docker, no model
#   make test        every automated check
#   make shell       a container on the IMAGE copy, for poking around
#                   (use `make run-mount` to mount the working tree instead)
#   make clean       remove build artefacts
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
#
# -----------------------------------------------------------------------------
# PORTABILITY NOTE — why this file avoids shell features.
#
# Every recipe below is a SINGLE command. That is deliberate. `set -e`, `for`,
# `&&`, `||` and `$(shell ...)` with control flow all require a working POSIX
# shell, and GNU Make on Windows (GnuWin32, still the common install) does not
# reliably have one. An earlier version of this file used a shell loop for the
# test suites and could not run on a stock Windows machine at all.
#
# Interpreter selection is done by probing with one-shot $(shell ...) calls and
# $(findstring), which need no shell control flow. See PYTHON below.
# =============================================================================

.PHONY: help run build verify verify-test test shell run-mount clean docker-check check-interp

DOCKER       ?= docker
COMPOSE      ?= $(DOCKER) compose

# ---------------------------------------------------------------- interpreter
# `python3` is correct inside the image (python:3.11-slim) and on Linux. It is
# NOT correct on a default Windows install, where `python3` is a Microsoft Store
# alias stub: present on PATH, not a Python, and it fails with "The system
# cannot find the path specified." rather than anything mentioning Python.
#
# So probe. A real interpreter answers `--version` with a version; the stub
# answers with Store text, which contains no "3.". $(findstring) does the test
# without needing a shell.
_PROBE_PY3 := $(shell python3 --version 2>&1)
_PROBE_PY  := $(shell python  --version 2>&1)
_OK_PY3    := $(findstring 3.,$(_PROBE_PY3))
_OK_PY     := $(findstring 3.,$(_PROBE_PY))

# An explicit PYTHON=... on the command line always wins -- except when it names
# something known to be broken, because then nothing can report it.
#
# src/scripts/check_interp.py explains this failure properly, but it runs *through*
# $(PYTHON): if that is the Store stub, the explanation cannot execute either, and
# the user gets the raw "install from the Microsoft Store" text with no mention of
# the Makefile. $(error) fires at parse time, needs no shell, and therefore needs
# no working interpreter.
_PROBE_PY_LAUNCHER := $(shell py --version 2>&1)
_OK_LAUNCHER       := $(findstring 3.,$(_PROBE_PY_LAUNCHER))

ifeq ($(origin PYTHON),command line)
  ifeq ($(PYTHON),python3)
    ifeq ($(_OK_PY3),)
      $(error PYTHON=python3 was requested, but `python3` is not a working interpreter here. On Windows it is normally a Microsoft Store alias stub: on PATH, not a Python, and it fails with "The system cannot find the path specified." rather than anything naming Python. Retry with a real one - `make help` prints the one this Makefile detected.)
    endif
  endif
endif

# An explicit PYTHON=... on the command line always wins.
ifeq ($(origin PYTHON),undefined)
  ifneq ($(_OK_PY3),)
    PYTHON := python3
  else
    ifneq ($(_OK_PY),)
      PYTHON := python
    else
      PYTHON := python3
    endif
  endif
endif

help: check-interp
	$(PYTHON) src/scripts/help_text.py

# ---------------------------------------------------------------- the target
# This is what judges run. It does not use $(PYTHON): the interpreter is chosen
# inside the image, where python3 always exists.
run: docker-check
	$(COMPOSE) run --rm app

build: docker-check
	$(COMPOSE) build

shell: docker-check
	$(COMPOSE) run --rm app /bin/bash

# Bind-mount the working tree instead of using the image's copy. Convenient
# for iterating, but NOT what judges should run: it makes the container test
# the local checkout rather than the shipped image. Results are written back
# to ./results on the host.
run-mount: docker-check
	$(COMPOSE) run --rm -v ./:/app app

docker-check: check-interp
	@$(PYTHON) src/scripts/check_docker.py

# ------------------------------------------------------- no-Docker fallback
# The judges have Docker. A contributor may not. These targets exist so the
# project is runnable either way, and `make verify` is what CI can call.
check-interp:
	@$(PYTHON) src/scripts/check_interp.py

verify: check-interp
	$(PYTHON) src/run.py --offline

# The held-out seal pre-flight on its own: is the sealed set intact, is the code
# frozen, is the tree clean. This was declared .PHONY with no recipe, so
# `make verify-test` silently did nothing and exited 0 - the worst possible
# failure mode for a check that exists to stop a run.
verify-test: check-interp
	$(PYTHON) src/eval/run_test_final.py --preflight

test: check-interp
	$(PYTHON) src/scripts/run_suites.py

clean: check-interp
	$(PYTHON) src/scripts/clean.py

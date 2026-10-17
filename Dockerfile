# =============================================================================
# Swiss Reality Check — Hack Apertus, Track 1B
#
# Deliberately small. The benchmark talks to a model over HTTP and never loads
# weights in-process, so this image needs no GPU runtime, no torch, and no model
# weights. It needs python and two small packages.
#
# What the reported numbers DID need is a local llama.cpp server on the host,
# serving Apertus-v1.5-8B as a Q4_K_M GGUF. That runs on the GPU outside this
# container; see technical_report.md §2. Judges using an API endpoint instead
# should set LLM_BASE_URL and LLM_API_KEY (see docker-compose.yml).
# =============================================================================
FROM python:3.11-slim

# Non-root: nothing here needs privileges.
RUN useradd --create-home --uid 1000 apertus

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first, so a source-only change does not reinstall them.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Project. src/ holds the harness (eval/, fix/, scripts/); data/ holds the
# benchmark datasets; docs/ holds the write-ups; results/ holds the archived
# arms and generated reports.
COPY src   ./src
COPY data  ./data
COPY docs  ./docs
COPY results ./results
COPY README.md          ./README.md
COPY technical_report.md ./technical_report.md
COPY DATASHEET.md       ./DATASHEET.md
COPY CHANGELOG.md       ./CHANGELOG.md

# Makefile and docker-compose.yml are NOT decoration. Every module in src/
# locates the project root by walking up until it finds a directory holding both
# data/ and Makefile - that pair is the root marker. An earlier Dockerfile copied
# neither, so all 43 of those modules raised StopIteration inside the container
# and `make run` - the target judges run - died on its first line of work.
#
# src/scripts/test_dockerfile.py asserts the marker files are present here, so
# this cannot regress silently again.
COPY Makefile          ./Makefile
COPY docker-compose.yml ./docker-compose.yml

# The harness reads its configuration from the environment (LLM_NAME,
# LLM_BASE_URL, LLM_API_KEY) and from src/eval/.env if one is mounted. Nothing
# here is baked in and no key is ever committed.
COPY src/eval/.env.example ./src/eval/.env.example

RUN chown -R apertus:apertus /app
USER apertus

# Offline by default. `--offline` runs every check that does not need a model:
# dataset integrity, retrieval recall, scoring, statistics, charts, narrative.
# The live smoke test runs only when LLM_BASE_URL is set.
CMD ["python", "src/run.py"]

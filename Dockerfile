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
# benchmark datasets; docs/ holds the write-ups.
COPY src   ./src
COPY data  ./data
COPY docs  ./docs
COPY README.md          ./README.md
COPY technical_report.md ./technical_report.md
COPY DATASHEET.md       ./DATASHEET.md

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

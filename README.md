# Swiss Reality Check — Hack Apertus

**Track:** [1B — Swiss Voices](https://github.com/HackApertus/project-template/tree/main/track_1b)
**Team:** Swiss Reality Check — Bhuwan B · Padmanaban G · Avinash A
**Event:** Hack Apertus Online Phase (1–16 Oct 2026)

> **Does an open model know Switzerland?** 180 items — knowledge, values and
> Alemannic dialect — where every answer traces to a verbatim passage in an
> official Swiss source, and every distractor is a real answer from Germany or
> the EU.

```bash
make run     # Docker; works on a clean checkout with no configuration
```

---

## Headline result

Apertus 1.5 **8B**, held-out test set (n=36), retrieval-augmented against 100
harvested official Swiss sources:

| Arm | Accuracy | 95% CI |
|---|---|---|
| Baseline | 55.6% (20/36) | [39.6, 70.5] |
| With retrieval | **86.1%** (31/36) | [71.3, 93.9] |
| **Delta** | **+30.6 pp** | exact 95% CI [+13.1, +30.6] |

Paired McNemar: **11 improved, 0 regressed, p = 0.001**.

And the number we would defend hardest, because it needs no model at all:

| retrieval | finds the source containing the answer |
|---|---|
| top-1 | 83.3% |
| top-3 | 90.5% |
| top-5 | **94.0%** |

**Read the limitations before the headline.** Only one model has results, the
sealed set was opened 28 times, and n=36 supports no per-category claim. All of
it is in [technical_report.md §5](technical_report.md#5-limitations).

---

## Deliverables

| Deliverable | Location |
|---|---|
| Technical report | [`technical_report.md`](technical_report.md) |
| Technical report (PDF) | [`swiss_reality_check_report.pdf`](swiss_reality_check_report.pdf) |
| Code | [`src/`](src/) — `eval/` harness, `fix/` analysis, `scripts/` |
| Datasets | [`data/`](data/) |
| Write-ups, charts, plans | [`docs/`](docs/) |
| Key findings | [`results/narrative/findings.md`](results/narrative/findings.md) |
| Statistical report | [`results/final_scores/statistical_report.md`](results/final_scores/statistical_report.md) |
| Per-item results | [`results/test_run/`](results/test_run/) |
| Dataset (Hugging Face) | https://huggingface.co/datasets/bhuwanb23/apertus |

License: **Apache-2.0** (code) — see [`LICENSE`](LICENSE). The **dataset** is
**CDLA-Permissive-2.0**; see [`DATASHEET.md`](DATASHEET.md).

---

## Running it

Judges run `make run` from the repository root, on a clean checkout. It runs
**offline by default** — dataset integrity, retrieval recall, scoring,
statistics, charts and narrative all execute without an LLM, because the
benchmark's most important claim is model-free.

```bash
make run          # via Docker
make verify       # same checks, no Docker
make test         # 13 automated suites, 11,540 checks
make help         # all targets
```

### With a live model

The reported numbers were produced against a local **llama.cpp** server on an
RTX 5060:

```bash
export LLM_NAME=Apertus-v1.5-8B-Instruct-Q4_K_M
export LLM_BASE_URL=http://host.docker.internal:8080/v1
export LLM_API_KEY=EMPTY
make run          # additionally smoke-tests the live model
```

`host.docker.internal` rather than `127.0.0.1`: inside the container, loopback
is the container itself, so a server on the host is unreachable by that name
otherwise.

On the host directly:

```bash
llama-server -m apertus-v1.5-8b-text-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8080 --ctx-size 8192 -ngl 99
```

**Model substitution, disclosed.** The reported run used the text-only
**Q4_K_M** GGUF extract, not `swiss-ai/Apertus-v1.5-8B`. The full checkpoint is
gated and is the Omni model — 8.9 B parameters, ~19 GB in bf16, with vision and
audio towers — which does not fit an 8 GB card. Every pillar of this benchmark
is text, so the text-only extract is the right instrument, but the substitution
is recorded in every artefact rather than left implicit. Full rationale in
[technical_report.md §6](technical_report.md#6-reproducibility).

### Dependencies

`python-dotenv`, and optionally `numpy` (dense retriever) and `openai` (OpenAI
backend). **No torch, no pandas, no matplotlib** — the charts are hand-rolled
SVG. The default retrieval and scoring path runs on the standard library.

---

## What is in here

```
Makefile              make run / verify / test
Dockerfile            slim image; no GPU runtime, no weights
docker-compose.yml    LLM_NAME / LLM_BASE_URL / LLM_API_KEY
technical_report.md   architecture, evaluation, limitations
DATASHEET.md          dataset card

src/
  run.py              the entrypoint make run executes
  eval/               harness: clients, prompts, runners, scoring, judge
  fix/                the method: error taxonomy, target selection,
                      contamination gate, RAG, statistics, charts, narrative
  scripts/            dataset build and verification helpers

data/                 the benchmark datasets and harvested sources
docs/                 plans, baseline notes, submission assets
results/              run artefacts — the evidence behind every number
findings/             issue files
```

### Two findings we would put ahead of the accuracy number

**The obvious fix was contaminated.** The system prompt proposed in the project
plan asserts Swiss facts verbatim. It answers **25 of 84 dev items — 30%**. A
benchmark built that way measures its own prompt. The prompt that ships carries
behavioural rules only, at 0/84, and a gate that *raises* keeps it there.

**Retrieval was never the bottleneck.** 94% recall at k=5 from pure-Python BM25
with zero dependencies is what ruled out installing a dense retriever — decided
before a single model call, and confirmed by the accuracy result afterwards.

---

## Demo video

`brag-output/` is gitignored; the video is uploaded through the submission form.
Its size and SHA-256 are recorded in [`docs/submission/`](docs/submission/) so
the uploaded file can be verified.

---

## Honesty about what did not happen

Three things a reader should know before trusting anything above:

- **No 70B results exist.** The 8B-vs-70B comparison is this project's premise
  and it is half evidenced.
- **The sealed test set was opened 28 times**, recorded in an append-only log.
  Greedy decoding, nothing tuned between runs, but not bit-exact — a long greedy
  decode on a GPU is subject to run-to-run reduction order.
- **The error taxonomy never resolved.** 78% of content errors are
  `UNCLASSIFIED`, so no dominant failure mode is claimed and no weakest-area
  target is named. The tools that would have named one refused, which is the
  point.

`make run` prints all three as disclosures, every time.

# Track 1B — Repository layout and submission readiness

Updated 2026-10-16, after restructuring to the Hack Apertus Track 1B template.

## The required layout

```
README.md             challenge description + submission requirements   DONE
technical_report.md   architecture, evaluation, limitations            DONE
Makefile              `make run` spins the project up                  DONE
src/                  your code                                        DONE
data/                 datasets                                         present (2.0 MB)
findings/             issue files (track_1a only)                      present + explained
docs/                 diagrams, notes, longer write-ups               present
```

Plus, because the template asks for reproducibility:

```
Dockerfile            slim image; no GPU runtime, no weights
docker-compose.yml    LLM_NAME / LLM_BASE_URL / LLM_API_KEY
requirements.txt      3 packages, two of them optional
DATASHEET.md          dataset card
LICENSE               Apache-2.0 (code) / CDLA-Permissive-2.0 (data)
results/              run artefacts — the evidence behind every number
```

## Where things moved

| Was | Now |
|---|---|
| `eval/` | `src/eval/` |
| `fix/` | `src/fix/` |
| `scripts/` | `src/scripts/` |
| `eval/results/` | `results/` |

`results/` is at the repository root rather than under `src/`: code belongs in
`src/`, and results are outputs. Burying them inside the source tree made them
look like source and would have put generated JSON under the tree the Dockerfile
copies.

History is preserved — every move was a `git mv`, so `git log --follow` works
on each file.

## How the restructure was made safe

Sixty modules computed the repository root by counting directory levels:

```python
ROOT = Path(__file__).resolve().parent.parent     # true at eval/, false at src/eval/
```

Moving the code would have broken all sixty. Rather than hand-editing sixty
path expressions, each became a single depth-independent line:

```python
ROOT = next(p for p in Path(__file__).resolve().parents
            if (p / "data").is_dir() and (p / "Makefile").is_file())
```

One line in, one line out, and 60 downstream `ROOT / "..."` uses keep working.
The marker is `data/` **and** `Makefile/`, so it cannot anchor on a directory
that happens to share a name.

## `make run`

```
make run      Docker, offline by default
make verify   the same checks, no Docker
make test     13 suites, 11,540 checks
make shell    container with the project mounted
make help     all targets
```

Offline by default is a deliberate design decision, not laziness. The
benchmark's most defensible claim needs no model at all — retrieval recall is
measured against ground truth over all 84 dev items — and the held-out results
are *shipped* rather than reproduced, because that set is scored once. So
`make run` on a clean checkout with zero configuration does real work and exits
0.

With a live model it additionally smoke-tests the endpoint:

```bash
export LLM_NAME=Apertus-v1.5-8B-Instruct-Q4_K_M
export LLM_BASE_URL=http://host.docker.internal:8080/v1
export LLM_API_KEY=EMPTY
make run
```

`host.docker.internal`, not `127.0.0.1`: inside the container, loopback is the
container itself. `docker-compose.yml` maps the name for Linux, where Docker
does not provide it by default.

### The configuration layer, and the bug that hiding it would have enabled

The template names three variables. This harness had grown its own
(`APERTUS_8B_*`) first. Both are accepted, with precedence:

1. `APERTUS_<KEY>_*` in the **real** environment
2. `LLM_NAME` / `LLM_BASE_URL` / `LLM_API_KEY` in the **real** environment
3. `APERTUS_<KEY>_*` from `src/eval/.env`
4. defaults

Order 2 above 3 is the whole point. A developer's stale `src/eval/.env` was
defeating the variables judges set: `LLM_BASE_URL` came through, `api_base` came
out right, and the backend stayed `mock` — a run that looked configured and was
quietly evaluating synthetic responses. `load_dotenv` fills gaps with
`setdefault`, which makes a file-sourced value indistinguishable from a real one,
so the keys it supplied are now recorded and treated as lower precedence.

Two smoke checks pin this down, both driving a subprocess with a stripped
environment so they cannot pass by accident.

---

## Verification

Everything below was run from a **clean `git ls-files` checkout** in a
temporary directory — not from the development tree, which has artefacts the
clone does not. That distinction caught four bugs that were invisible at home:

| Bug | Only visible on a clean checkout because |
|---|---|
| The RAG corpus is derived and gitignored, so absent | every retrieval call raised `FileNotFoundError` |
| The dev-split results are derived and gitignored, so absent | four CLI assertions never reached the code under test |
| A test asserted a derived artefact "still exists" | it is correctly absent from a clone |
| The smoke test treated an unreachable endpoint as a harness failure | no `.env` and no server on a fresh clone |

The last one is the one that mattered most for the judge experience: `make test`
came out **red** on a fresh clone because there was no model to talk to. An
unreachable endpoint is now a **skip** with the reason stated; a protocol or
parse failure is still a **FAIL**.

Final state from the clean checkout:

- `python src/run.py` → all checks passed, exit 0, two disclosures printed
- 13 suites → all pass
- every local link in `README.md` and `technical_report.md` resolves

---

## Outstanding, and not fixable from here

| # | Issue |
|---|---|
| **B3** | **No 70B results exist.** Every arm is 8B. The 8B-vs-70B comparison is the project's premise and it is half evidenced. Disclosed in `README.md`, `technical_report.md` §5, and printed by `make run` every time. |
| **B5** | No human has scored the 15 blind cross-check items. The values arm is self-judged and unaudited. Not delegable to a model. |
| **B1** | All 30 dialect items carry `validated_by: null`. No native Alemannic speaker has reviewed them. |
| — | The error taxonomy left 78% of content errors `UNCLASSIFIED`, so no dominant failure mode is claimed and no weakest-area target is named. By design — `select_target.py` refuses with all three gates firing. |
| — | The sealed test set was opened 28 times (append-only log). Greedy decoding, nothing tuned between runs, but not bit-exact. |
| — | `make run` itself was not executed here: neither `make` nor `docker` is installed on this machine. The Dockerfile, `docker-compose.yml` and `Makefile` were validated structurally (COPY targets exist, YAML parses, every command resolves) and `src/run.py` — which is what the container runs — was executed directly from a clean checkout and from an unrelated working directory. |

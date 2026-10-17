# Changelog — Swiss Reality Check, Track 1B

Every entry is a change that altered the submission's evidence, not its wording.
The governing rule: **a number that is stated anywhere must be derived from the
artefacts it describes.** Most of the work below exists because that rule was
violated and the violation was found by a scan rather than by reading.

---

## The headline change

| | Before (superseded) | After (current) |
|---|---|---|
| Corpus | 120 MCQs | **300 MCQs** (50 per category) |
| Distinct sources | 55 (of a 100-source harvest) | 55 |
| Split | 84 dev / 36 sealed | **210 dev / 90 sealed** |
| Answer letters | 30/30/30/30 | **75/75/75/75** |
| Detection floor (overall) | +16.7 pp | **+6.7 pp** |
| Detection floor (per category) | +16.7 pp at n=6 | **+40.0 pp at n=15** |
| Sealed baseline | 55.6 % (20/36) | **51.1 % (46/90)** |
| Sealed BM25 RAG k=3 | 86.1 % (31/36) | **86.7 % (78/90)** |
| Delta | +30.6 pp, CI [+13.1, +30.6] | **+35.6 pp, CI [+25.1, +39.5]** |
| Paired | 11 improved / 0 regressed, p=0.001 | **34 improved / 2 regressed, p<0.001** |
| Retrieval recall @1/3/5 | 83.3 / 90.5 / 94.0 % | **82.4 / 91.4 / 92.9 %** |
| Categories clearing their own floor | 0 of 6 | **3 of 6** (geography, history, politics) |
| Sealed SHA-256 | `df819e8c…` | **`83c20589e1c5b668…`** |

The previous arms are **kept** at `results/test_run/*.superseded-n36.json` rather
than deleted, so the supersession is auditable. `src/scripts/promote_arm.py`
refuses to promote an arm containing parse errors rather than silently scoring them
as wrong.

---

## 1. Corpus scaled 120 → 300

300 MCQs, exactly 50 per category, all six categories balanced. Every item carries
a verbatim quote traceable to one of 55 distinct official sources; 300/300 verified.
Difficulty 60 easy / 148 medium / 92 hard. Answer letters balanced 75/75/75/75 across
the whole corpus.

*Fixed along the way:* **K108** was marked C (Obwalden) while its own source and notes
said D (Appenzell Innerrhoden). The old baseline had predicted D and was therefore
scored as *wrong* on a correct answer — a false negative that flattered the RAG delta.
**K264** was reframed so its undated 2,110-commune snapshot cannot be confused with
K070's dated 2,121 figure.

`verify_knowledge.py` emits one informational near-duplicate warning (K117/K282).

## 2. Re-split and re-sealed at 210/90

Stratified 70/30 with exactly 15 sealed items per category, which is what makes the
per-category paired comparison possible at all. New seal hash `83c20589…`.

Corpus sizes are now **derived** from the split files throughout the codebase
(`build_knowledge.py`, `seal.py`, `statistical_report.py`, `baseline_report.py`,
`run.py`, `published_claims.json`), which is why a rescale did not require editing
a dozen `assert`s.

## 3. A parser bug was understating the baseline by 26 points

Served completions ended with an end-of-turn marker rendered as visible text. The
parser did not recognise the marker unless it was pipe-terminated, so **49 of 90**
sealed baseline answers came back `PARSE_ERROR` and were scored as wrong. The raw
baseline was **27.8 %**, not 51.1 %.

`strip_control_markers()` now handles the marker without a closing pipe. Rescoring
from the saved raw responses — no new generation — gives 0/90 parse errors and
**51.1 %**.

This is why the new baseline (51.1 %) is *lower* than the old one (55.6 %) despite a
corpus 2.5× larger, and it is the single most important correctness fix in this
changelog: the previous headline was partly measuring a parser, not a model.

## 4. Both arms now come from one paired invocation

The control and RAG arms are produced by a single `run_rag_eval.py` run, so they
share one generation context. A McNemar test assumes both arms saw the same
questions under the same conditions; taking the control from a separate run is
exactly the confound the pairing exists to rule out.

## 5. The stale-figure class of bug, and the systematic fix

A repo-wide scan for the previous numbers returned **223 hits**. Most were
legitimate — historical plan records, comments explaining the old values, test
fixtures, the deliberately-archived n=36 arms. But the *live* ones were severe:

- the submitted **6-page PDF** carried the whole n=36 headline table;
- the **dataset card** published to Hugging Face carried it too;
- the chart annotation and the retrieval subtitle said **94 %** recall and
  **n=84 dev items** when the real figures were 92.9 % and 210;
- the narrative still reported the detection floor for n=36;
- the narrative selected scenario **"pending"** because it had no model results to
  read — it now selects **"A — Strong improvement"**.

**The fix is structural, not editorial.** `src/scripts/submission_numbers.py` is now
the single loader for every number a submission asset prints; `retriever.recall_figure()`
is the single source for retrieval recall. Both submission builders, both chart
annotators, the narrative and the dataset card read from them. Hardcoding a figure
in an asset is no longer possible without editing a loader.

Two follow-on bugs were caught by scanning the *rebuilt* PDF for `{PLACEHOLDER}`
tokens, which found 12 string literals that had been given `{...}` references without
being converted to f-strings — i.e. the PDF was about to ship literal
`{BASE_ACC}` to a judge.

## 6. Power analysis, recomputed

The detection floor is computed, not asserted. At n=90 a paired change needs 6
improvements with **zero** regressions (+6.7 pp). Per category at n=15, only a clean
6/0 sweep is detectable (+40.0 pp) — anything with a regression is undetectable.

Consequence for the write-up: **3 of 6 categories clear their floor**
(geography +46.7, history +40.0, politics +53.3 pp); health, law and services are
reported as *no detectable change*, not as small gains. No category is ranked.

## 7. Official model restored

The official `swiss-ai/Apertus-v1.5-8B` checkpoint was downloaded and converted
locally: `models/Apertus-v1.5-8B-text-Q4_K_M.gguf`, 5.01 GB, served on
`127.0.0.1:8081`→`8080`. `serve_task.cmd` now preflights the model file and fails
loudly instead of restarting every 3 seconds.

## 8. Repository layout flattened

`eval/results/` scratch moved to `results/{raw_responses,parsed,scores,logs}`
(gitignored); published artefacts live in `results/`. `track_1b/` is gone — the
project is addressed from the repository root. This broke
`upload_hf_dataset.py`, which still pointed at `eval/results/final_scores/…` and
silently staged **without** the statistical report and scores; found and fixed.

## 9. Integrity disclosures

- **Seal audit trail is incomplete.** The n=90 seal was frozen at 06:46:56 UTC. The
  log holds 60 entries: 55 predate the freeze (superseded seal), 5 postdate it — and
  **none is timestamped at the 06:59:59 UTC recorded in both archived arms**. The
  headline run is therefore absent from the audit trail, and the 5 post-freeze
  entries are all RAG-side; no `baseline` access to the new seal is recorded.
  Cause: logging was added to the runners *after* they had already been driven
  through them. The log was **not** backfilled. Stated in `technical_report.md` §5.
- **Values are self-judged** (8B judge, no human agreement rate yet).
- **Non-determinism.** Greedy decode at T=0/seed 42 is not bit-exact on GPU.
  Independent values reruns gave mean 1.096 (sealed prompt 1.0) and 1.068.
- **Dialect is unvalidated** — awaiting native-speaker sign-off (B1).
- **Only 8B has results.** No 70B numbers exist anywhere.
- **No dev run exists at n=210.** The dev split grew but was not re-run, so the
  sealed test set is the only current measurement. The dev→test transfer figure is
  therefore *not* drawn; `fig3` renders only the measured arm and says why.

---

## Files touched, by purpose

| Purpose | Files |
|---|---|
| New loaders (stale-number fix) | `src/scripts/submission_numbers.py`, `src/eval/…/retriever.recall_figure()` |
| Arm promotion + guard | `src/scripts/promote_arm.py` |
| Parser fix + seal logging | `src/eval/run_knowledge.py`, `src/eval/rescore.py`, `src/fix/rag/run_rag_eval.py` |
| Derived split sizes | `src/eval/generate_charts.py`, `src/eval/narrative.py`, `src/eval/statistical_report.py` |
| Asset builders | `src/scripts/prepare_submission_assets.py`, `src/scripts/build_submission_pdf.py`, `src/scripts/upload_hf_dataset.py` |
| Corpus | `data/knowledge/*`, `data/sources/README.md` |
| Docs | `README.md`, `technical_report.md`, `DATASHEET.md`, `src/eval/README.md`, `src/fix/rag/RESULTS.md`, `src/fix/comparison.md` (banner), `docs/plans/phase_7.md`, `docs/plans/track_1b_gap_analysis.md` |
| Regenerated | `results/final_scores/*`, `results/charts/*`, `results/narrative/findings.md`, `results/test_run/*`, `docs/submission/**`, `swiss_reality_check_report.pdf` |

## Not done, and why

| Item | Status |
|---|---|
| Human agreement on 18 knowledge + 15 values items | **needs the human** |
| Native Swiss German validation (B1) | **needs a native speaker** |
| ISO-639-3 glottocodes; consent-template / not-applicable docs | outstanding |
| Dev-split run at n=210 | not run — sealed test is the current measurement |
| 70B arms | out of hardware scope (8 GB VRAM) |
| Hackathon submission upload | **needs the account holder** |
# findings/ — issue files

**The Hack Apertus template scopes this directory to Track 1A ("issue files").
This project is Track 1B, so it is not a required deliverable and there are no
judging-scored issue files to place here.**

The directory is kept, empty, with this note, so the layout matches the template
and so its absence is visibly deliberate rather than an oversight.

## Where the project's findings actually live

Track 1B has no "issues" to file. What exists instead is the analysis of *what
the benchmark found about the model*, and those artefacts live with the
evidence they are derived from:

| What | Where |
|---|---|
| The story — five acts, findings, limitations | [`results/narrative/findings.md`](../results/narrative/findings.md) |
| Every number, with confidence intervals | [`results/final_scores/statistical_report.md`](../results/final_scores/statistical_report.md) |
| Machine-readable statistics | [`results/final_scores/test_scores.json`](../results/final_scores/test_scores.json) |
| Per-item rows, raw responses, provenance | [`results/test_run/`](../results/test_run/) |
| The figures | [`results/charts/`](../results/charts/) |
| Deeper write-up | [`technical_report.md`](../technical_report.md) |

## Open issues that a maintainer would actually file

These are real and unresolved. They are listed here rather than filed because
Track 1B does not use this directory, and an issue list kept in a directory
nobody reads is worse than one kept where the limitations are.

| # | Issue | Blocks |
|---|---|---|
| **B1** | No native Alemannic speaker has validated any dialect item. All 30 carry `validated_by: null`. | Publication of the 53 language renderings; the dialect pillar's validity |
| **B2** | *(resolved 2026-10-16)* Apertus-8B is running locally via the Q4_K_M GGUF on an RTX 5060. | — |
| **B3** | No 70B route. **Every result in this repository is 8B.** | The 8B-vs-70B comparison, which is the project's premise; the cross-judge for the values arm |
| **B5** | No human has scored the 15 blind cross-check items. | The values agreement rate; the values arm is self-judged and unaudited |
| — | The error taxonomy left 78% of content errors `UNCLASSIFIED`, so no dominant failure mode is claimed and no weakest-area target is named. | Phase 3's improvement routing, by design — the tools refuse rather than guess |
| — | The sealed test set was opened 28 times (logged, append-only). | Exactness of the numbers, though not their validity |

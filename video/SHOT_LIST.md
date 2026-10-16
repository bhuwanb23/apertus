# SHOT LIST — Swiss Reality Check demo (2:30 screen recording + VO)

Prep sheet for the recorder. Nothing here has been recorded yet.
Pace reference: `video/script.md` — 346 spoken words, 2:29 at 140 wpm.

---

## 1. Pre-load checklist (do this BEFORE hitting record)

Everything on this list must already be open, scrolled to the right place, and cached.
Never navigate, never open a file, never start a run on camera.

| # | Screen | What to show | Notes |
|---|---|---|---|
| 1 | **Terminal** | Repo root prompt, large monospace | Prompt visible, no scrolling. No command runs live. |
| 2 | **VS Code** | `data/knowledge/knowledge_dev.json` | One knowledge question expanded: `question`, all 4 `options`, `correct_answer`, `source_url`. **Highlight `source_url`.** Tab size 2, font ≥ 18pt. |
| 3 | **Browser (tab 1)** | `eval/results/charts/fig1_overall_accuracy.svg` | Full-width, 100% zoom, white background. Chance line visible. |
| 4 | **Browser (tab 2)** | `eval/results/charts/fig3_dev_to_test.svg` | Dev → test bars. |
| 5 | **Browser (tab 3)** | `eval/results/charts/fig2_category_intervals.svg` | **The point of this shot is the intervals crossing zero.** Leave it on screen. |
| 6 | **Browser (tab 4)** | `eval/results/charts/fig4_retrieval_recall.svg` | top-1 / top-3 / top-5 recall. Optional, use if time allows. |
| 7 | **Terminal** | `fix/rag/` retriever already run, output parked | **Pre-run and freeze the output.** Do NOT run the retriever live — it takes time and may fail. A prerecorded clip is fine. |
| 8 | **Browser (tab 5)** | GitHub repo tree for `apertus` | Scroll once, slowly. |
| 9 | **Any** | Title card: `Swiss Reality Check` / `Hack Apertus · Track 1B` | Final fade target. |

> **Chart filenames are exact and real.** They are SVG, at
> `eval/results/charts/fig1_overall_accuracy.svg`, `fig2_category_intervals.svg`,
> `fig3_dev_to_test.svg`, `fig4_retrieval_recall.svg`.
> A plan file elsewhere in the repo references PNG names — **those files do not exist. Ignore them.**
> Open the `.svg` files directly; Chrome/Edge/Firefox all render them. Use a light-on-dark or white background, not inverted, so labels stay legible.

### Never show on camera

- `data/knowledge/knowledge_test.json` — do not open it, do not screenshot it.
- Any screen containing `sealed test set SHA-256` or the append-only access log **except** during the deliberate disclosure beat at 2:10 (see §4).
- The values score `1.096 / 2.0` — **unless** the label `self-judged — 8B judged 8B` is on screen simultaneously.

---

## 2. Recording settings

| Setting | Value |
|---|---|
| Resolution | **1920 × 1080**, 60 fps (30 fps acceptable) |
| Aspect | 16:9 |
| Recorder | **OBS Studio** — Display Capture / Window Capture. Windows Game Bar (`Win+Alt+R`) is the fallback if OBS install is slow. |
| Capture area | Single monitor, taskbar visible, clock covered |
| Window | Recorder window and any app being recorded on the **same** screen unless you have a second monitor |
| Terminal font | ≥ 20pt monospace, colour scheme with real contrast |
| VS Code font | ≥ 18pt, zoom to 110–125% |
| Browser zoom | 100%, or 125% for the SVGs if axis labels are small |
| Microphone | Wired/lavalier > built-in. Test level peaks at −12 dB, no clipping. |
| Room | Quiet. Kill fans/Dish if the laptop is fan-heavy; fan noise ruins VO. |
| Do Not Disturb | On. Notifications off. Phone in another room. |

### Warm-up (5 min, before the real take)

1. Record 20 s of VO silence and 20 s of speech — check levels.
2. Rehearse the four numbers that matter: **55.6**, **86.1**, **+30.6**, **p = 0.001**. Say them out loud twice.
3. Do one throwaway take. Never use take 1.

---

## 3. Per-section shot plan

| Time | Section | Screen | Action | VO beat |
|---|---|---|---|---|
| 0:00–0:12 | HOOK | Terminal → dataset question | Static terminal frame. Hard cut to one question, full frame, options visible. Hold still. | "names a European institution… Fluent. Confident. Completely wrong." |
| 0:12–0:25 | BENCHMARK | VS Code `knowledge_dev.json` | Slow scroll **upward** through the file, stop on one question. | "120 multiple-choice questions across six categories" |
| 0:25–0:40 | BENCHMARK | Same, zoom to `source_url` | Highlight/underline the URL field. | "every distractor is a real answer from Germany or the EU" |
| 0:40–0:55 | FINDING | `fig1_overall_accuracy.svg` | Static. Point at the 55.6 bar and the 25% chance line with the cursor. | "fifty-five point six percent… chance is twenty-five" |
| 0:55–1:10 | FINDING | `fig1_overall_accuracy.svg` (hold) → or a simple text card "30 dialect items · 15 refused" | If using a card, it must read: **30 items · 15 refused or not understood · MCQ 50% · free translation 0.0/2.0** | "on fifteen of them — half — it refused" |
| 1:10–1:30 | FIX | Terminal, `fix/rag/` | Frozen output. Highlight one retrieved chunk and its source label. | "top three retrieved chunks ninety point five percent of the time" |
| 1:30–1:45 | FIX | Same | Cursor moves from chunk → into prompt. | "Plain BM25… no fine-tuning… works on any model" |
| 1:45–2:00 | RESULT | `fig3_dev_to_test.svg` → `fig1_overall_accuracy.svg` | Dev bars first, then cut to the overall chart. | "reserved test set… 86.1… plus thirty point six points" |
| 2:00–2:10 | RESULT | `fig2_category_intervals.svg` | **Hold. Let the viewer see the intervals crossing zero.** No pointer. | "every interval crosses zero — so we claim no category" |
| 2:10–2:20 | CLOSE / disclosure | Repo tree, then a disclosure card | Disclosure card text, verbatim: **"The sealed test set was opened ~27 times (runner bug). Reserved until the improvement was frozen. Every access is in the append-only log."** | "the sealed test set was opened more than once… a runner bug" |
| 2:20–2:30 | CLOSE | GitHub repo tree → title card | One slow scroll. Fade to `Swiss Reality Check` card. | "all open source. Reusable for any country." |

---

## 4. Mandatory disclosure beat (2:10)

This is not optional. The disclosure card must be on screen for the full spoken line, and the
line must be in the VO. Cutting it is the one edit that makes the video wrong.

On-screen text, verbatim:

```
DISCLOSURE
Sealed test set opened ~27 times (runner bug), against a single-shot design.
It was reserved until the improvement was frozen; the log records every access.
Greedy decoding (temp 0.0, seed 42) — repeats are reproduction attempts, not a search.
```

---

## 5. Edit checklist

**Content integrity — check these before export, every time**

- [ ] **No mention of 70B** anywhere: VO, titles, cards, captions, description. 70B was dropped, not approximated. Zero cross-model or cross-scale claims.
- [ ] **"Opened once" / "one shot"** appears nowhere. The disclosure beat (§4) is present and holds for its full duration.
- [ ] **No dominant error mode** is claimed or implied. Never surface `fix/error_taxonomy.md` — it carries a MOCK BACKEND banner and is unresolved.
- [ ] **No per-category win.** `fig2_category_intervals.svg` is shown *for the intervals crossing zero*. No category is named as stronger or weaker. No leaderboard, no highlighting of a single bar.
- [ ] **Values:** either not mentioned, or `1.096 / 2.0` appears only with `self-judged — 8B judged 8B` on screen at the same time.
- [ ] `data/knowledge/knowledge_test.json` is never visible.
- [ ] Numbers on screen match the VO exactly: 55.6 / 86.1 / +30.6 / 11 improved / 0 regressed / p=0.001 / 48.8→83.3 dev.
- [ ] All four figures shown are consistent: it is the **8B** model, and the setup is described only as "running locally". No hardware or quantisation detail is spoken.

**Craft**

- [ ] Cut on the beat, not mid-word. 6–10 frames of handle on each cut.
- [ ] Add a lower-third naming the section at 0:12 / 0:40 / 1:10 / 1:45 / 2:10 — helps a judge follow a 2:30 video.
- [ ] Background music at −24 LUFS under VO, ducked on VO entry. Never over the disclosure card.
- [ ] Total duration **2:25 – 2:35**. Trim from the BENCHMARK section first if long; never from the disclosure beat.
- [ ] Audio: no clipping, no room echo, VO peaks around −12 dB.
- [ ] Captions burned in (judges watch muted).
- [ ] Export: H.264 MP4, 1080p, AAC 48 kHz stereo. Filename `swiss-reality-check-demo.mp4`.

**Description / submission copy**

- [ ] Short description repeats: benchmark, corpus, harness, pipeline, all open source.
- [ ] Link to the repo and to `eval/results/narrative/findings.md`.
- [ ] Include the disclosure in the description text too — one sentence: *"The sealed test set was opened more than once (~27) due to a runner bug; it was reserved until the improvement was frozen and every access is in the append-only log."*
# Swiss Reality Check — Demo Voiceover Script

**Hack Apertus · Track 1B "Swiss Voices"**
Target runtime: **2:30** · Pace: **140 wpm** · Spoken word count: **352** (= 2:31)
Read at a calm, unhurried pace. `[SCREEN:]` cues are for the editor, not spoken.

Every number below is traceable to a run in `eval/results/`. Do not ad-lib numbers.

---

## 0:00 – 0:12 · HOOK

`[SCREEN: Terminal, one static frame, 40pt monospace. Hard cut to a single dataset question filling the frame.]`

> Ask a Swiss model how Switzerland cooperates with NATO — it isn't a member — and it names a European institution, not the Swiss one.
>
> Fluent. Confident. Wrong.
>
> You'd never know.

## 0:12 – 0:40 · THE BENCHMARK

`[SCREEN: Scroll `data/knowledge/knowledge_dev.json` in VS Code — stop on one question, expand it, show all four options and the `source_url` field. Highlight the URL.]`

> So we built a benchmark where being wrong is visible. This is Apertus 1.5 8B, running locally.
>
> A hundred and twenty multiple-choice questions across six categories. Every answer checked against a quoted official Swiss government URL. Every distractor is a real answer from Germany or the EU.
>
> Thirty values scenarios in five languages — German, French, Italian, Swiss German, Romansh. Thirty dialect items.

## 0:40 – 1:10 · THE FINDING

`[SCREEN: Browser, `eval/results/charts/fig1_overall_accuracy.svg` — the 55.6% bar against the 25% chance line.]`

> On the held-out test set, baseline accuracy was fifty-five point six percent. Chance on four options is twenty-five. So that's real signal — the model does know a lot of this.
>
> But the dialect arm. Thirty Swiss German questions, and on fifteen — half — it refused, or didn't understand the sentence at all. On the ones it did answer as multiple choice: half right. Free translation: zero out of two.

## 1:10 – 1:45 · THE FIX

`[SCREEN: `fix/rag/` — retriever output already on screen. Highlight one retrieved chunk and its source label going into the prompt.]`

> First we measured where the answer already was. On dev, the correct source was in the top three retrieved chunks ninety point five percent of the time.
>
> So the fix is retrieval. Plain BM25 — pure Python, no GPU — pulling relevant passages from the harvested official Swiss corpus, each labelled with its source, handed to the model before it answers.
>
> No fine-tuning. No bigger model. It works on any model.

## 1:45 – 2:10 · THE RESULT

`[SCREEN: `fig3_dev_to_test.svg`, then `fig2_category_intervals.svg` — the intervals visibly crossing zero. Do not linger on any single category.]`

> Designed on dev: forty-eight point eight to eighty-three point three. We froze it, then moved to a test set reserved until the improvement was finished.
>
> On that set: fifty-five point six to eighty-six point one — plus thirty point six points. Eleven improved, zero got worse, exact McNemar p equals zero point zero one.
>
> And per category, every interval crosses zero. We claim no category.

## 2:10 – 2:30 · THE CLOSE

`[SCREEN: GitHub repo tree, one slow scroll. Fade to the title card.]`

> Full disclosure, because it should be. The sealed test set was opened more than once — about twenty-seven times — because of a runner bug. It was reserved until the improvement was frozen, but the log records every access.
>
> Benchmark, corpus, harness, pipeline — all open source. Reusable for any country.

---

## Timing summary

| Section | Window | Words | ≈ @140 wpm |
|---|---|---|---|
| HOOK | 0:00–0:12 | 31 | 0:13 |
| THE BENCHMARK | 0:12–0:40 | 63 | 0:27 |
| THE FINDING | 0:40–1:10 | 71 | 0:30 |
| THE FIX | 1:10–1:45 | 71 | 0:30 |
| THE RESULT | 1:45–2:10 | 65 | 0:28 |
| THE CLOSE | 2:10–2:30 | 51 | 0:22 |
| **Total** | **2:30** | **352** | **2:31** |

If the read runs long, cut from THE BENCHMARK first — never from the disclosure beat.

## Claims deliberately NOT made

Do not add these even if asked on camera. Each is ruled out by the evidence:

- **No 70B / no cross-model or cross-scale comparison.** 70B was dropped (VRAM), not approximated. Scale is future work only.
- **No "opened once" / "one shot".** Say "reserved until the improvement was frozen", and disclose the ~27 opens.
- **No dominant error mode.** The error taxonomy is MOCK-BACKEND generated and unresolved (78% UNCLASSIFIED). Never say "NUMERIC is the top failure".
- **No per-category wins.** n=6 per category; every interval crosses zero. This line *is* the honest version of the per-category table.
- **No values score.** If the `1.096 / 2.0` figure is ever shown, the label **"self-judged — 8B judged 8B"** must be on screen at the same time.
- **No "the model doesn't know Swiss things".** The claim is narrower and stronger: retrieval closed a +30.6 pp gap.
- **The hook is a real, recorded baseline error** (dev item K104: the model answered "Partnership for Peace and the Western European Union"; correct is the Euro-Atlantic Partnership Council). Live backend, `is_mock: false`. It also improved under retrieval, so the story closes.
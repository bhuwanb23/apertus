# Source Corpus — "Swiss Reality Check"

**Phase 1A.1 · Source Harvesting · Complete**

> **Addendum — S058, Alemannic Wikipedia (dialect).** A 15th source family, `S058`, was harvested from
> `als.wikipedia.org` (CC BY-SA 4.0): **14 articles, 134 verbatim Swiss German sentences, 135 fact
> candidates.** It is the corpus's only Swiss German text and its only cultural material. All 14 files
> declare `SOURCE_ID: S058` and are named
> `raw_pages/S058_alemannic_wikipedia_institutions_<topic>.txt` (a multi-file source — see the registry row).
>
> | | |
> |---|---|
> | Verbatim integrity | Every sentence machine-verified as an exact contiguous substring of the rendered article. **134/134 pass.** |
> | Translations | Authored, unvalidated, and labelled as such in every file. |
> | Dialect | `basel` 4 files (only `Basler Fasnacht` declares `{{Dialekt|Baseldeutsch}}` explicitly), `zürich` 2 files (both declare `{{Dialekt|Zürichdeutsch}}`), `uncertain` 8 files (no template; Basel-leaning orthography but not attributable). **Alemannic Wikipedia is not uniformly Basel-leaning** — do not assume `DIALECT: basel` as a default. |
> | Word count | Hard rule "never tidy" outranks the 6–20 word target: 45 sentences exceed 20 words because their Alemannic clauses cannot be dropped without breaking contiguity. Each file carries a `=== WORD-COUNT NOTES ===` section enumerating them. |
> | Cross-reference value | 73 fact candidates cross-reference **23 distinct** existing sources (S001, S002, S003, S004, S005, S006, S008, S008b, S012b, S018, S025, S026, S028, S029, S030, S032, S033, S037, S038, S040, S047, S048, S049) — these are the dialect-decodes-a-fact items. |
> | Novel facts | Carnival/Fasnacht culture, Landsgemeinde practice, the 1918 Landesstreik, Zwingli/Reformation, the Idiotikon, plus institutional facts absent from the English corpus: the Swiss federal monopolies (Regale), the federal "intervention" (eidgenössische Intervention), the Bundesratsparteien magic formula, the 1974 Jura observers, and metric weights only from 1877. |
> | Known open gap | `Bundesverfassung (Schweiz)` exists on als.wikipedia and is the correct source for Swiss constitutional fact content; it was not harvested (`Verfassung` turned out to be a translated German concept article). Fetch next if constitutional coverage is needed. |

| | |
|---|---|
| Sources harvested | **100** (target was 30–40) |
| Verified fact candidates | **933** (+461 Swiss German sentences) |
| Target questions (Phase 1A.2) | 120 MCQs, 20 per category |
| Capacity ratio | **~3.9 facts per question** — comfortably sufficient |
| All URLs fetched | HTTP 200 verified on 2026-10-12; +45 dialect sources in Phase 1C |

## Files

| Path | Contents |
|---|---|
| `source_registry.csv` | Master index. Columns: `source_id,url,title,category,language,date_accessed,notes,fact_count,raw_file` |
| `raw_pages/*.txt` | One file per source: header metadata, verbatim quotes, numbered fact candidates with evidence quotes, MCQ notes |
| `verification_log.md` | Corrections to pre-existing plan assumptions, and documented open gaps |

## Trust tiers

Every source was fetched and read. Only 10 of 52 come from non-ministerial bodies, and each is labelled.

| Tier | Sources | Domains |
|---|---|---|
| **A — Federal ministry / agency** | 17 | `sem`, `bag`, `bsv`, `bafu`, `bazg`, `bk`, `bar`, `bger`, `edoeb`, Canton Bern conciliation authority |
| **B — Official citizen portal** | 27 | `ch.ch` (Federal Chancellery service of the Confederation, cantons and communes) |
| **C — Non-ministerial** | 11 | `myswitzerland.com` (SRG/federation), `swissinfo.ch` (SRG SSR), `ch-info.swiss` (Federal Chancellery publication, web edition), `icrc.org`, `ethz.ch` |

**Caveat on Tier C:** these were substituted because the primary sources were unavailable to automated fetching. `eda.admin.ch`, `admin.ch` and `bger.ch` HTML pages return HTTP 403 to automated requests. Where a Tier C source is used, the facts are cross-checked where possible and the file records which. For a strict tier-A-only benchmark, drop S027–S030, S043, S048–S050, S055 (11 sources, 80 facts) — coverage remains above target.

## Category balance

| Category | Sources | Facts | Primary domains |
|---|---|---|---|
| politics | 14 | 125 | ch.ch, bk.admin.ch |
| history | 10 | 75 | bar.admin.ch, bk.admin.ch, bger.ch, icrc.org |
| law | 8 | 79 | ch.ch, sem.admin.ch, be.ch |
| health | 7 | 71 | ch.ch, bsv.admin.ch, bag.admin.ch |
| geography | 7 | 50 | ch.ch, myswitzerland, ch-info, swissinfo |
| services | 7 | 56 | ch.ch, bafu.admin.ch, bazg.admin.ch, swissinfo.ch |
| privacy | 2 | 16 | edoeb.admin.ch (added in Phase 1B) |
| **dialect** | **45** | **461** | **als.wikipedia.org (Alemannic Wikipedia, CC BY-SA 4.0)** |

Politics is over-weighted because the direct-democracy cluster (initiative, referendum, double majority, e-voting, voting rights, parliament composition) is both the richest source of hard numbers and the core of the benchmark thesis.

### Dialect tier (added in Phase 1C)

The 45 dialect sources are **not** government pages. They are the **Alemannic Wikipedia** (ls.wikipedia.org), a free encyclopedia in Swiss German written by native speakers, covering Zürich, Bern, Basel, Aargau and Walser German. They were added because the dialect pillar needs *Swiss German text*, and the only trustworthy source of that is native-authored text with a stable URL. Each carries a dialect label and a DIALECT_EVIDENCE header; 8 files are honestly marked DIALECT: uncertain and are excluded from per-dialect claims. Two articles were harvested by two agents and exist twice (Fasnacht, Schweiz), so item provenance is resolved by content match rather than by URL. See data/dialect/dialect_pilot_note.md.

## Caveat flags (encoded in `notes`)

| Flag | Count | Meaning for question drafting |
|---|---|---|
| `CANTONAL-VARIABLE` | 19 | Fact differs by canton. **Never** phrase the question as if the federal rule were universal. |
| `COMMUNAL-VARIABLE` | 3 | Varies by municipality. Same rule. |
| `REGIONAL-VARIABLE` | 4 | Varies by language region. |
| `TIME-SENSITIVE` | 2 | Figure is year-locked. State the year in the question. |
| `PREMISE-CORRECTED` | 7 | Harvest contradicted an assumption. See `verification_log.md`. |
| `NON-EN:de` | 1 | S044 is German-language; quote is translated and marked. |
| `SHARED-PAGE` | 8 | URL reused across two categories (4 pairs). |
| `MULTI-PAGE` | 4 | Topic spanned a second official page, recorded as `SUPPLEMENT_URL`. |

## Facts deliberately NOT recorded

Per golden rule 1, no fact was created without a verifiable quote. The following were requested during harvesting and **could not be confirmed on any accessible official page** — they are therefore absent, not guessed:

- Accident insurance (UVG) salary threshold for compulsory employer cover.
- A codified "Federal Act on Safeguarding Switzerland's Neutrality" — accessible sources state neutrality is anchored in international law and was never codified in a statute. Recording it would have contradicted the sources.
- Which specific cantons border which specific country (only per-country border lengths were published).
- Max weekly working hours as a single national figure (appears only in sector-specific collective agreements).
- Precise franchise band eligibility by age or rural residence — the sources show deductible choice is **voluntary**, not rule-bound.

See `verification_log.md` for full detail.

## RAG readiness (Phase 3.3b)

Each `raw_pages/*.txt` is a self-contained, chunkable document: metadata header, verbatim source quotes, then atomic fact candidates each carrying its own evidence quote. A retrieval index over these 100 files gives the Phase 3 RAG pipeline a corpus that is (a) small enough to embed in minutes, (b) already chunk-aligned to one fact per chunk, and (c) traceable — every retrieved chunk points back to a `source_id` and a live official URL.

**Chunk count estimate:** ~447 fact chunks + ~447 quote chunks ≈ 900 chunks. Roughly 90–140k tokens total. A single-pass embedding + FAISS index is sufficient; no chunking strategy beyond the existing file boundaries is required.

## Link verification

The 48 URLs harvested in Phase 1A.1 were re-checked on 2026-10-12; the 3 Phase 1B additions were verified on fetch: **48 / 48 return HTTP 200** (browser user-agent + `Accept-Language` required; all `*.admin.ch` sites reject requests without a browser UA, and `myswitzerland.com` returns 406 without a full header set).

**Reproducing the check** — note the TLS and UA requirements, or you will get false negatives:

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$H = @{
  "User-Agent"="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
  "Accept"="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
  "Accept-Language"="en-GB,en;q=0.9"
}
(Import-Csv data\sources\source_registry.csv).url | Select-Object -Unique | ForEach-Object {
  try { "{0}  {1}" -f [int](Invoke-WebRequest $_ -Headers $H -UseBasicParsing -TimeoutSec 45).StatusCode, $_ }
  catch { "FAIL  $_" }
}
```

## Reproducing

Each file header records the exact working URL. 22 URLs from the original plan are dead, 403-blocked, 406-blocked, or JS-shell-only and were replaced during harvesting — see `verification_log.md` §2.

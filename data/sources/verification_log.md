# Verification Log — Phase 1A.1 Source Harvesting

Two jobs: record what **contradicted** the pre-existing plan (so the errors do not propagate into the MCQ set), and record what remains **unverified** (so the datasheet can state honest limitations).

---

## 1. Factual corrections — assumptions that were WRONG

These were assumptions carried into `docs/plans/phase_1.md`. Harvesting against official sources contradicted all five. **They must not be reused as question stems or distractors.**

### 1.1 Tenancy notice period is three months, not one month

- **Plan said:** "Tenancy notice periods (typically 3 months, specific dates)" in the category guide, and the Phase 1A.1 table said "notice periods" — but the *drafting guidance* implied a one-month rule.
- **Official source (S044, Canton Bern conciliation authority, German):** "In einem Mietvertrag muss die Kündigungsfrist **mindestens drei Monate für Wohnräume** und sechs Monate für Geschäftsräume betragen." Minimum three months for residential, six for commercial. It can be extended by contract, never shortened.
- **Also corrected:** there is **no universal "give notice by the end of the month" rule**. The source states "die ortsüblichen Kündigungstermine" — the *locally customary* termination dates. The termination date is therefore locally variable.
- **Implication:** any question on notice periods must either state the residential/commercial distinction or be flagged cantonal-variable.

### 1.2 Health insurance deductibles are voluntary bands, not rule-assigned

- **Plan said:** "Franchise levels (300 to 2500 CHF)" and implied tiers assigned by age/affluence.
- **Official source (S046, FOPH):** the standard deductible is CHF 300 for adults and **CHF 0 for children**. Adults may *voluntarily* opt for 500, 1000, 1500, 2000 or 2500; children for 100, 200, 300, 400, 500 or 600. Insurers are **not obliged** to offer the full range, and may differentiate for 19–25 year-olds.
- **Also corrected:** CHF 1,000 is **not** a deductible band. It is the maximum annual cost share for an adult holding the standard CHF 300 deductible (300 deductible + 700 maximum retention fee).
- **Also corrected:** there is **no rural-residence or age-based eligibility rule** for deductible bands.

### 1.3 The UN referendum was 3 March 2002, not 10 March

- **Official source (S049, swissinfo.ch):** referendum **3 March 2002**; accession **10 September 2002** was correct.
- **Implication:** the accession date is safe to use; the referendum date is not what the plan implied.

### 1.4 Import de-minimis is CHF 150, not CHF 100

- **Official source (S036, Federal Office of Customs):** the tax-free limit is **CHF 150** per person per day. Above it, VAT is charged on the **total** value, not just the excess. Reduced VAT rate 2.6%, standard 8.1%.
- **Implication:** the plan's "customs" cluster needs the CHF 150 figure.

### 1.5 Switzerland has no codified neutrality statute

- The plan's Category 6 cluster implied a "Neutrality Act". Accessible official sources state permanent neutrality is anchored in international law, recognised by the Congress of Vienna in 1815, and **has never been codified in a federal statute**. A question asserting a statute would be factually wrong.

### 1.6 "41 hours max weekly" is not a national figure

No accessible ch.ch page states a national maximum weekly working time. It is governed by sectoral collective agreements. **Not recorded as a fact.** What *is* verified (S032): Sunday work is generally prohibited; night work is banned 23:00–06:00; minimum daily rest 11 hours (12 for under-18s); minimum weekly rest 8 hours.

---

## 2. Dead and restructured URLs

The plan's URL list was written against an older site structure. Every replacement is recorded in the relevant `raw_pages` file header.

| Planned URL | Status | Working replacement |
|---|---|---|
| `ch.ch/en/political-system/federal-council/` | 404 | `ch.ch/en/political-system/government/` |
| `ch.ch/en/political-system/popular-initiatives/` | 404 | `ch.ch/en/political-system/political-rights/initiatives/what-is-a-federal-popular-initiative/` |
| `ch.ch/en/employment/` | 404 | `ch.ch/en/work/` |
| `ch.ch/en/swiss-citizenship/` | 404 | `ch.ch/en/foreign-nationals-in-switzerland/naturalisation/` |
| `ch.ch/en/taxes/` | 404 | `ch.ch/en/taxes-and-finances/paying-taxes/` |
| `ch.ch/en/education/` | 404 | `ch.ch/en/school-and-education/` |
| `ch.ch/en/environment/` | 404 | (ch.ch has no environment theme) → `bafu.admin.ch` |
| `ch.ch/en/political-system/cantons/` | 200, JS hub, zero facts | sub-pages `…/cantons/cantonal-government-role-and-composition/`, `…/federalism/` |
| `ch.ch/en/housing/` | 200, JS hub, zero facts | `ch.ch/en/housing/rent/rental-and-leasing-agreements/` |
| `bag.admin.ch/…/krankenversicherung.html` | 404 | `bag.admin.ch/en/health-insurance-premiums-and-co-payment` |
| `bsv.admin.ch/bsv/en/home/sozialversicherung/ahv.html` | 404 | `bsv.admin.ch/en/old-age-insurance-system` |
| `bsv.admin.ch/…/berufliche-vorsorge.html` | 404 | `bsv.admin.ch/en/old-age-provision-occupational-benefits-plan` |
| `bazg.admin.ch/bazg/en/home.html` | 404 | `bazg.admin.ch/en/value-added-tax-vat-chf-150-tax-free-limit` |
| `sem.admin.ch/sem/en/home/themen/aufenthalt.html` | 200, thin | `…/aufenthalt/biometr_auslaenderausweis.html` and `…/aufenthalt/eu_efta.html` |
| `bfs.admin.ch/…/population.html`, `…/languages.html` | 200, JS-rendered, empty body | **BFS unusable for verbatim extraction** → myswitzerland, ch-info, swissinfo |
| `admin.ch/gov/en/start/federal-council/members-of-the-federal-council.html` | **403** (bot block) | `bk.admin.ch/en/federal-council-affairs` |
| `eda.admin.ch/aboutswitzerland/en/home/history.html` and all `eda.admin.ch` | **403** | `bar.admin.ch`, `bk.admin.ch` PDF, `ch-info.swiss` |
| `bger.ch` HTML | **403** (Incapsula JS challenge) | `bger.ch` 150-year anniversary PDF |
| `myswitzerland.com/en/…` | **406** | `myswitzerland.com/en-gb/planning/about-switzerland/general-facts/facts-about-switzerland/<slug>/` |
| `ethz.ch/…/organisation/history.html` | 404 | `ethz.ch/en/the-eth-zurich/portrait/history/overview.html` |
| `icrc.org/en/document/icrc-historical-overview` | 404 | `icrc.org/en/document/history-icrc` |
| `fedlex.admin.ch/eli/cc/2022/491/en` (FADP, SR 235.1) | **200 but JS-only shell** — returns only the "this site requires JavaScript" notice, no article text | `edoeb.admin.ch` (EN paraphrase of the articles: `/en/faq-data-protection`, `/en/basic-knowledge`, `/en/duty-to-provide-information`) |
| `edoeb.admin.ch/en` | **200** — was assumed restructured/403; it works, and the whole site is fetchable in EN | (use `edoeb.admin.ch` for all FADP/privacy topics, incl. `/en/photos-and-video-surveillance`, `/en/employment`) |
| `dsa.be.ch/{de,fr}/start/themen/videoueberwachung.html` | 200 but **JS-rendered body — navigation shell only** | `vs.ch` (Canton Valais, FR) + `lausanne.ch` (Ville de Lausanne, FR) for cantonal/municipal video-surveillance rules |
| `myswitzerland.com/en-us/…/tipping` | 200 (use the `/en-us/`, `/en-gb/` or `/en-ch/` form, not bare `/en/`) | same path — this is the working form for the tipping fact |

**Practical consequence for reproducibility:** anyone re-running this harvest with a headless browser will get *different* URLs than an HTTP fetch for the 403/406 sites. The registry records the URL that actually returned content, and `raw_file` links each row to its evidence.

---

## 3. Open gaps — requested, not verifiable, not recorded

Listed for the datasheet's limitations section. None of these were invented.

| # | Gap | Why it stays open |
|---|---|---|
| G1 | UVG accident-insurance salary threshold (employer must insure above ~CHF 22,050) | Not on any accessible official page. Suva publishes *8 hours/week* as the non-occupational-accident threshold and CHF 148,200 max insured earnings, but not the salary threshold. |
| G2 | Cantonal income-tax rate bands | ch.ch (S018) deliberately states no CHF figures and defers to the Federal Department of Finance. |
| G3 | Which cantons border which country | Only per-country border *lengths* are published (S027). |
| G4 | Federal vs. national language distinction wording | Resolved at a general level by S047, but the EDA "About Switzerland" multilingualism page — the cleanest statement — is 403-blocked. |
| G5 | Rütli Oath (1291) as a named event | S037 confirms the 1291 Waldstätte Alliance and the three founding cantons, but the *Rütli* location specifically was not verifiable on an accessible official page. |
| G6 | Federal Supreme Court official languages | BGer HTML is JS-challenged; the 150-year PDF does not state it. |
| G7 | Max weekly working hours | Not a single national figure — see §1.6. |
| G8 | Three pillars of vocational training / apprenticeship wage | Not on the SBFI page fetched; lives on the 403-blocked EDA portal. |
| G9 | Swiss Post ownership status | Not asserted on any fetched page. |
| G10 | Four-flow recycling model (Glas/Metall/Papier/Kunststoff) | Not on the BAFU pages fetched. |
| G11 | Verbatim text of the FADP (SR 235.1) itself | `fedlex.admin.ch` is a JavaScript-only shell to an HTTP fetch. Every FADP article reference in S053 comes from the FDPIC's English paraphrase, not from the statute. |
| G12 | Official (ministerium / regulator) statement of Swiss tipping law | None found on ch.ch, admin.ch, bazg or edoeb. S055 rests on a state broadcaster (swissinfo.ch), the national tourism body (myswitzerland.com) and the hospitality trade association (GastroSuisse). Swissinfo's tax-rule facts are a *news report quoting* the Federal Council's statement, not the statement itself. |

---

## 4. Native-speaker dependency (for Phase 1C)

Not a source gap, but recorded here because it affects corpus completeness:

- **S044 is German-language.** Its facts are translated into English and marked as such in the file. A German-reading Swiss reviewer should confirm the translation before the questions are finalised.
- Several files contain **Swiss German terms** in their quotes (e.g. `Gebührensack`, `ortsüblichen Kündigungstermine`, `Nachmieter`). These are quotable but must not be paraphrased into Standard German when building the Phase 1C dialect items.

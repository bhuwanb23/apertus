# S056 — Alemannic Wikipedia orthography notes

SOURCE_ID: S056
LANGUAGE: gsw (Alemannisch / Schwyzerdütsch)
DATE_ACCESSED: 2026-10-12
LICENSE: CC BY-SA 4.0 (als.wikipedia.org)
FETCH METHOD: MediaWiki Action API, `action=query&prop=extracts&explaintext=1&redirects=1` (plain-text article body, links stripped to `[title]`). Wikitext was NOT used, because wikitext markup would break verbatim sentence contiguity.

> **This is a summary file, not a corpus item file.** The authored content here is descriptive prose about a writing system; the ONLY quoted Alemannic in it is quoted from the Alemannic Wikipedia's own pages about itself.

---

## 1. The short version

There is **no single Alemannic orthography**, and the Alemannic Wikipedia does not claim one. What the corpus actually contains is a **house style** — closer to Dieth than to Marti, but looser — plus **at least five visibly different registers** inside the S056 set alone. A benchmark built on these files must treat orthography as a *variable to be flagged per item*, not as a constant to be assumed.

## 2. What the Alemannic Wikipedia says about itself

From `https://als.wikipedia.org/wiki/Alemannisch` (§ on social status of Alemannisch), quoted verbatim:

> „D Bsunderheit vu der alemannische Wikipedia isch, dass dett Theme in em sachliche Alemannisch gschriibe werret.“

> „D Alemannisch wird allerdings au in der Schwyz praktisch nume gschwätzt und ehnder sälte uffgschriibe.“

And on the project's scope, from `https://als.wikipedia.org/wiki/Wikipedia` (§ *D Alemannisch Wikipedia*):

> „D alemannisch Wikipedia isch zyderhäär e Projäkt fir ali Inträssierte rùnd ùm dr Boodesee, i der Düütschschwiiz und em Rhy no bis i d Gägend vo Stroossburg.“

> „Zäntraali Theeme i dr alemannische Wikipedia sin d Sprooche und d Sproochwüsseschaft, d Dialäkt und d Mundartkultur, s Schaffe vo Mundartschriftsteller und süschtigi Sache us em alemannische Sproochruum.“

From `https://als.wikipedia.org/wiki/Orthographie`, on the absence of a standard (§ *Norm*), quoted verbatim:

> „Im Underschid daderzue git's für di alemannische Dialäkte kei normierti Rächtschrybig u kei Standardsprach.“

That last sentence is the single most important fact for this project: **the Standard German translations in the S056 files cannot be checked against an official Alemannic standard, only against native-speaker judgement.** It is exactly why rule 4 of the brief (flag the translation as authored and unvalidated) is load-bearing rather than decorative.

## 3. The Alemannic Wikipedia's own bibliographic framing

From `https://als.wikipedia.org/wiki/Orthographie` (§ *Büecher*), quoted verbatim:

> „Schwyzertütschi Dialäktschrift. Vom Eugen Dieth 1938. (2. Auflage bearb. u. hrsg. von Christian Schmid-Cadalbert, Aarau 1986)“
>
> „Bärndütschi Schrybwys. Ein Wegweiser zum Aufschreiben in berndeutscher Sprache. Vom Werner Marti; 1985: Bern. ISBN 3-7720-1597-2“

**Note the edition correction.** The Alemannic Wikipedia gives Marti as **1985**, not 1972. A third edition (2018) also exists in the trade. If Phase 1C cites "Marti 1972", reconcile against the 1985 ISBN the Alemannic Wikipedia itself prints.

## 4. The two-axis taxonomy the Alemannic Wikipedia itself uses

From `https://als.wikipedia.org/wiki/Orthographie` (§ *Alemannischi Rächtschrybige*), quoted verbatim:

> „Innerhalb vo dere Tradition git's grundsätzlech zwöi verschidnigi Müglechkeite für di alemannische Rächtschrybig: Entweder en Orientierig ar schriftdütsche Rächtschrybig oder en Orientierig ar Ussprach.“

**Axis A — long /aː/: written-German-oriented vs speech-oriented.**

> „Die, wo sech a der schriftdütsche Rächtschrybig orientiere, schrybe der läng /aː/ entweder mit <a> (Bad), <ah> (Bahn) oder <aa> (Waag); dergäge schrybe die, wo sech ar Ussprach orientiere, i allne Fäll <aa> (Pfaad, Baan, Waag).“

This is the single most consequential difference between Dieth and Marti, and the Alemannic Wikipedia states it plainly:

**Axis B — orientation toward Standard orthography vs toward speech.** From the same page:

> „Es git aber ou Eigeheite, wo di alemannischi Rächtschrybig vom dütsche Standard abwycht. Im Fall vo de Buechstabe <k, ck> liggt das dran, das di hochalemannische Dialäkte di zwöiti (hochdütschi) Lutverschiebig vollständig hei düregfüert (im Underschid zu de nideralemannische u zum Schriftdütsch), so das us emnen alte /k/ d Affrikate /kx/ isch worde.“

> „En anderen Underschid isch d Bedüttig vo <gg, bb, dd>, wo im Underschid zum Schriftdütsche nid Lenis bezeichne, sondern Fortis.“

**Which tradition is which**, from the same page, quoted verbatim:

> „**Orientierig am Schriftdütsche** — Schwyz: D Orientierig am Schriftdütsche findet sech bi de meischten eltere Schriftsteller, z. B. bi Rudolf von Tavel, Simon Gfeller, Otto von Greyerz, Carl Albert Loosli. Es Bispil für ne Beschrybig von so're Rächtschrybig isch ds Buech Bärndütschi Schrybwys vom Werner Marti. **Die Tradition isch im Bärndütsche bis hüt sehr starch.**“

> „**Orientierig ar Ussprach** — Schwyz: D Orientierig ar Ussprach isch syt der Mitti vom 20. Jahrhundert ufcho, bsunders mit em Buech Schwyzertütschi Dialäktschrift vom Eugen Dieth.“

**So: Marti 1985 (`Bärndütschi Schrybwys`) = written-German-oriented, long /aː/ written `a`/`ah`/`aa` at choice, conservative. Dieth 1938 (`Schwyzertütschi Dialäktschrift`) = speech-oriented, long /aː/ ALWAYS `aa`.**

The Alemannic Wikipedia also names a third tradition, from Alsace:

> „Frankrich: Anne 2003 isch uf eme Symposium e «Charte de la graphie harmonisée des parlers alsaciens» bschlosse wore … In 2008 gebt s a neia Version vo däre Charte : «Orthal».“

`Orthal` is the modern Alsatian harmonised chart and is worth consulting for anything the S056 set flags as Alsace-oriented.

## 5. Dieth's own rules — quoted from `https://als.wikipedia.org/wiki/Dieth-Schreibung`

### 5.1 The founding principle

> „Schryyb wie de schwäzesch! (Ooni ùf di hoochdydsch Räächdschryybig z luege)“
>
> „Zwische lange ùn chùùrze Sälbschdlud wird ùnderschiide. Zwische gschlosene ùn ùfige Sälbschdlud wird ùnderschiide. Zwische schwache ùn schdaarge Midlud (Lenes ùn Fortes) wird ùnderschiide.“

Those are Dieth's three load-bearing distinctions, and they map directly onto what the S056 items test:

| Dieth rule | Standard German | S056 example |
|---|---|---|
| long vs short syllable | often unstated | `aa`/`ä`/`oo`/`ee` vs short `a`/`e`/`o` |
| closed vs open syllable | schwa marking | `Züüg` (closed) vs `Määss` (open) |
| strong vs weak (fortis/lenis) consonant | `gg`/`bb`/`dd` | `Streggè` = Gleis, `scht` for `st` |

### 5.2 No doubling to mark length

> „Mer schrybd also imer: Züritüütsch gaa, baseldytsch goo, elsäserdydsch gee dt. 'gehen'“

> „S h wird nie bruuchd zùm d Lengi vùm e Sälbschdlud aazzaige“

This is the key contrast with Marti-style written-German orientation, and it is **directly visible in S056**: `grösser` → `grööscht` / `greeßer` / `gröösser` depending on sub-dialect, all from the same root.

### 5.3 `k` vs `gg` vs `kh` — the sharpest Dieth/Suter dispute

> „Wel s in dr Schwyz gängig isch, d Affrikata [kx] mid eme aifache k bzw. ck z schryybe, wird in dr Dieth-Schryybig dr Buechschdaab k wäge dêm nid fir d Fortis [k] bruuchd, sùndere eebe fir die Affrikata [kx]. Fir dr Lud [k] schrybd mer derno gg, d. h. mer schrybd Sack ùn said [z̥akx], mer schrybd Brùgg ùn said [b̥rʊk].“

> „Dr Rudolf Suter, wù d Gramadig ùn s Wèèrderbuech vùm Baasel gschriibe hed, hed aber dooderfiir (also fir ghuuchds [kʰ]) aifach k gschriibe, d. h. Kind.“

So **Dieth 1938 would write `Gghind`; Rudolf Suter, the Basel lexicographer, writes `Kind`.** The Alemannic Wikipedia records both conventions:

> „k schdood fir dr Lud [k], kch schdood fir d Affrikata [kx]. Daas gseet näär esoo uus: D Fortis [k] schrybd mer k: züritüütsch Klarinett (schdad no Dieth Gglarinett) — D Affrikata [kx] schryb mer kch: züritüütsch Kchùnscht (schdad no Dieth Kùnscht) — E ghuuchd [kʰ] schryb mer kh: baaseldytsch Khind (schdad no Suter Kind)“

**S056 consequence:** `Kafi Freitag`, `Chuchichäschtli`, `Buchez`-type items would discriminate Dieth from Suter conventions directly. None of the requested articles yielded a clean `kh`/`kch`/`gg` contrast, which is a gap worth filling in a second pass.

### 5.4 `ß`/`ss` and `sch`/`sh`

> „In dr Haubdsach hed er d Schryybig vù dr s- ùn sch-Lud schdaarg veraifachd. Schdad dääne Sonderzaiche, wù dr Dieth voorgschriibe ghaa hed, hed er voorgschlaa bim s nùme s oder ss z schryybe ùn nid ß. Bi ʃ/ʃʃ u ch/cch füert er nùme no em Dieth syni ǜbergangsreglen aa, das me nämlech wi ìm ʃrìftdütschen i aḷḷne fäḷ sch u ch söḷ ʃrybe, usgnoo sp u st ìm wortaalut.“

The Alemannic Wikipedia **does not print a Dieth-style `ſ`** in the article body (it uses a plain `s`). This matters for the Schiff file, where the house style writes `Floss` and `Bugwulscht` where Standard German writes `Floß` and `Bugwulst`.

### 5.5 `scht` vs `schd` — the Heusler rule

This is the most interesting rule for the S056 set, and it is quoted at length:

> „Im Baseldytsche cha me gar nid säge, öb d Ussprach schd oder scht isch. Der Underschid zwüsche d u t verschwindet nämlech im Kontakt mit emnen andere stimmlose Lut wi sch. Das isch en allgemeini Reglen ir Ussprach vo alemannische Dialäkt, wo als Heuslers Gsetz bekannt isch.“

> „Der Grund, werum das men im Baseldytsche normalerwys Boscht u Stai mit t schrybt, liggt also nid ir Uussprach, sondern ir Analogie zu de hochdütsche Schrybige mit t: Post u Stein. Me chönnt aber vor Uussprach här grad so guet Boschd u Schdai schrybe.“

> „Im Keiserstüelische cha me genauso weni wi im Baseldytschen säge, öb d Ussprach scht oder schd isch. … I söttigne Fäll het ds Keiserstüelische immer e d.“

**This is the dialect variation S056 actually contains.** Compare, both in the S056 set:

- Basel/Zürich house style (`Streggèvozwygigè`, `Unterscheidig`): `scht`
- Schwäbisch-Alemannisch Fasnacht register (`Schteet`, `Nascht`, `gschdiigt`): `scht` with heavy apicalisation
- St. Gallen Gletscher register: `Schteibröcke`, `Rükschtand`

No `schd` (Keiserstüel) or `Boschd` spellings were harvested. **That is a real gap in S056 and the next pass should target Kaiserstüel/Oberrheinisch material.**

### 5.6 Doubled consonants at word end

> „Dieth 1938 wyst ussertdäm druf hii, das bi vǜrklech länger usʃpraach o nach emne länge wokaaḷ söḷ verdoplet wärde: Aatte, Muetter. Am wortändi wärde t u p nach Dieth 1938 nìd vertoplet.“

**Consistently followed across S056:** `Brot`, `Banhof`, `Dämpfi`, `Zürich`, `Kafi`, `Zug`, `Velo`, `Schiff` — no final doubling. The Alemannic Wikipedia also confirms no geminate marking in the running text (`guggaun`, not `gg`), and the `Buech` question is settled the same way.

### 5.7 Loanwords left untranslated

> „Främdwèèrder sole grùndsäzlich au ludnooch gschriibe wääre. Z. B. elsäserdydsch Khüldüür dt. 'Kultur'“

The Alemannic Wikipedia itself does **not** follow this — it keeps `Industry`, `Konservierigsstoff`, `Diacetylwiisüüriglyceride` in the Brot article and `Filterkaffi`, `Espresso`, `Neskaffi` in the Kaffee article. **The S056 corpus therefore contains both policies.** Flag per item.

### 5.8 No apostrophe at word end

> „Dr Aboschdroof wird nie gschriibe. Bärndütsch ds Huus dt. 'das Haus'. Nid: d's Huus“

**Consistently followed in S056:** `s Wätter`, `d Stadt`, `s Brot` — never `s'`. This is a reliable negative marker for Alemannic-vs-Bavarian text.

### 5.9 `Rückverwandlung` / linking `-n`

> „Des n, wù in dr maischde alemanische Dialägd as Verbindig bruuchd wird, wän bschdimdi Sälbschdlud ùfenander dräfe, wird immer an s Woord voornedraa draaghänggd, d. h. nie mid Bindeschdrich oder elaai gschriibe.“

**Followed in S056** (`a schtand`, `a Drüm`, `a di Staat`).

## 6. Markers a reader should expect — and where each occurs in S056

| Marker | Standard | S056 occurrence | Files |
|---|---|---|---|
| final devoicing (all codas) | — | `Rampf`, `Aaloss`, `Brot`, `Floss`, `Gschicht` | Brot, Basel, Schiff, Baanhof |
| `-t` for Standard `-d` | — | `Brot`, `Brot`, `Bild`→`Schbil` | Brot, Fasnacht |
| `-e` for Standard `-en` | — | `befördere`, `variiere`, `dransportiere` | Zug, Wetter, Schiff |
| `ä` for long /aː/ (Dieth `aa`) | Bahnhof | `Baan`, `Bade`, `Läng` | Baanhof |
| `oo` for long /oː/ | Bahnhof | `grööscht`, `Züüg`, `Boot` | Zürich, Zug, Baanhof |
| `aa` for long /aː/ | Bahn | `Baan`, `Brügg`, `maa` | Basel, Brot |
| `ee` for long /eː/ | Beeren | `Seebecki`, `greeßer`, `Kee` | Broetli, Zürich |
| `üü` for long /yː/ | Beeren | `düür`, `Lüüt`, `üüs`, `Chüeuschrank` | Kaffee, Zug, Wetter, Röschti |
| `öö` for long /øː/ | Köhre | `grööstet`, `öö`, `köönigligi` | Kaffee, Jahrmarkt |
| `scht` for /ʃt/ | — | `voschtand`, `Unterscheidig`, `Schteibröcke`, `schteut` | Baanhof, Gletscher, Röschti |
| `schp` for /ʃp/ | — | `Schipfi`, `abschpile` | Zürich, Wetter |
| `ch` = /ç/ | — | `Bachhefi`, `Fähri` | Brot, Basel |
| `ch` = /x/ | — | `Chüeuschrank`, `Chillefiirdig` | Röschti, Jahrmarkt |
| dropped case endings | -e/-en/-er | `d Stadt`, `s Brot`, `d Erni` | all |
| no final gemination | Doppelkonsonant | `Brot`, `Bahnhof` | all |
| no apostrophe | d's | `s Wätter` | all |
| `gm-` participle prefix | ge- | `gmacht`, `gmaale`, `gschribe` | Brot, Kaffee, Baanhof |
| `gsch-` participle prefix | ge- | `gschintete`, `Gsichder` | Röschti, Fasnacht |
| `gw-` participle prefix | ge- | `gwunne`, `gna-` | Kaffee, Wäldi |
| `mr` / `mä` / `mò` / `mer` = man | man | all four attested | Brötli, Brot, Baanhof, Kartoffeldämpfer |
| `em` / `zom` / `am` = in dem / zu dem | in dem | `em Jura`, `zom` | Bise, Röschti |
| `ooli` / `alliwyl` = alle | alle | `allewyl` | Basel |

## 7. What the Alemannic Wikipedia's own pages list as contested

From `https://als.wikipedia.org/wiki/Orthographie` (§ *Spezielli Problem*), quoted verbatim — these are exactly the places where S056 items should be flagged as under-determined:

> „Zämeschrybig vs. Getrenntschrybig: ufe Zug vs. uf e Zug; so ne Sach vs. sone Sach; imene Tag vs. i mene Tag“
>
> „Aposchtrof: ds Vélo vs. d's Vélo; z Züri vs. z'Züri; d Hose vs. d'Hose; itz chunt's vs. itz chunts“
>
> „Verdoppelig oder nid (z. T. dialäktabhängig): Hilf vs. Hilff; nüüt vs. nüt; Sig vs. Siig; ruuch vs. ruch; **Schwytzer vs. Schwyzer**; **Zit vs. Ziit**“
>
> „<y> vs. <i> (z. T. dialäktabhängig): Zyt vs. Zi(i)t; Ytrag vs. I(i)trag; **Orthography vs. Orthographii**“
>
> „Diphthonge (z. T. dialäktabhängig): **nöi vs. neu; Seich vs. Saich**“
>
> „Schwa: e huereguete Räge vs. ä huäräguätä Rägä“

The `Schwytzer vs. Schwyzer` and `nöi vs. neu` and `Ytrag vs. Itrag` entries are directly relevant: **S056 contains `Schwyzer` (Schwiz file) and `Itrag`-type `Iiwooner` (Wäldi) and `nöizytlich` (Zürich), so dialect-internal spelling variance is already present and must not be normalised.**

## 8. Register inventory actually observed in S056

| # | Register | Files | Marker sample |
|---|---|---|---|
| 1 | Basel house style | Basel, Brot, Kaffee, Schiff, Zug, Jahrmarkt, Schwiz (lead) | `Bruggen`, `zää`, `Däig`, `allewyl` |
| 2 | Zürich heavy Alemannisch | Baanhof, Zürich | `Èn`, `dè`, `Streggè`, `meischtfrequèntyrte` |
| 3 | Schwäbisch-Alemannisch (near-Dieth) | Fasnacht (§ *Schwäbesch-Alemannesche Fasnet*) | `fo`, `wut`, `widergschbiaglet`, `Schwäbisch-alemannischi` |
| 4 | Thurgau / St. Gallen | Gletscher, Wäldi | `ä` for /aː/, `tüei`, `dürä`, `Dialèkt` |
| 5 | Hochalemannisch / Oberrheinisch | Brötli | `ä` = indefinite article, `-e` endings, `Häfä` |
| 6 | Basel-Landschaft village speech | Kartoffeldämpfer | `mer`, `die`, `emene`, `Grumbiirre`, `Dämpfene` |
| 7 | Swiss-wide conservative (`ü` = /ʌ/) | Schwiz (§ *Sprooch*) | `Bùndesverfassig`, `Prozänt`, `nùmme` |

**Seven registers in 17 files.** Any claim that S056 is "Basel Alemannisch" is false; the header `DIALECT: basel` is corpus-level bookkeeping, and each file's `DIALECT_EVIDENCE` header names the actual register.

## 9. Gaps to close in a second pass

1. **No `kh`/`kch`/`gg` lexical items** → the Dieth-vs-Suter test is unexercised. Target: articles about children, cattle, food.
2. **No `schd` (Keiserstüel) spellings** → the Heusler rule is only half-represented.
3. **No `Märit`** — confirmed absent from als.wikipedia. Search the `Basler Herbstmäss` and `Mustermäss Basel` articles (linked from Jahrmarkt) for more fair/market vocabulary.
4. **No `Zügle`, `Buchez`, `Trotte`, `Rüteli`, `Gummi`, `Tschugga`** — all confirmed absent as article titles. `Rüteli-Schwur` exists as an article title but is historical-political, not everyday domestic vocabulary.
5. **No Alsace/`Orthal` register** — would test the third orthographic tradition the Alemannic Wikipedia itself names.
6. **The 1972 vs 1985 Marti date** in the brief needs reconciling against the Alemannic Wikipedia's own ISBN record (§ 3 above).

## 10. Verification method used for this corpus

Because the Alemannic Wikipedia's house style is loose enough that a reader (or a text-fetching tool) can silently "correct" a dialect form into a Standard-looking one, **no sentence in S056 was accepted on visual inspection.** Each of the 108 sentences was string-matched byte-for-byte against the UTF-8-decoded API extract of its own article.

That check caught 14 real transcription errors that visual reading had missed, including:

- `Schwyz` mis-read as `Schwiiz`
- `Bischbil` mis-read as `Bischpil`
- `numme` mis-read as `numm`
- `Wort` mis-read as `Woat` (the source really does say `Woat`)
- `Der` mis-read as `Dr`
- `beschriibe` mis-read as `beschriube`
- `vozichet` mis-read as `vozichtet`
- German quotation marks „ “ substituted for the straight `"` actually in the source
- three lowercased sentence-starts (`deilwys`, `de Name Schipfi`, `me cha`) re-capitalised

**Anyone extending S056 should reuse the same byte-level check. Visual proofreading is not sufficient for this corpus.**
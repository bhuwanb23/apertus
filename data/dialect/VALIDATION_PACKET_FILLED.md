# Native Speaker Validation Packet — Phase 1C

**Send this to the volunteer.** Everything they need is below. Estimated time: 15–20 minutes.

---

## What we need and why

I am building a benchmark ("Swiss Reality Check") that tests how well an open language model handles Swiss German, Swiss institutional knowledge and Swiss cultural norms, for a hackathon run by EPFL, ETH Zurich and CSCS.

**Good news for you: you do not need to check the Swiss German.** Every Swiss German sentence in the benchmark was copied verbatim from the **Alemannic Wikipedia** (`als.wikipedia.org`), which is written by native speakers and freely licensed. If a sentence came from there, it is real Swiss German — somebody Swiss wrote it that way.

**What I do need you to check is the English around it:**

1. **The Standard German translations.** These are the one part I wrote myself. If a translation is wrong or unnatural, the whole item is broken.
2. **The dialect labels.** Some items are tagged `basel`, `zurich`, `bern`, `walser`, `valais`. If an item is tagged with the wrong region, that is a real error.
3. **The multiple-choice distractors.** In the "what does this mean?" questions, the three wrong options must be genuinely wrong but plausible.

I am **not** asking you to grade the model or take a test. I am asking you to fact-check my translations.

---

## What you get

Credit as a named contributor in the repository README and in the dataset datasheet, with whichever handle you prefer.

---

## The 30 items

They are split into four kinds:

| Kind | Count | What you check |
|---|---|---|
| **Translation** | 12 | Is the Standard German right and natural? |
| **Comprehension** (what does this mean?) | 8 | Is the right option right, and are the three wrong options genuinely wrong? |
| **Culture-in-dialect** (a Swiss fact inside a Swiss German sentence) | 5 | Same as above, plus: is the Swiss fact true? |
| **Dialect identification** (which dialect is this?) | 5 | Is the labelled dialect correct? |

Full data: `data/dialect/dialect_items.json`. A ready-to-fill answer sheet is at the bottom of this file — copy it, fill it in, send it back. **You do not need to read the JSON.**

---

## Please answer these five questions per item

```
id:        D001
kind:      translation
dialect:   basel
sg:        (the Swiss German sentence)
mine (de): (the Standard German translation I propose)

1. Is my German translation CORRECT?            yes / mostly / no
2. Would a Swiss person write it that naturally?  yes / mostly / no
3. Is the dialect label right?                  yes / probably / no  (only for dialect_identification, and generally)
4. For multiple-choice: are the three wrong options genuinely wrong?   yes / one is debatable / no
5. Correction, if any:  ______________________________________________
```

---

## The items

### D001 — translation (basel)

**Swiss German:**  *D' Säu verdraage nämli keini raui Grumbiirre.*

**My Standard German:**  Die Schweine vertragen nämlich keine rohen Kartoffeln.

*(dialect difficulty: easy)*

---

### D002 — translation (basel)

**Swiss German:**  *Mit de mäiste Brotdäig cha mä au chliineri Bröötli bache.*

**My Standard German:**  Mit dem meisten Brotteig kann man auch kleinere Brötchen backen.

*(dialect difficulty: easy)*

---

### D003 — translation (basel)

**Swiss German:**  *D Abgaas vom Schiffsmotor wärde über e Chemmi abgläitet.*

**My Standard German:**  Die Abgase vom Schiffsmotor werden über einen Schornstein abgeleitet.

*(dialect difficulty: easy)*

---

### D004 — translation (basel)

**Swiss German:**  *Ire Gussisepfanne tuet me de mit e chly Anke d Röschti aabrätle.*

**My Standard German:**  In der Gussepfanne röstet man dann die Rösti mit etwas Butter an.

*(dialect difficulty: medium)*

---

### D005 — translation (basel)

**Swiss German:**  *Hüte wird d Bezäichnig au für anderi Märt brucht, wo nid ständig si, hüfig für Volksfest.*

**My Standard German:**  Heute wird die Bezeichnung auch für andere Märkte gebraucht, die nicht ständig sind, häufig für Volksfeste.

*(dialect difficulty: medium)*

---

### D006 — translation (basel)

**Swiss German:**  *Organisator fodr Fasnet isch normalerweis a oatsasässege Narrazomft.*

**My Standard German:**  Organisator der Fasnacht ist normalerweise eine ehrenamtliche Narrenzunft.

*(dialect difficulty: hard)*

---

### D007 — translation (basel)

**Swiss German:**  *Für viili Basler isch d’Basler Fasnacht dr wichtigschti Aaloss im Yoor, und au diè gröschti Fasnacht vo der Schwyz.*

**My Standard German:**  Für viele Basler ist die Basler Fasnacht das wichtigste Ereignis im Jahr, und auch die grösste Fasnacht der Schweiz.

*(dialect difficulty: medium)*

---

### D008 — translation (basel)

**Swiss German:**  *Ermeri Lüt und in Krisezite fast die ganzi Bevölkerig häi Ersatzkaffi drunke wie Malzkaffi oder Schiggoree.*

**My Standard German:**  Ärmere Leute und in Krisenzeiten fast die ganze Bevölkerung haben Ersatzkaffee getrunken wie Malzkaffee oder Zichorienkaffee.

*(dialect difficulty: medium)*

---

### D009 — translation (zurich)

**Swiss German:**  *D Schwiiz het hüüt zämme mit Luxeburg dr höchschti Ussländerbeschtand in ganz Europa.*

**My Standard German:**  Die Schweiz hat heute zusammen mit Luxemburg den höchsten Ausländerbestand in ganz Europa.

*(dialect difficulty: medium)*

---

### D010 — translation (zurich)

**Swiss German:**  *S Woort und de Glaube häts natüürli scho vorane ggëë, aber über söttigi Sache hät mer halt früener chuum gschribe.*

**My Standard German:**  Das Wort und der Glaube hätten natürlich schon vorher existiert, aber über solches wurde halt früher kaum geschrieben.

*(dialect difficulty: medium)*

---

### D011 — translation (bern)

**Swiss German:**  *Für d Froue isch ds Braue den so Sälbstverständlech gsi, wi ds Bache vo Brot.*

**My Standard German:**  Für die Frauen war das Brauen so selbstverständlich wie das Backen von Brot.

*(dialect difficulty: medium)*

---

### D012 — translation (walser)

**Swiss German:**  *D Chilche ùn d Schuel sin bis in d 1920er Joor franzeesich gsii, derno isch s Idalieenisch ùfchùù.*

**My Standard German:**  Die Kirche und die Schule sind bis in die 1920er Jahre französisch gewesen, danach ist das Italienische hinzugekommen.

*(dialect difficulty: hard)*

---

### D013 — dialect identification (zurich)

**Swiss German:**  *Schpaatussiidler gelted dernaa nöd als Ussländer.*

**My question:**  Which Swiss German dialect is this sentence written in?

- **A.** Baseldytsch
- **B.** Züritüütsch **<-- my answer key: check this one**
- **C.** Bärndütsch
- **D.** Walser/Wallisertiitsch

*(dialect difficulty: easy)*

---

### D014 — dialect identification (bern)

**Swiss German:**  *Im Kapitel 17 chöme die zwöi e neue Name, also Abraham und Sara über.*

**My question:**  Which Swiss German dialect is this sentence written in?

- **A.** Baseldytsch
- **B.** Züritüütsch
- **C.** Bärndütsch **<-- my answer key: check this one**
- **D.** Walser/Wallisertiitsch

*(dialect difficulty: medium)*

---

### D015 — dialect identification (walser)

**Swiss German:**  *Di Gmäind Chlooschtärsch ischt mit dr Rhätischä Bahn guet ärschlossän.*

**My question:**  Which Swiss German dialect is this sentence written in?

- **A.** Baseldytsch
- **B.** Züritüütsch
- **C.** Bärndütsch
- **D.** Walser **<-- my answer key: check this one**

*(dialect difficulty: medium)*

---

### D016 — dialect identification (valais)

**Swiss German:**  *Dur ds Taal vaner Lienne fiert der Füesswäg zum Rawilpass.*

**My question:**  Which Swiss German dialect is this sentence written in?

- **A.** Wallisertiitsch **<-- my answer key: check this one**
- **B.** Baseldytsch
- **C.** Bärndütsch
- **D.** Züritüütsch

*(dialect difficulty: medium)*

---

### D017 — dialect identification (basel)

**Swiss German:**  *D' Dämpfi isch bis in d' sibziger Joor in de Schwiinemascht zum gare vo Grumbiire iigsetzt worde.*

**My question:**  Which Swiss German dialect is this sentence written in?

- **A.** Bärndütsch
- **B.** Baseldytsch **<-- my answer key: check this one**
- **C.** Züritüütsch
- **D.** Wallisertiitsch

*(dialect difficulty: medium)*

---

### D018 — culture in dialect (zürich)

**Swiss German:**  *Dr Bundesrat hät sibe Mitgliider, wo jedes für sich au wider Bundesrat oder Bundesrätin gheisst.*

**My question:**  According to this sentence, how many members does the Swiss Federal Council have?

- **A.** Five
- **B.** Seven **<-- my answer key: check this one**
- **C.** Nine
- **D.** Twelve

*(dialect difficulty: easy)*

---

### D019 — culture in dialect (zürich)

**Swiss German:**  *De Bundespräsident hät als «erschte under Gliiche» (primus inter pares) kei wiiteri Rächt, sondern erfüllt Repräsentationsuufgabe und leitet d Bundesratssitzige.*

**My question:**  According to this sentence, what extra authority does the Bundespräsident have over the other Federal Councillors?

- **A.** A casting vote, which lets the Bundespräsident break a deadlock on his own
- **B.** The power of veto, which lets the Bundespräsident block a decision of the other six
- **C.** The power to dismiss a Federal Councillor who disagrees with him
- **D.** None - the Bundespräsident is first among equals, represents the country and chairs the Federal Council meeting **<-- my answer key: check this one**

*(dialect difficulty: hard)*

---

### D020 — culture in dialect (uncertain)

**Swiss German:**  *Im Ständerot git’s 46 Abgordneti, un i ihn sändet alli Kantön zwöi Ständeröt, numme die sogenannte Halbkantön sände eine.*

**My question:**  According to this sentence, how many members does the Swiss Council of States (Ständerot) have?

- **A.** 46 **<-- my answer key: check this one**
- **B.** 50
- **C.** 52
- **D.** 26

*(dialect difficulty: medium)*

---

### D021 — culture in dialect (basel)

**Swiss German:**  *D Fasnacht duurt denn gnau 72 Stund und heert drum am Donschtig Morgen am Vieri mit em Ändstraich wider uff.*

**My question:**  According to this sentence, how long does the Basel Fasnacht last?

- **A.** Exactly 48 hours
- **B.** Exactly 72 hours
- **C.** Exactly 96 hours **<-- my answer key: check this one**
- **D.** Exactly 24 hours

*(dialect difficulty: medium)*

---

### D022 — culture in dialect (bern)

**Swiss German:**  *1885 hei d Schwyzer Brauereie der Wy als Nationalgetränk dür ds Bier verdrängt.*

**My question:**  According to this sentence, in which year did the Swiss breweries displace wine as the national drink?

- **A.** 1851
- **B.** 1876
- **C.** 1885 **<-- my answer key: check this one**
- **D.** 1914

*(dialect difficulty: medium)*

---

### D023 — comprehension (basel)

**Swiss German:**  *D Basler Fasnacht isch die greeschti Fasnacht in dr ganze Schwiz.*

**My question:**  What does this sentence mean?

- **A.** The Basel Fasnacht is the oldest carnival in the whole of Switzerland.
- **B.** The Basel Fasnacht is the largest carnival in the whole of Switzerland. **<-- my answer key: check this one**
- **C.** The Basel Fasnacht is the best-known carnival in the whole of Switzerland.
- **D.** The Basel Fasnacht is the longest-running carnival in the whole of Switzerland.

*(dialect difficulty: easy)*

---

### D024 — comprehension (basel)

**Swiss German:**  *E Masgge isch in Basel e Goschdyymierte, aso aine won e Goschdyym und a Larven aahet.*

**My question:**  What does this sentence mean?

- **A.** A 'Masgge' is a plain carnival mask worn over the face.
- **B.** A 'Masgge' is the costume alone, worn without any mask.
- **C.** A 'Masgge' is any masked participant, whether or not the participant is costumed.
- **D.** A 'Masgge' is a costumed figure - someone who wears both a costume (Goschdyym) and a mask (Larve) **<-- my answer key: check this one**

*(dialect difficulty: medium)*

---

### D025 — comprehension (zürich)

**Swiss German:**  *Er isch au gäge d Räislöiferei ufträtte, also s Verschicke vo Landslüt as Söldner i frömdi Chrieg, wo d Innerschwyzer Arischtokraty finanziell starch devo profitiert hät.*

**My question:**  What does this sentence mean?

- **A.** He fought to have Swiss men exempted from military service in foreign wars
- **B.** He opposed the Reisläuferei - the hiring out of Swiss men as soldiers in foreign wars - from which the Innertschwyzer aristocracy profited financially **<-- my answer key: check this one**
- **C.** He opposed the Reisläuferei and argued for its abolition by the Confederation
- **D.** He supported the Reisläuferei, arguing that it gave Swiss soldiers abroad useful military experience

*(dialect difficulty: hard)*

---

### D026 — comprehension (zürich)

**Swiss German:**  *Die sibe Bundesröt regiered eigetli zäme über alli Gschäft, aber tatsächlich stönd si je eim Departement vor; das isch s Departemäntalprinzip.*

**My question:**  What does this sentence mean?

- **A.** The seven Federal Councillors govern together over all business, but in practice each stands in front of one department - this is the departmental principle **<-- my answer key: check this one**
- **B.** The seven Federal Councillors each govern a separate department alone, without any joint decisions
- **C.** The seven Federal Councillors govern together over all business and each of them also represents one canton
- **D.** The seven Federal Councillors take it in turns to govern alone, one year each

*(dialect difficulty: hard)*

---

### D027 — comprehension (bern)

**Swiss German:**  *Wil ou Wy wird fermentiert u trotzdäm wird Wy nid brout sondern kelteret.*

**My question:**  What does this sentence mean?

- **A.** Wine, too, is fermented, and nevertheless wine is not brewed - it is cellared instead **<-- my answer key: check this one**
- **B.** Wine is brewed in the brewery in the same way as beer
- **C.** Wine is not fermented at all; it is pressed and bottled directly
- **D.** Wine is distilled in the brewery and sold as a spirit

*(dialect difficulty: medium)*

---

### D028 — comprehension (valais)

**Swiss German:**  *Dr tradizionell Dialäkt va Ayent gcheert zum Frankoprovenzalischu.*

**My question:**  What does this sentence mean?

- **A.** The traditional dialect of Ayent belongs to the Alemannic group
- **B.** The traditional dialect of Ayent belongs to the Rhaeto-Romance group
- **C.** The traditional dialect of Ayent belongs to the Lombard group of northern Italy
- **D.** The traditional dialect of Ayent belongs to the Franco-Provençal group **<-- my answer key: check this one**

*(dialect difficulty: medium)*

---

### D029 — comprehension (walser)

**Swiss German:**  *Sit dm 9. Dezembär 2005 chund Chlooschtärsch dür dn Gotschnä-Umfahrigs-Tunell vam Durchgangsvärchehr entlaschtät.*

**My question:**  What does this sentence mean?

- **A.** Since 9 December 2005 Klosters has been relieved of through traffic by the Gotthard bypass tunnel **<-- my answer key: check this one**
- **B.** Since 9 December 2005 Klosters has been bypassed by the Vereina tunnel
- **C.** Since 9 December 2005 the railway line through Klosters has been closed to all freight
- **D.** Since 9 December 2005 Klosters has been connected to the Rhätische Bahn by a new line

*(dialect difficulty: hard)*

---

### D030 — comprehension (basel)

**Swiss German:**  *Idiotikon isch en alts Wort für es Wörterbuech, wo die Wort drinstönd, wo für e bistimmti Landschaft tipisch sind, aber nöd au die, wo glych sind wie i de Schriftsprach.*

**My question:**  What does this sentence mean?

- **A.** 'Idiotikon' is an old word for a dictionary that records every word spoken in a region, including those identical to Standard German
- **B.** 'Idiotikon' is an old word for a dictionary of standard literary German written by Alemannic speakers
- **C.** 'Idiotikon' is an old word for a dialect dictionary recording the words typical of a particular region, but not the words that are the same as in Standard German **<-- my answer key: check this one**
- **D.** 'Idiotikon' is an old word for a bilingual Alemannic-French dictionary of the Swiss border region

*(dialect difficulty: hard)*

---

## Answer sheet

Copy this block into an email or DM and fill it in. `yes / mostly / no`, and leave blank if you skip the item.

```
- [ ] D001 · 1. D001: ___  2. D001: ___  3. D001: ___  4. D001: ___  5. D001: __________
- [ ] D002 · 1. D002: ___  2. D002: ___  3. D002: ___  4. D002: ___  5. D002: __________
- [ ] D003 · 1. D003: ___  2. D003: ___  3. D003: ___  4. D003: ___  5. D003: __________
- [ ] D004 · 1. D004: ___  2. D004: ___  3. D004: ___  4. D004: ___  5. D004: __________
- [ ] D005 · 1. D005: ___  2. D005: ___  3. D005: ___  4. D005: ___  5. D005: __________
- [ ] D006 · 1. D006: ___  2. D006: ___  3. D006: ___  4. D006: ___  5. D006: __________
- [ ] D007 · 1. D007: ___  2. D007: ___  3. D007: ___  4. D007: ___  5. D007: __________
- [ ] D008 · 1. D008: ___  2. D008: ___  3. D008: ___  4. D008: ___  5. D008: __________
- [ ] D009 · 1. D009: ___  2. D009: ___  3. D009: ___  4. D009: ___  5. D009: __________
- [ ] D010 · 1. D010: ___  2. D010: ___  3. D010: ___  4. D010: ___  5. D010: __________
- [ ] D011 · 1. D011: ___  2. D011: ___  3. D011: ___  4. D011: ___  5. D011: __________
- [ ] D012 · 1. D012: ___  2. D012: ___  3. D012: ___  4. D012: ___  5. D012: __________
- [ ] D013 · 1. D013: ___  2. D013: ___  3. D013: ___  4. D013: ___  5. D013: __________
- [ ] D014 · 1. D014: ___  2. D014: ___  3. D014: ___  4. D014: ___  5. D014: __________
- [ ] D015 · 1. D015: ___  2. D015: ___  3. D015: ___  4. D015: ___  5. D015: __________
- [ ] D016 · 1. D016: ___  2. D016: ___  3. D016: ___  4. D016: ___  5. D016: __________
- [ ] D017 · 1. D017: ___  2. D017: ___  3. D017: ___  4. D017: ___  5. D017: __________
- [ ] D018 · 1. D018: ___  2. D018: ___  3. D018: ___  4. D018: ___  5. D018: __________
- [ ] D019 · 1. D019: ___  2. D019: ___  3. D019: ___  4. D019: ___  5. D019: __________
- [ ] D020 · 1. D020: ___  2. D020: ___  3. D020: ___  4. D020: ___  5. D020: __________
- [ ] D021 · 1. D021: ___  2. D021: ___  3. D021: ___  4. D021: ___  5. D021: __________
- [ ] D022 · 1. D022: ___  2. D022: ___  3. D022: ___  4. D022: ___  5. D022: __________
- [ ] D023 · 1. D023: ___  2. D023: ___  3. D023: ___  4. D023: ___  5. D023: __________
- [ ] D024 · 1. D024: ___  2. D024: ___  3. D024: ___  4. D024: ___  5. D024: __________
- [ ] D025 · 1. D025: ___  2. D025: ___  3. D025: ___  4. D025: ___  5. D025: __________
- [ ] D026 · 1. D026: ___  2. D026: ___  3. D026: ___  4. D026: ___  5. D026: __________
- [ ] D027 · 1. D027: ___  2. D027: ___  3. D027: ___  4. D027: ___  5. D027: __________
- [ ] D028 · 1. D028: ___  2. D028: ___  3. D028: ___  4. D028: ___  5. D028: __________
- [ ] D029 · 1. D029: ___  2. D029: ___  3. D029: ___  4. D029: ___  5. D029: __________
- [ ] D030 · 1. D030: ___  2. D030: ___  3. D030: ___  4. D030: ___  5. D030: __________
```

---

## How we will use this

- Every correction you send is applied and the item is marked `validated_by: your_handle`.
- Items you confirm keep their text unchanged. Items you correct get your version.
- **If you only have time for some items, that is genuinely useful** — send what you can. Partial validation is reported honestly as partial in the datasheet.
- If you would rather not be named, say so and we will record "validated by a Swiss German speaker, name withheld".

---

## One thing worth knowing

A large part of this project is deliberately *not* measuring whether a model agrees with a political opinion. Where a question is genuinely contested — neutrality, weapons transfers, joining NATO — the benchmark scores whether the model identified the correct Swiss legal framework and acknowledged that Swiss people disagree, and it does **not** score the model's position. I mention it because some people worry about that kind of benchmark, and I would rather you know up front.

---

## Contact

Reply to this message or DM me. Corrections in German, English or Swiss German are all fine.

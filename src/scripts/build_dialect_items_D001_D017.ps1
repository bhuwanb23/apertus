$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$root = 'D:\projects\ml\apertus'
$raw  = Join-Path $root 'data\sources\raw_pages'

# --- spec -------------------------------------------------------------------
# file, verbatim-prefix, sentence-number, difficulty, dialect, evidence, synonyms(json), notes
$spec = @(
  @{ id='D001'; f='S056_alemannic_wikipedia_basel_kartoffeldaempfer.txt'; pre='D'' Säu verdraage'; s=2;
     diff='easy'; dia='basel';
     ev='S056 header `DIALECT: basel`; the file''s DIALECT_EVIDENCE block places this in village-spoken Basel-Landschaft Alemannisch (Mappach, BL) and names `Grumbiirre` as the definitive Basel-Landschaft dialect word. The file''s own word-count note flags S2 as "the shortest dialect-variation-contrast item available".';
     syn='{"schweine":["schweine","säu","ferkel","schwin"],"vertragen":["vertragen","verdraage","verdrii","erlidige"],"rohen":["rohen","raui","roh","ungekocht","rohe"],"kartoffeln":["kartoffeln","grumbiirre","grumbier","erdäpfel","härdöpfle","kartoffle"]}';
     nt='' }

  @{ id='D002'; f='S056_alemannic_wikipedia_basel_brot.txt'; pre='Mit de mäiste Brotdäig'; s=3;
     diff='easy'; dia='basel';
     ev='S056 header `DIALECT: basel`; DIALECT_EVIDENCE calls this "plain house-style Alemannisch with a Basel/Southwest-German feel" and names `Bröötli` as a Basel `-li` diminutive. LEXICAL NOTES L1/L8/L9 cover Däig, Bröötli, bache.';
     syn='{"meisten":["meisten","mäiste","meiste","grösste"],"brotteig":["brotteig","brotdäig","teig","däig","deig","brotteig"],"kleinere":["kleinere","chliineri","kleinere","chlineri","kleine"],"brötchen":["brötchen","bröötli","brötli","weckli","brötli","brezel"],"backen":["backen","bache","bachen","baken","öppe"],"können":["können","cha","chömme","chöme","mä"]}';
     nt='' }

  @{ id='D003'; f='S056_alemannic_wikipedia_basel_schiff.txt'; pre='D Abgaas vom Schiffsmotor'; s=8;
     diff='easy'; dia='basel';
     ev='S056 header `DIALECT: basel`. LEXICAL NOTE L22: "`Chemmi` = Schornstein — deliberate sense-shift, `Kamin`/`Schornstein` -> Alemannic `Chemmi`, a wholly different word. The strongest lexical item in the file." The file is otherwise pure Basel house style (`Aadriib`, `Wässerfaarzüüg`, `aabriibe`).';
     syn='{"abgase":["abgase","abgas","räuch","usgwäich","auspuffgase"],"schiffsmotor":["schiffsmotor","motor","maschine","schiffsmotor"],"schornstein":["schornstein","chemmi","kamin","schlot","dachlüfter","rauchfang","abgasrohr"],"abgeleitet":["abgeleitet","abgläitet","gführt","abgeläitet","usglet","weitergeleitet"],"werden":["werden","wärde","wärde"]}';
     nt='Deliberate lexical trap: a model that pattern-matches `Chemmi` to Standard `Kamin` loses the highest-weight content word. `Kamin` is accepted as a synonym because the reference itself is `Schornstein` and the two are near-synonymous in Standard German.' }

  @{ id='D004'; f='S056_alemannic_wikipedia_basel_roesti.txt'; pre='Ire Gussisepfanne'; s=3;
     diff='medium'; dia='basel';
     ev='S056 header `DIALECT: basel`; the file''s lead sentence enumerates five regional Alemannic names for the dish (`Röschti`, `Brägel`, `Brausi`, `Häärpflchoch`), confirming Alemannic lexis rather than Standard borrowings. LEXICAL NOTE L14: "`Anke` = Butter — Alemannic-only word, Standard `Butter` has no dialect counterpart in most Swiss German".';
     syn='{"gussepfanne":["gussepfanne","gussisepfanne","brätpfanne","pfanne","ussere"],"rösti":["rösti","röschti","roesti","bröti","brät"],"butter":["butter","anke","abbutter","anckä","ankä"],"röstet":["röstet","röstet","aabrätle","anbrätle","brätlet","rösti","röstet"],"man":["man","me","mä","merr"]}';
     nt='Reference renders the verb loosely as "röstet ... an"; `aabrätle` is specifically anbratenen/rösten. Synonyms cover both.' }

  @{ id='D005'; f='S056_alemannic_wikipedia_basel_jaehrmarkt.txt'; pre='Hüte wird d Bezäichnig'; s=3;
     diff='medium'; dia='basel';
     ev='S056 header `DIALECT: basel`. The file''s DIALECT_EVIDENCE records that `Märit`/`Märik` do not exist on als.wikipedia at all; the working Alemannic headword is `Märt` (LEXICAL NOTE L1), with `Mäss` as a second one. Both are Alemannic-only and neither is recoverable from Standard German.';
     syn='{"bezeichnung":["bezeichnung","bezäichnig","benennung","usdruck","name"],"märkte":["märkte","märt","märk","mässe","mäs","joormärt","markt"],"volksfest":["volksfest","volksfäscht","volksfäschte","volksfest","mess"],"heute":["heute","hüt","hüte","hüüt","hüte"],"ständig":["ständig","ständig","stänig","stässig","stetig"],"andere":["andere","anderi","annere","witeri"]}';
     nt='This file also carries the harvest note that `Märit` vs `Markt` was REFUTED as a dialect contrast. That does not affect the item: as a T1 translation task it tests `Märt` = Märkte, a lexical mapping, not a dialect discrimination.' }

  @{ id='D006'; f='S056_alemannic_wikipedia_basel_fasnacht.txt'; pre='Organisator fodr Fasnet'; s=4;
     diff='hard'; dia='basel';
     ev='S056 header `DIALECT: basel`, but this specific sentence sits in the `=== Schwäbesch-Alemannesche Fasnet ===` subsection, which the DIALECT_EVIDENCE block flags as orthographically a DIFFERENT system from the rest of the article (near-Dieth, `fo`, `fodr`, `mo`, final devoicing throughout, no unstressed `-e`). Orthography is recorded per item for exactly this reason. The header is a corpus-level Basel convenience label.';
     syn='{"organisator":["organisator","veranstalter","initiant","usläser"],"fasnacht":["fasnacht","fasnet","fastnacht","schwäbisch-alemannische fasnet","schwäbesch-alemannische fasnet"],"normalerweise":["normalerweise","normalerwis","gmeistens","gwöhnlich","us schtand","eistims"],"ehrenamtliche":["ehrenamtliche","oatsasässege","oatsasässege","unbezahlt","freiwillig","ohne bezahlung"],"narrenzunft":["narrenzunft","narrazomft","zunft","zomft","narrenzünfte","zomft","fasnechtszunft"]}';
     nt='Hard because it is dense heavy Alemannisch: `fodr` = für, `is normalerweis a` = ist normalerweise eine, `oatsasässege` = ehrenamtliche, `Zomft` = Zunft. Function words carry no weight, so the item stands or falls on four content words.' }

  @{ id='D007'; f='S056_alemannic_wikipedia_basel_basel.txt'; pre='Für viili Basler isch d'; s=7;
     diff='medium'; dia='basel';
     ev='S056 header `DIALECT: basel`; DIALECT_EVIDENCE states the article is "demonstrably Basel-oriented" with the lexical set `Brugg`, `Quardier`, `Gündeli`, `Süüde`/`rächts`. LEXICAL NOTES L10 (`Aaloss` = Ereignis, Alemannic `-oos` for long /o:/) and L11 (`Yoor` = Jahr) are both in this sentence. At the 20-word cap, no length flag.';
     syn='{"basler":["basler","basler","baslener"],"fasnacht":["fasnacht","fasnet","fastnacht"],"wichtigste":["wichtigste","wichtigschti","wichtigschti","eerschti","eerschti"],"ereignis":["ereignis","aaloss","aaloss","anlass","geschehnis","ereignis"],"jahr":["jahr","yoor","joor","johr"],"schweiz":["schweiz","schwyz","schwiz","schwiiz"],"grösste":["grösste","gröschti","grösste","grössti","meeschti"]}';
     nt='Verbatim text contains the typographic apostrophe in `d" + [char]0x2019 + "Basler` (U+2019). Preserved exactly as in the source; do NOT normalise to an ASCII apostrophe.' }

  @{ id='D008'; f='S056_alemannic_wikipedia_basel_kaffee.txt'; pre='Ermeri Lüt und in Krisezite'; s=5;
     diff='medium'; dia='basel';
     ev='S056 header `DIALECT: basel`. The Alemannic headword `Kaffi` is given in the article''s own first sentence (LEXICAL NOTE L1), and L10 records `Schiggoree` = Zichorienkaffee as "genuinely dialectal, no Standard counterpart". 18 words, within cap, no length flag.';
     syn='{"ärmere":["ärmere","ärmeri","arme","bemittle","gschachte"],"leute":["leute","lüt","lüüt","mensch","persone","mensche"],"krisenzeiten":["krisenzeiten","krisezite","kriise","notzite","mangelzeiten"],"bevölkerung":["bevölkerung","bevölkerig","bevölcherig","einwohner","bevölkerig"],"ersatzkaffee":["ersatzkaffee","ersatzkaffi","ersatz","ersatzkaffi","surrogatkaffee"],"getrunken":["getrunken","drunke","trunk","konsumiert","gematet"],"malzkaffee":["malzkaffee","malzkaffi","malz","maltkaffee"],"zichorienkaffee":["zichorienkaffee","zichorie","schiggoree","chicorée","inulin","zichoriekaffee","chicoree","wegwarte"]}';
     nt='' }

  @{ id='D009'; f='S057_alemannic_wikipedia_zurich_auslaender.txt'; pre='D Schwiiz het hüüt zämme'; s=14;
     diff='medium'; dia='zurich';
     ev='S057 header `DIALECT: zurich` with an explicit `{{Dialekt|Zürichdeutsch|Züridütsch}}` tag; the file is a city-Zürich article, which C1 of the Brauerei file identifies as the reference point for urban Zürich German (unlike Kloster Einsiedeln, which is Seedialect). C5 (Brauerei) explicitly records `hüt` as SHARED across Basel/Bern/Zürich, so `hüüt` is NOT counted as evidence here; the item rests on Zürich compound morphology and vowel spelling.';
     syn='{"schweiz":["schweiz","schwiiz","schwiz","schwyz"],"heute":["heute","hüt","hüüt","hüüte","hüt","hüte"],"zusammen":["zusammen","zämme","zäme","mit","gsamt","gemeinsam"],"luxemburg":["luxemburg","luxeburg"],"höchsten":["höchsten","höchschti","höchstschti","höchschti","höchst","grösste"],"ausländerbestand":["ausländerbestand","ussländerbeschtand","bestand","ausländerzahl","ausländerpopulation","anzahl vo ussländer"],"europa":["europa","euroopa","üropa"]}';
     nt='`Ussländerbeschtand` and `Schwaarz`/`zämme` vowel spellings are the load-bearing evidence. The item deliberately does NOT rely on `hüt`/`hüüt`, which the corpus records as a shared form across Basel, Bern and Zürich.' }

  @{ id='D010'; f='S057_alemannic_wikipedia_zurich_chindlistein.txt'; pre='S Woort und de Glaube'; s=5;
     diff='medium'; dia='zurich';
     ev='S057 header `DIALECT: zurich`, `{{Dialekt|Zürichdeutsch|Züritüütsch| Züritüütsch}}`. CONTRAST NOTE C1: the `äi`/`ää` spelling of long /a:/ ("Chindlistäi, Rutschstäi, Wöörter, ggëë, ghaa, Fruchtbaarkäit") is "the single most distinctive orthographic signature of this article", verified against Bernese which uses plain `a` in the same slot and never `äi`. C3 warns that `me`/`mer` is variable INSIDE this article, so `mer` is not used as evidence here.';
     syn='{"wort":["wort","woort","wörd","woat"],"glaube":["glaube","glaubens","glaube","guetscheme"],"existiert":["existiert","existiirt","vorane","gsi","geschebe","gsi"],"natürlich":["natürlich","natüürli","natürliche","natürli"],"geschrieben":["geschrieben","gschribe","gschriben","ufgschribe","notiert"],"solches":["solches","söttigi","solchi","söche","dergli"],"früher":["früher","früener","früher","eher","früher","nit gly","kaum"]}';
     nt='Note the reference double-negates ("wurde halt früher kaum geschrieben") which maps to `chuum gschribe`. Synonyms include `kaum`/`nit gly` so both halves of the reference are reachable. Folklore register per C5 — valid documentary Zürich German but more formal than everyday speech.' }

  @{ id='D011'; f='S057_alemannic_wikipedia_bern_brauerei.txt'; pre='Für d Froue isch ds Braue'; s=6;
     diff='medium'; dia='bern';
     ev='S057 header `DIALECT: bern` with an explicit `{{Dialekt|Berndeutsch|Bärndütsch|Bärndütsch}}` tag. CONTRAST NOTE C1 (this file) is the key: this very sentence is the Bernese side of the VERIFIED contrast — Basel writes the same word as `Broot` and also uses the loaf-word `Laib`, while the final devoicing /d/ -> /t/ is ABSENT in Bernese. C5 records `Froue` as Bernese plural with the -w- dropped. C9 records `bache`/`chunnt` as SHARED, so they are not evidence.';
     syn='{"frauen":["frauen","froue","frouen","fraue","damen"],"brauen":["brauen","braue","brau","braue","bierbrauen","bieren"],"selbstverständlich":["selbstverständlich","sälbstverständlech","gewohnt","gowoont","selbstverständli"],"backen":["backen","bache","bachen","baken","backe"],"brot":["brot","broot","laib","laibli","semmel","weck"]}';
     nt='`Brot`/`Broot`/`Laib` is a verified contrast (Brauerei C1), so a model defaulting to the Basel `Broot` still scores full credit — which is correct, since the task is translation, not dialect identification.' }

  @{ id='D012'; f='S057_alemannic_wikipedia_walser_issime.txt'; pre='D Chilche ùn d Schuel'; s=12;
     diff='hard'; dia='walser';
     ev='S057 header `DIALECT: walser` with `{{Dialekt|Issimedeutsch|Walsertiitsch|Éischemtöitschu}}`; SUBDIALECT_NOTE identifies this as Südwalser German in the Aosta Valley (Italy) — genuine Walser German by the wiki''s own classification. CONTRAST NOTE C2 documents the phonology self-described in the article (`Chilche`, `Idalieenisch`, `gsii`, `ùfchùù`); C5 records `Chilche` as the Walser short form against the Wallisertiitsch `Chilchu`.';
     syn='{"kirche":["kirche","chilche","chilchu","chirche","chürche"],"schule":["schule","schuel","schuel","schuela"],"französisch":["französisch","franzeesich","frankoprovenzalisch","französische"],"italienisch":["italienisch","idalieenisch","italiaanisch","italienische"],"jahre":["jahre","jaar","joor","jahr","johr"],"gewesen":["gewesen","gsii","gsy","gsi","gsi"],"hinzugekommen":["hinzugekommen","ufchùù","ufchuu","dazugekommen","hinzu","üfchùù"]}';
     nt='High-alpine Südwalser register: `Chilche`/`Schuel`/`franzeesich`/`Idalieenisch`/`gsii`/`ùfchùù`. Note the settlement is in Italy — this is Walser German, not a Swiss cantonal dialect, and must be labelled as such in any reporting.' }
)

$refSpec = @{
  'D001'='S2'; 'D002'='S3'; 'D003'='S8'; 'D004'='S3'; 'D005'='S3'; 'D006'='S4'; 'D007'='S7'
  'D008'='S5'; 'D009'='S14'; 'D010'='S5'; 'D011'='S6'; 'D012'='S22'
}

# --- extraction helpers -----------------------------------------------------
function Get-Verbatim([string]$path, [string]$prefix) {
  $lines = Get-Content -LiteralPath $path -Encoding UTF8
  $inside = $false
  foreach ($l in $lines) {
    if ($l -match '^=== VERBATIM SWISS GERMAN SENTENCES ===') { $inside = $true; continue }
    if ($l -match '^===') { $inside = $false }
    if ($inside -and $l.StartsWith('"' + $prefix)) {
      if ($l.StartsWith('"') -and $l.EndsWith('"')) {
        return $l.Substring(1, $l.Length - 2)
      }
      throw "VERBATIM line for '$prefix' is not a simple quoted span: $l"
    }
  }
  throw "VERBATIM sentence starting with '$prefix' not found in $path"
}

function Get-Reference([string]$path, [string]$snum) {
  $lines = Get-Content -LiteralPath $path -Encoding UTF8
  foreach ($l in $lines) {
    if ($l.StartsWith($snum + '. ')) {
      $arrow = [char]0x2192
      $idx = $l.LastIndexOf($arrow)
      if ($idx -lt 0) {
        # S057/S058 layout: the S#. line carries only the reference translation.
        if ($l.StartsWith($snum + '. "') -and $l.EndsWith('"')) {
          $t = $l.Substring(($snum + '. "').Length)
          return $t.Substring(0, $t.Length - 1)
        }
        throw "No translation separator in: $l"
      }
      $tail = $l.Substring($idx + 1).TrimStart()
      if ($tail.StartsWith('"') -and $tail.EndsWith('"')) {
        return $tail.Substring(1, $tail.Length - 2)
      }
      throw "Reference not a simple quoted span for $snum in $path"
    }
  }
  throw "Reference $snum not found in $path"
}

function Get-Header([string]$path, [string]$key) {
  $lines = Get-Content -LiteralPath $path -Encoding UTF8
  foreach ($l in $lines) {
    if ($l.StartsWith($key + ': ')) { return $l.Substring($key.Length + 2) }
  }
  throw "Header $key not found in $path"
}

$items = @()
foreach ($s in $spec) {
  $path = Join-Path $raw $s.f
  $sourceId = (Get-Header $path 'SOURCE_ID')
  $url      = (Get-Header $path 'URL')
  $ortho    = (Get-Header $path 'ORTHOGRAPHY')
  $verb     = Get-Verbatim $path $s.pre
  $ref      = Get-Reference $path $refSpec[$s.id]

  $items += [ordered]@{
    id                          = $s.id
    task_type                   = 'translation'
    dialect                      = $s.dia
    dialect_evidence             = $s.ev
    orthography                  = $ortho
    swiss_german_text            = $verb
    standard_german_reference    = $ref
    scoring                      = [ordered]@{
      type = 'content_keyword_coverage'
      synonyms = (ConvertFrom-Json $s.syn)
    }
    difficulty                   = $s.diff
    source_id                    = $sourceId
    source_url                   = $url
    validated_by                 = $null
    notes                        = $s.nt
  }
}

# --- T4 ---------------------------------------------------------------------
$t4 = @(
  @{ id='D013'; f='S057_alemannic_wikipedia_zurich_auslaender.txt'; pre='Schpaatussiidler gelted dernaa'; s=8;
     dia='zurich'; diff='easy'; ans='B';
     ev='S057 header `DIALECT: zurich`, explicit `{{Dialekt|Zürichdeutsch|Züridütsch}}`, city-Zürich article (C1 of the Brauerei file: this is the reference point for urban Zürich German).';
     opt='{"A":"Baseldytsch","B":"Züritüütsch","C":"Bärndütsch","D":"Walser/Wallisertiitsch"}';
     nt='Verified contrast: Ausländer C1 — `nöd` for `nicht`. Zürich harvest nöd 9 / nid 0; Bernese nid 6 / nöd 0; Basel nid 14 / nöd 0. C1 calls this "THE strongest lexical Basel+Bern vs Zürich opposition in the corpus" and the "headline Zürich/Bern contrast item". Corroborated by Zurich-only `Schpaatussiidler` (= Spätaussiedler) and `dernaa` (= demnach). NOT based on `hüt`/`hüüt`, which C6 of Brauerei records as shared by all three dialects.' }

  @{ id='D014'; f='S057_alemannic_wikipedia_bern_ismael.txt'; pre='Im Kapitel 17 chöme die zwöi'; s=12;
     dia='bern'; diff='medium'; ans='C';
     ev='S057 header `DIALECT: bern`, explicit `{{Dialekt|Berndeutsch|Bärndütsch|Bärndütsch}}`, standard Bärndütsch. The sentence also carries `Är`/`die`/`Name`, per Ismael C4/C1.';
     opt='{"A":"Baseldytsch","B":"Züritüütsch","C":"Bärndütsch","D":"Walser/Wallisertiitsch"}';
     nt='Verified contrast: `zwöi` = zwei. Bauern-Tabak C4 — Bernese harvest has `zwöi` 2 / `zwei` 0, the Zürich harvest has `zwei` 1 / `zwöi` 0, "a clean, usable minimal pair", both sides in-corpus. Restated as Ismael C3. Corroborated by Ismael C4 `Är` (Bernese vs Zürich `er`, both in-corpus) and C1 `Frou`/`Froue` (Bernese drops the -w-). CAVEAT: the Basel and Walser sides of the zwöi/zwei opposition are not attested in the harvest, so those two options are excluded by absence, not by a positive contrast.' }

  @{ id='D015'; f='S057_alemannic_wikipedia_walser_klosters.txt'; pre='Di Gmäind Chlooschtärsch ischt'; s=4;
     dia='walser'; diff='medium'; ans='D';
     ev='S057 header `DIALECT: walser`, `{{Dialekt|Walserdeutsch|Walsertiitsch|Walsertüütsch vam Chlooschtär}}`, SUBDIALECT_NOTE: genuine Walser German (Prättigau, Graubünden, Switzerland).';
     opt='{"A":"Baseldytsch","B":"Züritüütsch","C":"Bärndütsch","D":"Walser"}';
     nt='Two verified contrasts on one sentence. (1) Klosters C1: `ischt` for `ist` occurs ONLY in the alpine dialects (walser 2, valais 3) and is entirely absent from basel (156 `isch`), bern (24) and zurich (33). C1 explicitly states this CONTRADICTS the harvest brief''s Basel-vs-Zürich devoicing hypothesis and is the cleanest devoicing contrast in the corpus. (2) Klosters C2: `Gmäind` = Gemeinde is a THREE-WAY contrast — Wallis `Gmei` 3 / `Gmeind` 0, Zürich `Gmeind` 6 / `Gmäind` 0, Walser `Gmäind`. Basel is excluded as unusable here (infobox noise). The second marker rules out the Wallisertiitsch reading of `ischt`.' }

  @{ id='D016'; f='S057_alemannic_wikipedia_valais_ayent.txt'; pre='Dur ds Taal vaner Lienne'; s=3;
     dia='valais'; diff='medium'; ans='A';
     ev='S057 header `DIALECT: valais`, explicit `{{Dialekt|Walliserdeutsch|Wallisertiitsch|Wallisertitsch}}`. SUBDIALECT_NOTE: WALLISERTIITSCH (Höchstalemannisch, Valais German) — NOT Walser German; `valais` used deliberately rather than mislabelling it `walser`.';
     opt='{"A":"Wallisertiitsch","B":"Baseldytsch","C":"Bärndütsch","D":"Züritüütsch"}';
     nt='Verified contrast: Ayent C1 — `vaner`/`vanu` = von. C1: "THE most exclusive lexical marker in the corpus"; the forms occur only in the Wallisertiitsch harvest and are absent from basel, bern, zurich and walser, all of which use `vo` (Basel 242, Bern 23, Zürich 37) or, for Walser, `vù`/`vam` (8, per Issime C7). Restated as Blatten C3. All four distractors are therefore excluded by a POSITIVE contrast on the same slot, not by absence. Deliberately NOT using `Füesswäg`, which Ayent C6 corrects as SHARED Bernese/Wallisertiitsch rather than a Bernese marker.' }

  @{ id='D017'; f='S056_alemannic_wikipedia_basel_kartoffeldaempfer.txt'; pre='D'' Dämpfi isch bis in d'' sibziger'; s=1;
     dia='basel'; diff='medium'; ans='B';
     ev='S056 header `DIALECT: basel`; DIALECT_EVIDENCE places the article in village-spoken Basel-Landschaft Alemannisch (Mappach, canton Basel-Landschaft).';
     opt='{"A":"Bärndütsch","B":"Baseldytsch","C":"Züritüütsch","D":"Wallisertiitsch"}';
     nt='Verified contrast: `Joor` = Jahr, i.e. final devoicing of /r/. Bauern-Tabak C5: Bernese harvest `Jahr` 4 / `Joor` 0, Basel comparison sample `Joor` 17; Klosters C4 repeats it and states "the devoicing of Jahr is a shared West-/South-Alpine retention, not a Basel peculiarity"; Ayent C4 places the Wallisertiitsch on the OPPOSITE side (`eerschtu`, i.e. devoicing absent). Corroborated by Basel-only `Grumbiire`, `gare` and `Schwiinemascht` (LEXICAL NOTES L2, L3, L4). CAVEAT: Walser also writes `Joor` (Klosters C4, Issime C4), which is why Walser is NOT offered as an option here — including it would make the item ambiguous. The Wallisertiitsch distractor is excluded positively by the `eerschtu`/`Jahr` evidence in Ayent C4 and Blatten C8.' }
)

foreach ($t in $t4) {
  $path = Join-Path $raw $t.f
  $sourceId = (Get-Header $path 'SOURCE_ID')
  $url      = (Get-Header $path 'URL')
  $ortho    = (Get-Header $path 'ORTHOGRAPHY')
  $prompt   = Get-Verbatim $path $t.pre

  $items += [ordered]@{
    id                 = $t.id
    task_type          = 'dialect_identification'
    dialect             = $t.dia
    dialect_evidence    = $t.ev
    orthography         = $ortho
    prompt              = $prompt
    question            = 'Which Swiss German dialect is this sentence written in?'
    options             = (ConvertFrom-Json $t.opt)
    correct_answer      = $t.ans
    difficulty          = $t.diff
    source_id           = $sourceId
    source_url          = $url
    validated_by        = $null
    notes               = $t.nt
  }
}

$out = Join-Path $root 'data\dialect\items_D001_D017.json'
$json = $items | ConvertTo-Json -Depth 8
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($out, $json, $utf8NoBom)
Write-Output "wrote $out ($($items.Count) items)"
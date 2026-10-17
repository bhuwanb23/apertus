# Consent form template

**Status: TEMPLATE, NOT USED.** This benchmark collected no personal data from any
data subject, so no consent was solicited and none is recorded. This template is
shipped because the Hack Apertus rubric (Category 3, level 1) asks for an
appropriate consent form template to be provided, and because a template is the
only thing that can honestly be shipped when the answer is "no consent was
needed". Shipping it now means that if this benchmark ever gains a human-annotated
or human-recorded component, the instrument already exists and the dataset card
can point at it.

`DATASHEET.md` §3 records which requirement is not applicable and why, per
governance-template line.

---

## 1. When this template applies

Use it if any of the following becomes true. None is currently.

| Trigger | Applies to |
|---|---|
| A human annotator is paid or commissioned | their contributions |
| A participant is recorded (interview, survey, conversation) | the recordings and transcripts |
| Personal data appears in a test item | the item |
| Dialect items are validated by a named speaker and their voice is retained | the recordings |

## 2. Instrument

```
CONSENT FORM — Swiss Reality Check benchmark

Section A. Purpose
  1.1  What is this?
       The Swiss Reality Check benchmark measures how well a language model
       knows Swiss facts, Swiss institutional norms, and Swiss German.

  1.2  Why is your contribution needed?
       [ONE OF]
       (a) You are validating dialect items as a native speaker. Your judgements
           decide which items are kept.
       (b) You are annotating model responses against a published rubric.
       (c) You are providing source material for a test item.

  1.3  What will NOT happen with it
       Your contribution will not be used to train any model. It will be used
       only to score a model that already exists.

Section B. What is collected
  2.1  Your contributions: [describe precisely]
  2.2  What is NOT collected: no name, no contact details, no IP address, no
       device identifiers, no demographics beyond what 2.1 states.
  2.3  Storage: contributions are stored in this repository under the licence in
       section E, or held in aggregate as a score with no per-person record.

Section C. Risk, honestly stated
  3.1  Dialect validation carries a re-identification risk: a small set of
       speakers of a specific Alemannic variety can be identifiable from a
       recording. Mitigation: [recording is deleted after annotation / only
       derived text is retained / contributor is named only with consent].
  3.2  There is no other foreseeable risk to you. If there were, it would be
       listed here rather than in section F.

Section D. What you are agreeing to
  4.1  I have read sections A to C.
  4.2  I agree that my contributions may be published under the licence in E.
  4.3  I understand I may withdraw section 4.2 at any time, and that withdrawal
       removes future use but cannot retract a copy already downloaded.

Section E. Licence offered to you
  E.1  Your contributions: [CDLA-Permissive-2.0 / CC BY 4.0 / other - state one]
  E.2  Why this licence: it lets anyone use the benchmark, including
       commercially, without tracking you.

Section F. Contact and withdrawal
  F.1  Contact for withdrawal or questions: [email]
  F.2  Withdrawal response time: [n] working days.

Sign: ______________________   Name or pseudonym: ______________   Date: ________
```

## 3. Anonymity choices, and which this benchmark makes

| Choice | Setting here | Why |
|---|---|---|
| Attribution of annotators | none recorded | with 1 annotator, a "verified by" line is a fingerprint |
| Per-annotator record retained | no | a single score is the unit of evidence, not the person who gave it |
| Paid annotation | not applicable, none commissioned | — |
| Recording retention | not applicable | — |

Note on `validated_by`: the dialect items carry `validated_by: null`. When a
native speaker does validate them, that field records **a role, not a name**
(e.g. `native-speaker-1`) unless the validator asks to be named. A single named
speaker validating a small Alemannic variety is a re-identification vector, and
so is a name in a public repository.

## 4. What ships today

| File | What it is |
|---|---|
| `metadata/item_licensing.csv` | per-item licence, attribution and share-alike flags, and the basis for the classification |
| `metadata/source_registry.csv` | per-source URL, access date, and excerpt count |
| `DATASHEET.md` §3 | the not-applicable table, requirement by requirement |
| `data/sources/` | the verbatim excerpts each item was written from |
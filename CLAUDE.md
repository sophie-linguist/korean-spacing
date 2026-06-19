# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Note: this `korean-spacing/` directory is its own git repository, separate from the parent
> `lang-observatory` project. The parent `../CLAUDE.md` describes an unrelated neologism-detection
> system and does **not** apply here.

## Project Overview

An **offline Korean spacing (띄어쓰기) lookup tool**. Given a run-together expression (e.g. `할만하다`,
`아는데`, `차한대`), it consults the 우리말샘 dictionary and the 한글 맞춤법 spacing rules to explain
*why* a phrase should be spaced or joined, citing the relevant 항 (clause). It is an **explainer, not a
corrector**: it shows evidence (dictionary POS + rule) and lets the human decide.

**Core design principle**: precision over recall. When the answer is genuinely ambiguous (e.g. a head
that is both a noun and a verb stem), it shows *both* interpretations rather than guessing; when it has
no confidence, it stays silent and tells the user to re-search. Showing two answers for a
meaning-only-distinguishable ending (`-ㄴ데/-ㄴ지/-ㄴ바`) is correct behavior, not a bug.

**Deliberately no morphological analyzer** (no KoNLPy/mecab). Judgments come from three sources only:
the 우리말샘 dictionary, Hangul jamo arithmetic, and small hand-curated morpheme lists (particles, units,
auxiliary predicates). This keeps the tool deterministic, explainable, and shippable as a single exe.

## Commands

```bash
# Install (Python >= 3.11)
pip install -r requirements.txt          # or: pip install -e ".[dev]"

# Run the web UI (pywebview native window) — primary entry point
python -m shell.webui.app

# Run the legacy Tkinter UI
python -m shell.gui.app

# Tests
pytest                                    # all tests
pytest tests/test_conjugation.py          # one file
pytest tests/test_conjugation.py::test_decompose_codas   # one test
pytest -k homograph                       # by keyword

# Rebuild the dictionary index from a 우리말샘 JSON dump
python build/build_index.py \
  --source "전체 내려받기_우리말샘_json_20260603" \
  --output "dict.db" \
  --schema "build/schema.sql"
# (also regenerates core/aux_lexicon.json from the new DB)

# Build single-file Windows exe (PyInstaller, run on Windows)
powershell -ExecutionPolicy Bypass -File .\build\build_exe.ps1 -DictDbPath "dict.db"
```

**Test data dependency**: most tests are end-to-end and require the real `dict.db` (checked into the
repo, ~361 MB) resolved via the rules below. Only `test_build.py` builds its own temp DB from sample JSON.

## Architecture

### The judgment pipeline — `core/__init__.py:inspect()`

`inspect(text, db_path=None)` is the single orchestration entry point used by every UI shell. It returns
an `InspectResult` (see `core/schema.py`). The flow:

1. Normalize the query (`core/normalize.py`).
2. **제45항 connectives** (`및·겸·대·내지·등`) are checked *first*, before dictionary lookup, so multi-eojeol
   phrases aren't wrongly glued into a compound (`detect_connective`).
3. Dictionary lookup (`core/local_index.py:lookup`). **If found**, present the entry and append extra
   rule hints (제2항 word-is-listed, plus 제47항/제43항 cross-references where relevant).
4. **If not found**, run a strictly-ordered cascade of detectors, returning on the first match. Order
   matters and encodes precedence decisions (e.g. numerals before homographs so `만` in `12억3456만`
   isn't read as a dependent noun; particle chains before adnominal nouns so `너도`→`너+도`):
   `detect_numeral` → counter-phrase → counter-joined → `detect_homograph` → `_combined_result`
   → `detect_honorific` → `detect_compound` → `detect_particle_chain` → `detect_adnominal_noun`.
5. If nothing matches, return a silent "re-search" hint.

Every decision point appends a human-readable Korean line to `result.inspection_path` (which detector was
tried + `적용`/`해당 없음`); the last entry is the one that matched. Shells surface this as an "어떤 순서로
찾았는지" trace shown *after* the spacing judgment — it explains *how* the result was reached, not just what.

When editing the cascade, **preserve ordering and the comments explaining it** — each position prevents a
specific misclassification documented inline.

### The head-validation gate — `core/conjugation.py`

This is the conceptual core and the hardest module. To split a run-together chunk like `할만하다` into
`할` + `만하다`, the tool must confirm the head (`할`) is really a *predicate inflection* and not a noun
(so `주먹만하다` is **not** split into `주먹 만하다`). Mechanism, all deterministic:

- `restore_stem_candidates(head)` strips endings via jamo arithmetic + a finite ending table and an
  inverse-irregular-conjugation map (제15~18항, 제34~38항), **over-generating** stem+`다` candidates.
- The dictionary acts as a **self-filter**: only candidates registered as 동사/형용사 survive
  (`is_predicate_inflection`, `exists_with_pos`).
- `head_matches_base` / `base_forms_with_confidence` re-conjugate the surviving base forms forward and
  check the original head is reproduced — this assigns "정확도 높음" vs "참고" and drops non-standard
  homographs. Standard-language (`일반어`) predicates are preferred over dialect/archaic homographs.

Jamo functions (`decompose`, `compose`) operate on Unicode 완성형 syllable codepoints directly. Irregular
conjugations are encoded as explicit rule branches (ㄹ/ㅅ/ㄷ/ㅂ/ㅎ/르/러/ㅜ·ㅡ); some irregulars are
intentionally incomplete — over-generation is fine (self-filtered), but reverse maps that would cause
noun misclassification (e.g. `ㅏ←ㅡ`) are deliberately omitted.

### Detectors — `core/*.py`

Each handles one rule family and returns an `InspectResult` or `None` (silence): `numeral.py` (제43·44항,
units & 만-grouped large numbers — when a unit follows a man-grouped number it cites **both** 제44항 and
제43항, e.g. `삼천이백억오천만원`→`삼천이백억 오천만 원`; an already-correct large number returns a positive
confirmation `원칙허용="확인"` instead of silence), `homograph.py` (제41 vs 42 — particle vs dependent noun,
the `만큼·대로·데·지` split decided by the preceding word's POS), `compound.py` (제49·50항 — when a cover
piece is itself a `^`-spaced headword it is expanded to that spacing, e.g. `정상나선은하`→`정상 나선 은하`),
`particle.py` (제41항 chains), `adnoun.py` (제48항 adnominal + free noun), `connective.py` (제45항),
`honorific.py` (제48항), `caret_rule.py` (제49·50항, using the `^` morpheme-boundary marker from 우리말샘
headwords).

### Curated lists — closed by design

`core/segmenter.py` holds the combine-form tails: `_DEP_NOUN_TAILS` is **hand-curated** (the auto-extracted
1258-entry `dep_noun` list in `aux_lexicon.json` is *not used* because it pulls in common nouns that cause
misclassification — see the comment there), while auxiliary-verb tails come from `aux_lexicon.json`
(`aux_verb`, auto-extracted at build time) with an in-code fallback. Counters/quantifiers (제43항) are also
fixed tuples. **Keep these lists closed and curated**; widen only with care, since recall is traded for
precision intentionally.

### Data layer — `dict.db` (SQLite)

Single `entries` table (`build/schema.sql`) indexed from a 우리말샘 JSON dump by `build/build_index.py`
(streamed with `ijson`). Each headword stores `word_raw` (with `^`/`-` morpheme markers preserved),
`word_joined` (markers stripped, for joined lookup), `word_spaced`, `pos`, `definition`, `type`
(`일반어`/dialect/etc.), `cat`, and `has_caret`/`caret_count`. Lookups match on `word_joined` OR
`word_spaced`. **Caveat**: `word_spaced` turns *both* `^` (word boundary → space) and `-` (affix boundary →
stays joined) into spaces, so it over-splits (`위원-회`→`위원 회`). Code that needs the true spaced form
(e.g. `compound.py` piece expansion) must derive it from `word_raw` by spacing only `^` and dropping `-`.
Connections are cached per-path with `check_same_thread=False` (pywebview calls JS handlers
on a separate thread; reads are serial and read-only).

**DB path resolution** (`local_index.py:resolve_db_path`): explicit `db_path` arg → `KOREAN_SPACING_DB_PATH`
env var → `./dict.db` → `dict.db` next to the executable. Tests and UIs rely on this fallback chain.

### Rules data & presentation

`core/rules_data.json` / the top-level `*.json` files hold the clause text, examples, and commentary for
each 항; `core/pos_mapper.py` maps a dictionary entry's POS+definition to applicable clauses, and
`core/presenter.py` builds the display `Entry`/`InspectResult` (spacing badges, component breakdowns). UI
shells (`shell/webui/app.py`, `shell/gui/app.py`) only serialize `InspectResult` — **all linguistic logic
lives in `core/`**; keep shells thin.

## Conventions

- Code comments and docstrings are written in **Korean** and explain *linguistic rationale*, not just
  mechanics (which clause, which edge case is being prevented). Match this when editing `core/`.
- Detectors return `None` to mean "no confident judgment" — silence is a valid, intended outcome.
- Over-generation + dictionary self-filtering is the standard pattern for morphology; prefer it over
  trying to make jamo rules exhaustive.

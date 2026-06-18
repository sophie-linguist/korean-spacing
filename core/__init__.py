from __future__ import annotations

from typing import Any

from core.adnoun import detect_adnominal_noun
from core.caret_rule import caret_hint
from core.compound import detect_compound
from core.connective import detect_connective
from core.homograph import detect_homograph
from core.honorific import detect_honorific
from core.local_index import lookup
from core.normalize import normalize_query
from core.numeral import detect_numeral
from core.particle import detect_particle_chain
from core.conjugation import base_forms_with_confidence
from core.pos_mapper import map_entry
from core.presenter import make_component_entry, present
from core.schema import Entry, InspectResult, RuleHint
from core.segmenter import COUNTERS, segment, segment_combined

COUNTER_QUANTIFIERS = {"한", "두", "세", "네", "다섯", "여섯", "일곱", "여덟", "아홉", "열"}


def _unique_rule_hints(rule_hints: list[RuleHint]) -> list[RuleHint]:
    seen: set[tuple[str, str]] = set()
    unique: list[RuleHint] = []
    for hint in rule_hints:
        key = (hint.항번호, hint.원칙허용)
        if key in seen:
            continue
        seen.add(key)
        unique.append(hint)
    return unique


def _collect_rule_hints(entries: list[dict[str, Any]]) -> tuple[list[RuleHint], list[str]]:
    rule_hints: list[RuleHint] = []
    spacing_options: list[str] = []

    for entry in entries:
        pos = entry.get("pos") or ""
        definition = entry.get("definition") or ""
        word_raw = entry.get("word_raw") or ""

        for mapped in map_entry(pos, definition, word_raw.replace("^", "")):
            rule_hints.append(RuleHint(항번호=mapped.항번호, 원칙허용=mapped.원칙허용, 요지=mapped.요지))

        if entry.get("has_caret") == 1:
            ch = caret_hint(word_raw, entry.get("cat"))
            spacing_options.extend(ch.options)
            rule_hints.append(RuleHint(항번호=ch.rule, 원칙허용=ch.policy, 요지=ch.message))

    deduped_options = list(dict.fromkeys(spacing_options))
    return _unique_rule_hints(rule_hints), deduped_options


def _counter_phrase_result(normalized: str, segmentation) -> InspectResult | None:
    tokens = normalized.split()
    if len(tokens) < 2:
        return None

    last = tokens[-1]
    prev = tokens[-2]
    if last not in COUNTERS:
        return None
    if not (prev in COUNTER_QUANTIFIERS or prev.isdigit()):
        return None

    joined_last = " ".join(tokens[:-2] + [prev + last])
    rule = RuleHint(항번호="제43항", 원칙허용="원칙+허용", 요지="단위를 나타내는 명사는 띄어 씀을 원칙으로 하되 숫자/수 관형사 뒤에는 붙여 쓸 수 있습니다.")
    return InspectResult(
        input=normalized,
        found=True,
        rule_hints=[rule],
        spacing_options=[normalized, joined_last],
        segmentation=segmentation,
        notes=["이 표현은 단위 명사 문맥으로 판단되어 제43항 안내를 제공합니다."],
    )


def _counter_joined_result(normalized: str, segmentation) -> InspectResult | None:
    """붙은 입력('차한대')에서 수 관형사+단위명사 구조를 제43항으로 인식한다.

    segment()가 이미 '한+대'로 분리해 두므로, 그 결과(SegmentInfo)를 그대로 활용한다.
    동사 결합 경로(_combined_result)보다 먼저 호출해 '대' 같은 의존명사 꼬리가
    단위 구조를 가로채는 오탐('차한대'→'차한 대')을 막는다.
    """
    if segmentation is None or not segmentation.candidates:
        return None

    cand = segmentation.candidates[0]
    prefix = cand.original[: -(len(cand.left) + len(cand.right))]
    spaced = " ".join(filter(None, [prefix, cand.left, cand.right]))
    half_joined = " ".join(filter(None, [prefix, cand.left + cand.right]))

    rule = RuleHint(
        항번호="제43항",
        원칙허용="원칙+허용",
        요지="단위를 나타내는 명사는 띄어 씀을 원칙으로 하되 숫자/수 관형사 뒤에는 붙여 쓸 수 있습니다.",
    )
    return InspectResult(
        input=normalized,
        found=True,
        rule_hints=[rule],
        spacing_options=list(dict.fromkeys([spaced, half_joined])),
        segmentation=segmentation,
        notes=["수 관형사 + 단위 명사 구조로 판단되어 제43항을 안내합니다."],
    )


def _combined_result(normalized: str, db_path: str | None) -> InspectResult | None:
    """붙은 결합형('할만하다')을 머리 검증 게이트로 분리해 조항을 안내한다.

    머리가 용언 활용형으로 확인될 때만 결과를 만들고, 아니면 None(침묵)이다.
    """
    matched = segment_combined(normalized, db_path=db_path)
    if matched is None:
        return None

    segmentation, category, spaced = matched
    joined = "".join(normalized.split())

    head = segmentation.candidates[0].left
    tail = segmentation.candidates[0].right

    if category == "보조용언":
        rule = RuleHint(
            항번호="제47항",
            원칙허용="원칙+허용",
            요지="보조 용언은 띄어 씀을 원칙으로 하되 경우에 따라 붙여 씀도 허용합니다.",
        )
        note = "보조 용언 결합형으로 판단되어 제47항 원칙/허용을 함께 안내합니다."
        tail_prefer = ("보조 동사", "보조 형용사", "동사", "형용사")
        # 제47항: 띄어 씀(원칙)·붙여 씀(허용) 둘 다 가능.
        spacing_options = list(dict.fromkeys([spaced, joined]))
    else:
        rule = RuleHint(
            항번호="제42항",
            원칙허용="원칙",
            요지="의존 명사는 앞말과 띄어 씁니다.",
        )
        note = "관형사형 + 의존 명사 결합형으로 판단되어 제42항을 안내합니다."
        tail_prefer = ("의존 명사",)
        # 제42항: 의존 명사는 띄어 씀이 원칙 — 붙여 쓴 형은 옵션에서 제외.
        spacing_options = [spaced]

    entries = _combined_entries(head, tail, tail_prefer, db_path)

    return InspectResult(
        input=normalized,
        found=True,
        rule_hints=[rule],
        spacing_options=spacing_options,
        segmentation=segmentation,
        entries=entries,
        notes=[note],
    )


def _combined_entries(
    head: str, tail: str, tail_prefer: tuple[str, ...], db_path: str | None
) -> list[Entry]:
    """본용언 + 보조용언/의존명사 결합형의 구성요소 사전 정보를 만든다.

    본용언은 머리에서 기본형을 복원해 후보별 정확도를 함께 보인다.
    """
    entries: list[Entry] = []
    for base, high in base_forms_with_confidence(head, db_path=db_path):
        role = "본용언 · 정확도 높음" if high else "본용언 · 참고"
        e = make_component_entry(
            base, prefer=("동사", "형용사"), role=role, base_word=base, db_path=db_path
        )
        if e is not None:
            e.word = f"{head} → {base}"
            entries.append(e)

    tail_role = "보조 용언" if "보조" in tail_prefer[0] else "의존 명사"
    tail_entry = make_component_entry(tail, prefer=tail_prefer, role=tail_role, db_path=db_path)
    if tail_entry is not None:
        entries.append(tail_entry)
    return entries


def inspect(text: str, db_path: str | None = None) -> InspectResult:
    normalized = normalize_query(text)

    # 제45항 연결·열거어(및·겸·대·내지·등)는 여러 어절을 묶으므로, 단어 조회 전에
    # 먼저 처리해 합성어로 잘못 붙이지 않게 한다('이사장 및 이사' → '이사장및이사' 방지).
    connective_case = detect_connective(normalized)
    if connective_case is not None:
        return connective_case

    segmentation = segment(normalized)

    entries = lookup(normalized, db_path=db_path)
    result = present(entries, normalized)

    if not entries:
        # 수 + 단위(제43항) / 큰 수 만 단위(제44항)를 가장 먼저 본다.
        # '열두'를 한 단어로 인식(열두 마리)하고, '12억3456만'의 '만'을
        # 의존명사/조사로 오인하지 않도록 동형이의 분기보다 앞에 둔다.
        numeral_case = detect_numeral(normalized, db_path=db_path)
        if numeral_case is not None:
            numeral_case.segmentation = segmentation
            return numeral_case

        counter_case = _counter_phrase_result(normalized, segmentation)
        if counter_case is not None:
            return counter_case

        counter_joined_case = _counter_joined_result(normalized, segmentation)
        if counter_joined_case is not None:
            return counter_joined_case

        homograph_case = detect_homograph(normalized, db_path=db_path)
        if homograph_case is not None:
            return homograph_case

        combined_case = _combined_result(normalized, db_path)
        if combined_case is not None:
            return combined_case

        honorific_case = detect_honorific(normalized, db_path=db_path)
        if honorific_case is not None:
            return honorific_case

        compound_case = detect_compound(normalized, db_path=db_path)
        if compound_case is not None:
            return compound_case

        particle_case = detect_particle_chain(normalized, db_path=db_path)
        if particle_case is not None:
            return particle_case

        # 관형사 + 자립 명사(한잎 → 한 잎). 조사 연쇄(너도→너+도)에 우선권을 주기 위해
        # 조사·합성어 판별 뒤에 둔다.
        adnominal_case = detect_adnominal_noun(normalized, db_path=db_path)
        if adnominal_case is not None:
            adnominal_case.segmentation = segmentation
            return adnominal_case
        result.hint = "‘-다’로 끝나는 기본형(먹다·예쁘다)이나 ‘아는데·차한대’처럼 붙여 쓴 표현으로 검색해 보세요."
        result.segmentation = segmentation
        return result

    rule_hints, spacing_options = _collect_rule_hints(entries)

    # 사전에 한 단어로 등재된 표현이 보조용언 구성으로도 분석되는 경우(도와주다·알아보다 등):
    # 한 단어이므로 붙여 씀(제2항)이 우선이고, 보조용언으로 보면 띄어 쓸 수도 있음(제47항)을
    # 참고로 덧붙인다. (이 분기는 이미 'entries 발견'(=사전 등재) 경로이다.)
    combined_extra = _combined_result(normalized, db_path)
    if combined_extra is not None:
        joined = "".join(normalized.split())
        if not any(h.항번호 == "제2항" for h in rule_hints):
            rule_hints.insert(
                0,
                RuleHint(
                    항번호="제2항",
                    원칙허용="붙임",
                    요지="사전에 한 단어로 올라 있으므로 붙여 씁니다.",
                ),
            )
        if joined in spacing_options:
            spacing_options.remove(joined)
        spacing_options.insert(0, joined)  # 붙여 쓴 형(한 단어)을 맨 앞에
        for rh in combined_extra.rule_hints:
            if rh.항번호 == "제47항" and not any(h.항번호 == "제47항" for h in rule_hints):
                rule_hints.append(rh)
        for opt in combined_extra.spacing_options:
            if opt not in spacing_options:
                spacing_options.append(opt)

    # 수 병행 안내: '두마리(두마-리)·세개'처럼 우연히 사전에 있는 수+단위 표현이
    # 사전 풀이에 가려 띄어쓰기 안내가 비는 것을 막는다(제43·44항을 참고로 덧붙임).
    numeral_extra = detect_numeral(normalized, db_path, strong_only=True)
    if numeral_extra is not None:
        for rh in numeral_extra.rule_hints:
            if not any(h.항번호 == rh.항번호 for h in rule_hints):
                rule_hints.append(rh)
        for opt in numeral_extra.spacing_options:
            if opt not in spacing_options:
                spacing_options.append(opt)
        if numeral_extra.notes:
            result.notes = [*result.notes, f"수로 본다면 — {numeral_extra.notes[0]}"]

    result.rule_hints = rule_hints
    result.spacing_options = spacing_options
    result.segmentation = segmentation
    return result


__all__ = ["inspect", "InspectResult"]

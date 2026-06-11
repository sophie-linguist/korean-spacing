from __future__ import annotations

from typing import Any

from core.caret_rule import caret_hint
from core.compound import detect_compound
from core.homograph import detect_homograph
from core.honorific import detect_honorific
from core.local_index import lookup
from core.normalize import normalize_query
from core.particle import detect_particle_chain
from core.pos_mapper import map_entry
from core.presenter import present
from core.schema import InspectResult, RuleHint
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
    spacing_options = list(dict.fromkeys([spaced, joined]))

    if category == "보조용언":
        rule = RuleHint(
            항번호="제47항",
            원칙허용="원칙+허용",
            요지="보조 용언은 띄어 씀을 원칙으로 하되 경우에 따라 붙여 씀도 허용합니다.",
        )
        note = "보조 용언 결합형으로 판단되어 제47항 원칙/허용을 함께 안내합니다."
    else:
        rule = RuleHint(
            항번호="제42항",
            원칙허용="원칙",
            요지="의존 명사는 앞말과 띄어 씁니다.",
        )
        note = "관형사형 + 의존 명사 결합형으로 판단되어 제42항을 안내합니다."

    return InspectResult(
        input=normalized,
        found=True,
        rule_hints=[rule],
        spacing_options=spacing_options,
        segmentation=segmentation,
        notes=[note],
    )


def inspect(text: str, db_path: str | None = None) -> InspectResult:
    normalized = normalize_query(text)
    segmentation = segment(normalized)

    entries = lookup(normalized, db_path=db_path)
    result = present(entries, normalized)

    if not entries:
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
        result.hint = "‘-다’로 끝나는 기본형(먹다·예쁘다)이나 ‘아는데·차한대’처럼 붙여 쓴 표현으로 검색해 보세요."
        result.segmentation = segmentation
        return result

    rule_hints, spacing_options = _collect_rule_hints(entries)

    # 보조용언 병행 안내: 사전에 등재된 단어라도 보조용언 꼬리가 매칭되면 제47항 병행
    combined_extra = _combined_result(normalized, db_path)
    if combined_extra is not None:
        for rh in combined_extra.rule_hints:
            if rh.항번호 == "제47항" and not any(h.항번호 == "제47항" for h in rule_hints):
                rule_hints.append(rh)
        for opt in combined_extra.spacing_options:
            if opt not in spacing_options:
                spacing_options.append(opt)

    result.rule_hints = rule_hints
    result.spacing_options = spacing_options
    result.segmentation = segmentation
    return result


__all__ = ["inspect", "InspectResult"]

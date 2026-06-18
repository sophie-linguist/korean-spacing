"""동형이의 띄어쓰기 대비 카드 — 같은 글자, 다른 품사(띄움/붙임).

실제로 가장 많이 묻는 띄어쓰기는 '같은 글자가 의존 명사면 띄우고 조사/어미면 붙는'
경우다(데, 지, 만큼, 대로, 뿐, 만, 중, 간 …). 맥락에 따라 답이 갈리므로 자동 교정이
아니라 **두 해석을 품사·조항과 함께 나란히 보여 주고 사용자가 고르게** 한다.

표는 선별(curate)한다: 우리말샘의 '의존 명사 ∩ 조사' 자동 도출은 '게/도/이' 같은
고문체·우연 동음을 포함해 'X도/X들'마다 오발하기 때문이다. 대신 '앞말이 용언 활용형
이냐 체언이냐'는 conjugation 게이트로 자동 판별해 어느 해석이 맞는지 힌트를 준다.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.conjugation import is_predicate_inflection
from core.local_index import exists_with_pos
from core.presenter import make_component_entry
from core.schema import Entry, InspectResult, RuleHint

# 대비 유형
PARTICLE = "particle"   # 의존 명사(띄움) vs 조사(붙임)   — 용언/체언으로 자동 판별 가능
ENDING = "ending"       # 의존 명사(띄움) vs 어미(붙임)    — 둘 다 용언 뒤, 의미로 구별
BOUND = "bound"         # 명사·의존 명사(띄움) vs 굳은 합성어/접사(붙임)


@dataclass(slots=True)
class Reading:
    pos: str        # 품사 이름
    clause: str     # 조항 번호
    spacing: str    # "띄움" / "붙임"
    gloss: str      # 짧은 뜻
    example: str    # 예시


# 선별된 고빈도 동형이의. key는 입력 끝에서 떼어낼 글자.
HOMOGRAPHS: dict[str, tuple[str, list[Reading]]] = {
    "대로": (PARTICLE, [
        Reading("의존 명사", "제42항", "띄움", "용언 뒤, ‘~하는 그대로’", "본 대로, 들은 대로"),
        Reading("조사", "제41항", "붙임", "체언 뒤, ‘~와 같이’", "법대로, 마음대로"),
    ]),
    "만큼": (PARTICLE, [
        Reading("의존 명사", "제42항", "띄움", "용언 뒤, ‘그런 정도로’", "노력한 만큼, 아는 만큼"),
        Reading("조사", "제41항", "붙임", "체언 뒤, ‘~정도로’", "너만큼, 전봇대만큼"),
    ]),
    "만치": (PARTICLE, [
        Reading("의존 명사", "제42항", "띄움", "‘만큼’과 같은 의존 명사", "애쓴 만치"),
        Reading("조사", "제41항", "붙임", "‘만큼’과 같은 조사", "너만치"),
    ]),
    "뿐": (PARTICLE, [
        Reading("의존 명사", "제42항", "띄움", "용언 ‘-을’ 뒤, ‘다만 그러할 따름’", "웃을 뿐, 할 뿐"),
        Reading("조사", "제41항", "붙임", "체언 뒤, ‘그것만’", "너뿐, 셋뿐"),
    ]),
    "만": (PARTICLE, [
        Reading("의존 명사", "제42항", "띄움", "시간의 경과", "떠난 지 사흘 만에, 십 년 만에"),
        Reading("조사", "제41항", "붙임", "한정·강조", "너만, 하나만"),
    ]),
    "데": (ENDING, [
        Reading("의존 명사", "제42항", "띄움", "곳·경우·일", "아는 데까지, 머리 아픈 데 먹는 약"),
        Reading("어미 -ㄴ데/-는데", "제2항", "붙임", "배경·대조 연결", "비가 오는데 우산이 없다"),
    ]),
    "지": (ENDING, [
        Reading("의존 명사", "제42항", "띄움", "시간의 경과", "그를 만난 지 오래, 떠난 지 사흘"),
        Reading("어미 -ㄴ지/-는지", "제2항", "붙임", "막연한 의문", "올지 안 올지, 무엇을 할지"),
    ]),
    "바": (ENDING, [
        Reading("의존 명사", "제42항", "띄움", "앞말이 나타내는 일·방법", "느낀 바, 어찌할 바를 모르다"),
        Reading("어미 -ㄴ바", "제2항", "붙임", "‘~했더니/~했으므로’", "검토한바 이상이 없다"),
    ]),
    "중": (BOUND, [
        Reading("의존 명사", "제42항", "띄움", "여럿의 가운데 / ~하는 동안", "학생 중 하나, 회의 중"),
        Reading("한 단어", "제2항", "붙임", "굳어진 합성어", "은연중, 무의식중, 한밤중"),
    ]),
    "간": (BOUND, [
        Reading("의존 명사", "제42·45항", "띄움", "대상 사이·관계", "부모 자식 간, 서울 부산 간"),
        Reading("접미사 -간", "제2항", "붙임", "‘동안/장소’", "이틀간, 한 달간, 외양간"),
    ]),
    "전": (BOUND, [
        Reading("명사", "제2항", "띄움", "‘~ 앞·이전’", "식사 전, 출발 전"),
        Reading("한 단어", "제2항", "붙임", "굳어진 합성어", "오전, 직전, 생전"),
    ]),
    "후": (BOUND, [
        Reading("명사", "제2항", "띄움", "‘~ 뒤·다음’", "식사 후, 퇴근 후"),
        Reading("한 단어", "제2항", "붙임", "굳어진 합성어", "오후, 이후, 식후"),
    ]),
    "시": (BOUND, [
        Reading("의존 명사", "제42항", "띄움", "‘~할 때·경우’", "필요 시, 위급할 시"),
        Reading("한 단어", "제2항", "붙임", "굳어진 합성어", "비상시, 유사시"),
    ]),
    "내": (BOUND, [
        Reading("의존 명사", "제42항", "띄움", "‘일정 범위의 안’", "기한 내, 범위 내"),
        Reading("한 단어", "제2항", "붙임", "굳어진 합성어", "시내, 이내"),
    ]),
    "외": (BOUND, [
        Reading("의존 명사", "제42항", "띄움", "‘범위 밖·그것 말고’", "그 외, 예상 외"),
        Reading("한 단어", "제2항", "붙임", "굳어진 합성어", "이외, 의외"),
    ]),
}


# 동형이의 키가 분리 불가능한 복합 어미의 일부일 때 차단한다.
# 예: "든지"(-든지: 하든지 말든지, 얼마든지)는 단일 어미이므로 "든"+"지"로 가르면 안 된다.
_ENDING_BLOCKS: dict[str, tuple[str, ...]] = {
    "지": ("든", "던"),
}

# 앞말의 끝 음절이 이것이면 의존 명사(띄움) 해석을 억제하고 어미(붙임) 단일 안내만 한다.
# 의존 명사 '지'(시간 경과)는 과거 관형사형 -(으)ㄴ 뒤에만 온다(간 지, 떠난 지).
# '가는지'처럼 -는지로 끝나면 이는 어미이므로 '가는 지'로 띄우는 일은 거의 없다.
_BOUND_READING_BLOCK: dict[str, tuple[str, ...]] = {
    "지": ("는",),
}


def _prefix_entries(prefix: str, db_path: str | None) -> list[Entry]:
    """앞말이 사전에 등재된 체언이면 그 정보를 보인다.

    동형이의(데/지/중 …)는 '글자' 자체가 핵심이므로, 앞말이 용언 활용형이면
    본용언 복원은 후보가 과다(예: '가는'→가다·갈다·가늘다)해 노이즈가 되므로 생략한다.
    """
    noun = make_component_entry(
        prefix, prefer=("명사", "대명사", "수사"), role="앞말(체언)", db_path=db_path
    )
    return [noun] if noun is not None else []


def _key_entry(key: str, prefer: tuple[str, ...], role: str, db_path: str | None) -> Entry | None:
    return make_component_entry(key, prefer=prefer, role=role, db_path=db_path)


def _match(joined: str) -> str | None:
    """입력 끝에서 가장 긴 동형이의 글자를 찾는다(앞말이 있어야 함)."""
    best: str | None = None
    for key in HOMOGRAPHS:
        if joined.endswith(key) and len(joined) > len(key):
            if best is None or len(key) > len(best):
                best = key
    if best is not None:
        prefix = joined[: -len(best)]
        blockers = _ENDING_BLOCKS.get(best, ())
        if any(prefix.endswith(b) for b in blockers):
            return None
    return best


def _resolve_particle(prefix: str, db_path: str | None) -> str | None:
    """PARTICLE 유형에서 앞말 품사로 띄움/붙임을 확정한다.

    앞말이 용언 활용형 '전용'이면 의존 명사 → '띄움', 체언 '전용'이면 조사 → '붙임'.
    둘 다 가능하거나(예: ‘본’) 어느 쪽도 확인되지 않으면(미등재) None → 모호로 둔다.
    """
    pred = is_predicate_inflection(prefix, db_path=db_path)
    nominal = exists_with_pos(prefix, "%명사%", db_path) or exists_with_pos(
        prefix, "%대명사%", db_path
    )
    if pred and not nominal:
        return "띄움"
    if nominal and not pred:
        return "붙임"
    return None


def _rule_hint(r: Reading) -> RuleHint:
    return RuleHint(
        항번호=r.clause,
        원칙허용=r.spacing,
        요지=f"{r.pos}인 경우 {'띄어' if r.spacing == '띄움' else '붙여'} 씁니다 — {r.gloss} (예: {r.example})",
    )


def _ambiguous_hint(kind: str, prefix: str, spaced: str, joined: str, db_path: str | None) -> str:
    """확정 불가일 때 어느 해석이 맞는지 방향 힌트."""
    if kind == PARTICLE:
        if is_predicate_inflection(prefix, db_path=db_path):
            return f"여기서는 앞말 ‘{prefix}’이(가) 용언 활용형이라 의존 명사 → 띄어 씁니다: ‘{spaced}’."
        if exists_with_pos(prefix, "%명사%", db_path) or exists_with_pos(prefix, "%대명사%", db_path):
            return f"여기서는 앞말 ‘{prefix}’이(가) 체언이라 조사 → 붙여 씁니다: ‘{joined}’."
        return "앞말의 품사에 따라 갈립니다(용언 뒤→띄움, 체언 뒤→붙임)."
    if kind == ENDING:
        return "의미로 구별합니다: ‘곳·때·일’이면 띄우고(의존 명사), 연결·의문이면 붙입니다(어미)."
    return "앞말이 명사면 띄움이 원칙이고, 굳어진 합성어는 붙여 씁니다."


def detect_homograph(text: str, db_path: str | None = None) -> InspectResult | None:
    """입력이 동형이의 글자로 끝나면 띄움/붙임 안내를 만든다.

    앞말 품사로 한 해석이 확정되면(PARTICLE 유형) 정답 하나로 좁혀 안내하고,
    반대 해석은 조건부 '참고'로만 덧붙인다. 확정할 수 없으면 두 해석을 나란히 보인다.
    """
    joined = "".join(text.strip().split())
    key = _match(joined)
    if key is None:
        return None

    kind, readings = HOMOGRAPHS[key]
    prefix = joined[: -len(key)]
    if not prefix:
        return None

    spaced = f"{prefix} {key}"

    # 의존 명사 해석 억제: '가는지' 등 → 어미(붙임) 단일 안내.
    block = _BOUND_READING_BLOCK.get(key, ())
    if any(prefix.endswith(b) for b in block):
        ending = next((r for r in readings if r.spacing == "붙임"), readings[-1])
        entries = _prefix_entries(prefix, db_path)
        return InspectResult(
            input=text,
            found=True,
            rule_hints=[_rule_hint(ending)],
            spacing_options=[joined],
            entries=entries,
            notes=[
                f"‘{key}’ 앞이 ‘…{prefix[-1]}’로 끝나 어미(-{prefix[-1]}{key})로 봅니다 → 붙여 씁니다: ‘{joined}’.",
                f"의존 명사 ‘{key}’({readings[0].gloss})는 과거 관형사형 뒤에만 옵니다(예: {readings[0].example}).",
            ],
        )

    # BOUND 유형의 '한 단어(굳어진 합성어)' 붙임 해석은 사전 등재가 전제다.
    # 이 분기는 미등재 입력에서만 도달하므로(등재어는 사전 경로로 빠짐) 그 해석을 제외한다.
    # → '얼마전'은 '얼마 전'(띄움)만 안내하고 붙임은 보이지 않는다. ('간' 같은 접미사 붙임은 유지)
    if kind == BOUND:
        filtered = [r for r in readings if r.pos != "한 단어"]
        if filtered and len(filtered) < len(readings):
            readings = filtered
            if len(readings) == 1:
                only = readings[0]
                answer = spaced if only.spacing == "띄움" else joined
                entries = _prefix_entries(prefix, db_path)
                key_entry = _key_entry(
                    key, ("의존 명사", "명사", "접사"), only.pos, db_path
                )
                if key_entry is not None:
                    entries.append(key_entry)
                notes = [
                    f"‘{key}’은(는) {only.pos}(으)로 "
                    f"{'띄어' if only.spacing == '띄움' else '붙여'} 씁니다 — {only.gloss}."
                ]
                if only.spacing == "띄움":
                    notes.append(
                        f"‘{joined}’은 사전에 한 단어로 올라 있지 않으므로 붙여 쓰지 않습니다."
                    )
                return InspectResult(
                    input=text,
                    found=True,
                    rule_hints=[_rule_hint(only)],
                    spacing_options=[answer],
                    entries=entries,
                    notes=notes,
                )

    resolved = _resolve_particle(prefix, db_path) if kind == PARTICLE else None
    if resolved is not None:
        main = next(r for r in readings if r.spacing == resolved)
        other = next(r for r in readings if r.spacing != resolved)
        answer = spaced if resolved == "띄움" else joined
        if resolved == "띄움":
            decided = (
                f"앞말 ‘{prefix}’은(는) 용언 활용형이므로 ‘{key}’은(는) 의존 명사입니다 "
                f"→ 띄어 씁니다: ‘{answer}’."
            )
            ref = f"참고로 ‘{other.example}’처럼 체언 뒤에서는 ‘{key}’이(가) 조사가 되어 붙여 씁니다(제41항)."
        else:
            decided = (
                f"앞말 ‘{prefix}’은(는) 체언이므로 ‘{key}’은(는) 조사입니다 "
                f"→ 붙여 씁니다: ‘{answer}’."
            )
            ref = f"참고로 ‘{other.example}’처럼 용언 활용형 뒤에서는 ‘{key}’이(가) 의존 명사가 되어 띄어 씁니다(제42항)."
        key_prefer = ("의존 명사",) if main.spacing == "띄움" else ("조사", "접사")
        entries = _prefix_entries(prefix, db_path)
        key_entry = _key_entry(key, key_prefer, main.pos, db_path)
        if key_entry is not None:
            entries.append(key_entry)
        return InspectResult(
            input=text,
            found=True,
            rule_hints=[_rule_hint(main)],
            spacing_options=[answer],
            entries=entries,
            notes=[decided, ref],
        )

    rule_hints = [_rule_hint(r) for r in readings]
    notes = [
        "같은 글자라도 품사에 따라 띄어쓰기가 갈립니다 — 맥락을 보고 고르세요.",
        _ambiguous_hint(kind, prefix, spaced, joined, db_path),
    ]
    entries = _prefix_entries(prefix, db_path)
    key_entry = _key_entry(key, ("의존 명사", "조사", "접사"), readings[0].pos, db_path)
    if key_entry is not None:
        entries.append(key_entry)
    return InspectResult(
        input=text,
        found=True,
        rule_hints=rule_hints,
        spacing_options=list(dict.fromkeys([spaced, joined])),
        entries=entries,
        notes=notes,
    )

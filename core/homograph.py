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
from core.schema import InspectResult, RuleHint

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


def _prefix_hint(kind: str, prefix: str, spaced: str, joined: str, db_path: str | None) -> str:
    """앞말 성격으로 어느 해석이 맞는지 힌트(가능할 때만)."""
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
    """입력이 동형이의 글자로 끝나면 두 해석(띄움/붙임) 대비 카드를 만든다."""
    joined = "".join(text.strip().split())
    key = _match(joined)
    if key is None:
        return None

    kind, readings = HOMOGRAPHS[key]
    prefix = joined[: -len(key)]
    if not prefix:
        return None

    spaced = f"{prefix} {key}"
    rule_hints = [
        RuleHint(항번호=r.clause, 원칙허용=r.spacing, 요지=f"[{r.pos}] {r.gloss} (예: {r.example})")
        for r in readings
    ]
    notes = [
        "같은 글자라도 품사에 따라 띄어쓰기가 갈립니다 — 맥락을 보고 고르세요.",
        _prefix_hint(kind, prefix, spaced, joined, db_path),
    ]
    return InspectResult(
        input=text,
        found=True,
        rule_hints=rule_hints,
        spacing_options=list(dict.fromkeys([spaced, joined])),
        notes=notes,
    )

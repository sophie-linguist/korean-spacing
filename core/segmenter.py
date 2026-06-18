from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from core.conjugation import is_predicate_inflection
from core.schema import SegmentCandidate, SegmentInfo

# 결합형 꼬리(닫힌 집합). 우리말샘에서 자동추출한 core/aux_lexicon.json을 우선 사용하고,
# 파일이 없으면 아래 내장 폴백 목록을 쓴다(테스트/최소 배포용).
# 본용언계 보조용언은 연결어미 뒤, 의존명사·보조형용사는 관형사형 뒤에 온다.
_FALLBACK_AUX_VERB_TAILS = (
    "만하다", "듯하다", "법하다", "직하다", "뻔하다", "척하다", "체하다",
    "성싶다", "듯싶다",
    "보다", "주다", "버리다", "두다", "놓다", "싶다", "말다", "대다",
    "가다", "오다", "내다",
)
# 검증된 형식성 의존 명사 목록(수작업 큐레이션).
# 주의: aux_lexicon.json의 자동추출 dep_noun(1258개)은 일반명사('잎·도·끝·물·힘'…)가
# 대거 섞여 있어 오분할('한잎'→'한 잎' 의존명사, '너도'→'너 도')을 일으키므로 쓰지 않는다.
_DEP_NOUN_TAILS = (
    "것", "거", "데", "바", "수", "줄", "리", "뿐", "채", "체", "척", "양", "듯",
    "만큼", "만치", "대로", "만", "지", "터", "뻔", "법", "직",
    "따위", "때문", "마련", "무렵", "즈음", "노릇", "나름", "따름", "나위",
    "겸", "등", "딴", "둥", "망정", "셈", "족족",
)

_LEXICON_PATH = Path(__file__).with_name("aux_lexicon.json")


@lru_cache(maxsize=1)
def _tail_category() -> dict[str, str]:
    """꼬리 → 분류('보조용언'/'의존명사') 매핑.

    의존명사는 큐레이션 목록(_DEP_NOUN_TAILS)을 쓰고, 보조용언은 aux_lexicon.json의
    aux_verb를 쓰되 파일이 없으면 폴백한다.
    """
    aux: tuple[str, ...] = _FALLBACK_AUX_VERB_TAILS
    if _LEXICON_PATH.exists():
        data = json.loads(_LEXICON_PATH.read_text(encoding="utf-8"))
        aux = tuple(data.get("aux_verb", _FALLBACK_AUX_VERB_TAILS))
    mapping = {t: "의존명사" for t in _DEP_NOUN_TAILS}
    mapping.update({t: "보조용언" for t in aux})  # 겹치면 보조 용언 우선
    return mapping

COUNTERS = (
    "마리",
    "켤레",
    "자루",
    "벌",
    "채",
    "개",
    "대",
    "손",
    "죽",
)

QUANTIFIERS = (
    "다섯",
    "여섯",
    "일곱",
    "여덟",
    "아홉",
    "열",
    "한",
    "두",
    "세",
    "네",
)


def segment(text: str) -> SegmentInfo | None:
    normalized = "".join(text.strip().split())
    if not normalized:
        return None

    for counter in COUNTERS:
        if not normalized.endswith(counter):
            continue

        stem = normalized[: -len(counter)]
        if not stem:
            continue

        for quantifier in QUANTIFIERS:
            if not stem.endswith(quantifier):
                continue

            candidate = SegmentCandidate(
                original=normalized,
                left=quantifier,
                right=counter,
                hint=f"'{counter}'가 단위 의존명사로 쓰이면 제43항에 따라 띄어 쓸 수 있습니다.",
            )
            return SegmentInfo(
                message="나눠질 수 있는 덩어리",
                candidates=[candidate],
            )

    return None


def _match_tail(joined: str) -> tuple[str, str] | None:
    """joined 문자열 끝에서 가장 긴 결합형 꼬리를 찾아 (꼬리, 분류)를 돌려준다."""
    best: tuple[str, str] | None = None
    for tail, category in _tail_category().items():
        if joined.endswith(tail) and len(joined) > len(tail):
            if best is None or len(tail) > len(best[0]):
                best = (tail, category)
    return best


def segment_combined(text: str, db_path: str | None = None) -> tuple[SegmentInfo, str, str] | None:
    """'할만하다'처럼 붙은 결합형을 '머리 + 꼬리'로 분리한다.

    최장 꼬리 매칭으로 꼬리를 떼고, 머리가 용언 활용형인지 게이트로 검증한다.
    검증을 통과하지 못하면 None(침묵)을 돌려 명사 오분할을 막는다.

    반환: (SegmentInfo, 꼬리분류, 띄어쓴_표기). 분류는 '보조용언' 또는 '의존명사'.
    """
    joined = "".join(text.strip().split())
    if not joined:
        return None

    matched = _match_tail(joined)
    if matched is None:
        return None

    tail, category = matched
    head = joined[: -len(tail)]
    if not head:
        return None

    if not is_predicate_inflection(head, db_path=db_path):
        return None

    if category == "보조용언":
        hint = f"'{tail}'은(는) 보조 용언으로, 제47항에 따라 띄어 씀이 원칙이고 붙여 씀도 허용됩니다."
    else:
        hint = f"'{tail}'이(가) 의존 명사로 쓰이면 제42항에 따라 앞말과 띄어 씁니다."

    candidate = SegmentCandidate(
        original=joined,
        left=head,
        right=tail,
        hint=hint,
    )
    info = SegmentInfo(message="나눠질 수 있는 덩어리", candidates=[candidate])
    spaced = f"{head} {tail}"
    return info, category, spaced

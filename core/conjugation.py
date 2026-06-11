"""머리(용언 활용형) 검증 게이트 — 형태소분석기 없이 자모 연산 + 어미 표로 판정.

결합형 덩어리(예: '할만하다')를 '할' + '만하다'로 가를 때, 머리 '할'이 정말로
용언의 활용형인지 확인해 명사 오분할('주먹만하다'→'주먹 만하다')을 막는다.

원리: 보조용언/의존명사 앞에 올 수 있는 어미는 닫힌 집합이다. 머리에서 그 어미를
떼어 어간을 복원하고, '-다'를 붙인 기본형이 사전에 동사/형용사로 등록돼 있으면 통과.
모든 단계가 결정적 규칙(유니코드 자모 산술 + 유한 어미 표)이라 통계 모델이 없다.

1차 범위: 규칙활용만. 불규칙(ㅂ/ㄷ/르/ㅎ)은 2차.
"""

from __future__ import annotations

from core.local_index import exists_with_pos

_HANGUL_BASE = 0xAC00
_HANGUL_LAST = 0xD7A3
_JONG_COUNT = 28  # 종성 개수(없음 포함)

# 종성 인덱스(유니코드 종성 배열 기준)
_JONG_NONE = 0
_JONG_N = 4   # ㄴ
_JONG_D = 7   # ㄷ
_JONG_L = 8   # ㄹ
_JONG_B = 17  # ㅂ
_JONG_S = 19  # ㅅ

_CHO_IEUNG = 11   # 초성 ㅇ
_JUNG_O = 8       # 중성 ㅗ
_JUNG_U = 13      # 중성 ㅜ

# 본용언계 보조용언 앞에 오는 보조적 연결어미(한 음절 형태).
_CONNECTIVE_SYLLABLES = ("아", "어", "여", "게", "지", "고", "서")

# 관형사형으로 쓰여 의존명사·보조형용사 앞에 오는 한 음절 어미.
_ADNOMINAL_SYLLABLES = ("을", "은", "는")

# 어간 복원이 불규칙이라 음절 분해로는 못 잡지만 매우 흔한 형태(여 불규칙 '하다').
_FUSED_HEADS = {
    "해": "하다",
    "하여": "하다",
}

_VERB_ADJ_POS_LIKE = "%동사%"  # '%형용사%'와 함께 OR로 검사
_ADJ_POS_LIKE = "%형용사%"


def is_hangul_syllable(ch: str) -> bool:
    return len(ch) == 1 and _HANGUL_BASE <= ord(ch) <= _HANGUL_LAST


def decompose(syllable: str) -> tuple[int, int, int]:
    """완성형 한글 음절을 (초성, 중성, 종성) 인덱스로 분해한다. 비한글이면 ValueError."""
    if not is_hangul_syllable(syllable):
        raise ValueError(f"not a hangul syllable: {syllable!r}")
    code = ord(syllable) - _HANGUL_BASE
    cho = code // (21 * _JONG_COUNT)
    jung = (code % (21 * _JONG_COUNT)) // _JONG_COUNT
    jong = code % _JONG_COUNT
    return cho, jung, jong


def compose(cho: int, jung: int, jong: int) -> str:
    """(초성, 중성, 종성) 인덱스를 완성형 한글 음절로 합성한다."""
    code = _HANGUL_BASE + (cho * 21 + jung) * _JONG_COUNT + jong
    return chr(code)


def _strip_coda(syllable: str) -> str:
    """음절의 종성을 떼어낸 음절을 돌려준다(받침 없는 음절)."""
    cho, jung, _ = decompose(syllable)
    return compose(cho, jung, _JONG_NONE)


def restore_stem_candidates(head: str) -> list[str]:
    """머리에서 어미를 떼어 가능한 기본형('어간'+'다') 후보들을 만든다.

    규칙활용 + 흔한 불규칙(ㄹ탈락/ㄷ/ㅂ/ㅅ)을 다룬다. 후보는 과생성해도 되며,
    사전 조회로 실제 동사/형용사만 살아남는다(self-filter).
    """
    stems: list[str] = []

    def add_stem(stem: str) -> None:
        if stem and stem not in stems:
            stems.append(stem)

    # 1) 한 음절 어미(을/은/는/게/지/고/아/어/여/서 …)를 통째로 떼기.
    for ending in (*_CONNECTIVE_SYLLABLES, *_ADNOMINAL_SYLLABLES):
        if len(ending) == 1 and is_hangul_syllable(ending):
            if len(head) > 1 and head.endswith(ending):
                add_stem(head[:-1])

    # 2) 마지막 음절의 종성이 어미인 경우(관형사형 -ㄹ/-ㄴ): 종성만 제거.
    last = head[-1]
    if is_hangul_syllable(last):
        _, _, jong = decompose(last)
        if jong in (_JONG_L, _JONG_N):
            add_stem(head[:-1] + _strip_coda(last))

    # 3) 규칙 어간에서 불규칙 원형 후보 파생(아는→알, 들을→듣, 도우→돕 …).
    for s in list(stems):
        for variant in _irregular_stem_variants(s):
            add_stem(variant)

    candidates = [s + "다" for s in stems]
    # 융합형(여 불규칙 등 매우 흔한 예외) 직접 매핑.
    if head in _FUSED_HEADS:
        basic = _FUSED_HEADS[head]
        if basic not in candidates:
            candidates.insert(0, basic)
    return candidates


def _irregular_stem_variants(stem: str) -> list[str]:
    """규칙 어간 후보에서 불규칙 용언의 원형 어간을 파생한다(사전으로 self-filter)."""
    out: list[str] = []
    last = stem[-1]
    if not is_hangul_syllable(last):
        return out
    cho, jung, jong = decompose(last)

    if jong == _JONG_NONE:
        # ㄹ 불규칙(ㄹ 탈락 복원): 아는→알, 사는→살, 만드는→만들
        out.append(stem[:-1] + compose(cho, jung, _JONG_L))
        # ㅅ 불규칙: 지은→짓, 나아→낫
        out.append(stem[:-1] + compose(cho, jung, _JONG_S))
    if jong == _JONG_L:
        # ㄷ 불규칙: 들을→듣, 걸은→걷, 실은→싣
        out.append(stem[:-1] + compose(cho, jung, _JONG_D))
    # ㅂ 불규칙: 도우→돕, 고우→곱 (끝이 ㅇ+오/우, 받침 없음 → 앞 음절에 ㅂ받침)
    if cho == _CHO_IEUNG and jung in (_JUNG_O, _JUNG_U) and jong == _JONG_NONE and len(stem) >= 2:
        prev = stem[-2]
        if is_hangul_syllable(prev):
            pc, pj, pjong = decompose(prev)
            if pjong == _JONG_NONE:
                out.append(stem[:-2] + compose(pc, pj, _JONG_B))
    return out


def _is_registered_predicate(basic_form: str) -> bool:
    """기본형이 사전에 동사 또는 형용사로 등록돼 있는지."""
    return exists_with_pos(basic_form, _VERB_ADJ_POS_LIKE) or exists_with_pos(
        basic_form, _ADJ_POS_LIKE
    )


def is_predicate_inflection(head: str, db_path: str | None = None) -> bool:
    """머리가 용언 활용형으로 볼 수 있는지 판정한다(게이트).

    어미를 떼어 복원한 기본형 후보 중 하나라도 사전의 동사/형용사면 True.
    하나도 없으면 False → 호출부는 분리를 포기하고 침묵한다.
    """
    head = head.strip()
    if not head:
        return False

    for basic_form in restore_stem_candidates(head):
        if _is_registered_predicate(basic_form):
            return True
    return False

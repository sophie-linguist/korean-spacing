from __future__ import annotations

import pytest

from core import conjugation as cj


def test_decompose_compose_roundtrip():
    for ch in ["할", "먹", "읽", "강", "뷁"]:
        cho, jung, jong = cj.decompose(ch)
        assert cj.compose(cho, jung, jong) == ch


def test_decompose_codas():
    # 할 = ㅎ ㅏ ㄹ (종성 ㄹ)
    assert cj.decompose("할")[2] == cj._JONG_L
    # 간 = ㄱ ㅏ ㄴ (종성 ㄴ)
    assert cj.decompose("간")[2] == cj._JONG_N
    # 하 = 종성 없음
    assert cj.decompose("하")[2] == cj._JONG_NONE


def test_decompose_rejects_non_hangul():
    with pytest.raises(ValueError):
        cj.decompose("A")
    with pytest.raises(ValueError):
        cj.decompose("ㄴ")  # 호환 자모는 완성형 음절이 아님


@pytest.mark.parametrize(
    "head,expected_basic",
    [
        ("할", "하다"),      # 관형사형 -ㄹ
        ("갈", "가다"),
        ("간", "가다"),      # 관형사형 -ㄴ
        ("먹을", "먹다"),    # 관형사형 -을
        ("읽는", "읽다"),    # 관형사형 -는
        ("먹은", "먹다"),    # 관형사형 -은
        ("먹어", "먹다"),    # 연결 -어
        ("가서", "가다"),    # 연결 -서
        ("읽고", "읽다"),    # 연결 -고
        ("해", "하다"),      # 융합형(여 불규칙)
    ],
)
def test_restore_stem_includes_expected(head, expected_basic):
    assert expected_basic in cj.restore_stem_candidates(head)


# --- 게이트: DB(dict.db) 필요 ---

def test_gate_accepts_inflections():
    for head in ["할", "먹을", "읽는", "먹어", "가서", "해"]:
        assert cj.is_predicate_inflection(head) is True, head


def test_gate_rejects_nouns():
    # 명사 머리는 활용형이 아니므로 거부 → 오분할 방지
    for head in ["주먹", "사과", "사람"]:
        assert cj.is_predicate_inflection(head) is False, head


def test_gate_empty():
    assert cj.is_predicate_inflection("") is False
    assert cj.is_predicate_inflection("   ") is False


# --- 제18항 불규칙 활용 + 제34~38항 준말: 게이트 통과 + 표준 기본형 '정확도 높음' ---
# 예시는 업로드된 한글 맞춤법 형태 규정(맞춤법_형태_규정.json)에서 도출.

@pytest.mark.parametrize(
    "head,expected_base",
    [
        # 르 불규칙(제18항 ⑨)
        ("불러", "부르다"), ("갈라", "가르다"), ("몰라", "모르다"), ("흘러", "흐르다"),
        # 러 불규칙(제18항 ⑧)
        ("이르러", "이르다"),
        # ㅂ 불규칙(제18항 ⑥)
        ("도와", "돕다"), ("구워", "굽다"), ("고와", "곱다"),
        # ㅎ 불규칙(제18항 ③)
        ("그래", "그렇다"), ("노래", "노랗다"), ("빨개", "빨갛다"),
        # ㅜ/ㅡ 탈락(제18항 ④)
        ("퍼", "푸다"), ("꺼", "끄다"),
        # ㅅ·ㄷ 불규칙(제18항 ②⑤)
        ("지어", "짓다"), ("걸어", "걷다"),
        # 준말/모음 축약(제34~38항)
        ("봐", "보다"), ("와", "오다"), ("줘", "주다"), ("돼", "되다"), ("해", "하다"),
        ("보여", "보이다"), ("가", "가다"),
    ],
)
def test_irregular_gate_and_restore(head, expected_base):
    assert cj.is_predicate_inflection(head) is True, f"gate failed: {head}"
    high = [b for b, ok in cj.base_forms_with_confidence(head) if ok]
    assert expected_base in high, f"{head}: {expected_base} not in high={high}"


def test_gate_rejects_more_nouns():
    # 명사 오분할 방지 — 흔한 명사는 거부되어야 한다.
    for n in ["나라", "자라", "다리", "우리", "허리", "시간", "학교", "마음", "나무"]:
        assert cj.is_predicate_inflection(n) is False, n

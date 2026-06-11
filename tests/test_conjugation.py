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

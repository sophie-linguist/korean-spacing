"""제45항 — 연결·열거어(및·겸·대·내지·등) 띄어쓰기 end-to-end (dict.db 필요)."""

from __future__ import annotations

from core import inspect


def _clauses(r):
    return {h.항번호 for h in r.rule_hints}


def test_connecting_words_spaced():
    # 가운데 이어 주는 말: 및·겸·대·내지
    for q in ["한국어 및 한국문화", "청군 대 백군", "부장 겸 대표", "하나 내지 둘"]:
        r = inspect(q)
        assert _clauses(r) == {"제45항"}, q
        assert r.spacing_options == [q], q


def test_enumeration_word_spaced():
    # 끝의 열거 말: 등
    for q in ["책상 의자 등", "사과 배 귤 등"]:
        r = inspect(q)
        assert _clauses(r) == {"제45항"}, q


def test_joined_input_with_mit_is_split():
    # 붙여 써도 '및'은 안전하게 가른다(합성어로 붙이지 않음)
    r = inspect("한국어및한국문화")
    assert _clauses(r) == {"제45항"}
    assert r.spacing_options == ["한국어 및 한국문화"]


def test_does_not_wrongly_join_connective_phrase():
    # 회귀 방지: '이사장 및 이사'를 '이사장및이사'로 붙이면 안 됨
    r = inspect("이사장 및 이사")
    assert "이사장및이사" not in r.spacing_options
    assert r.spacing_options == ["이사장 및 이사"]


def test_no_false_positive_on_normal_words():
    # '등·대'가 단어 속에 있어도 제45항으로 오인하면 안 됨
    for q in ["시대", "평등", "고등학교", "대학교"]:
        assert "제45항" not in _clauses(inspect(q)), q
    # 수 + 단위 '대'는 그대로 제43항
    assert "제45항" not in _clauses(inspect("차 한 대"))
    # 명사 결합 '한국 문화'는 그대로 제50항
    assert "제45항" not in _clauses(inspect("한국 문화"))

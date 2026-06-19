"""수 띄어쓰기 — 제43항(수+단위)·제44항(만 단위) end-to-end (dict.db 필요)."""

from __future__ import annotations

from core import inspect


def _clauses(r):
    return {h.항번호 for h in r.rule_hints}


def test_native_number_plus_unit():
    # 고유어 수 + 단위 → 제43항(원칙 띄움/허용 붙임)
    for q, spaced in [("두마리", "두 마리"), ("세개", "세 개"), ("다섯권", "다섯 권"),
                      ("스물한살", "스물한 살")]:
        r = inspect(q)
        assert "제43항" in _clauses(r), q
        assert spaced in r.spacing_options, q


def test_compound_native_number_stays_whole():
    # '열두'는 한 단어 → '열두 마리'(열 두 마리 아님)
    r = inspect("열두마리")
    assert r.spacing_options[0] == "열두 마리"
    assert "열 두 마리" not in r.spacing_options


def test_bare_seumul_becomes_seumu_before_unit():
    # 단독 '스물'은 단위 앞에서 '스무'
    assert inspect("스물살").spacing_options[0] == "스무 살"


def test_sino_number_plus_unit():
    for q, spaced in [("오백원", "오백 원"), ("이천이십육년", "이천이십육 년")]:
        r = inspect(q)
        assert "제43항" in _clauses(r), q
        assert spaced in r.spacing_options, q


def test_noun_plus_number_plus_unit():
    # 명사 + 수 + 단위: 앞 명사는 그대로 두고 수·단위만 띄움
    for q, spaced in [("차한대", "차 한 대"), ("사과두개", "사과 두 개")]:
        r = inspect(q)
        assert "제43항" in _clauses(r), q
        assert spaced in r.spacing_options, q


def test_large_number_man_units():
    # 제44항: 만/억/조 단위로 띄어 씀
    for q, spaced in [("십이억삼천사백오십육", "십이억 삼천사백오십육"),
                      ("만이천", "만 이천"), ("12억3456만", "12억 3456만")]:
        r = inspect(q)
        assert "제44항" in _clauses(r), q
        assert spaced in r.spacing_options, q


def test_large_number_plus_unit_cites_both_clauses():
    # 만 단위 띄어쓰기(제44항)와 단위 명사 띄어쓰기(제43항)가 함께 적용되는 경우
    for q, spaced in [("삼천이백억오천만원", "삼천이백억 오천만 원"),
                      ("12억3456만원", "12억 3456만 원")]:
        r = inspect(q)
        cl = _clauses(r)
        assert "제44항" in cl and "제43항" in cl, q
        assert spaced in r.spacing_options, q


def test_man_in_large_number_not_treated_as_homograph():
    # '12억3456만'의 '만'은 수 단위지 의존명사/조사가 아님
    assert _clauses(inspect("12억3456만")) == {"제44항"}


def test_already_correct_large_number_gets_positive_confirmation():
    # 만/억/조가 맨 끝이라 띄울 곳이 없는 큰 수는 침묵 대신 '이대로 맞다'고 확인한다.
    for q in ["삼천이백억", "이천억"]:
        r = inspect(q)
        assert r.found, q
        assert "제44항" in _clauses(r), q
        assert r.spacing_options == [q], q
        assert any("바르게 적혔" in n for n in r.notes), q


def test_plain_number_without_man_unit_stays_silent():
    # 만 단위가 없는 수(삼백)는 제44항 확인 대상이 아니다(억지 확인 금지).
    assert "제44항" not in _clauses(inspect("삼백"))


def test_dictionary_word_still_gets_number_guidance():
    # 사전에 우연히 있는 '두마리(두마-리)'도 제43항 안내가 비지 않음(가림 방지)
    r = inspect("두마리")
    assert "제43항" in _clauses(r)
    assert "두 마리" in r.spacing_options


def test_no_false_positive_on_common_words():
    # 단위 글자로 끝나도 앞이 수가 아니면 제43/44가 끼면 안 됨
    for q in ["도서관", "서원", "사장", "공장", "사건", "사자", "일단", "병원"]:
        cl = _clauses(inspect(q))
        assert "제43항" not in cl and "제44항" not in cl, q

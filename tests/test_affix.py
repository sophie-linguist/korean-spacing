"""접두사 + 자립 명사 인식 — 제2항(접사 붙임) end-to-end (dict.db 필요)."""

from __future__ import annotations

from core import inspect


def _policies(r):
    return {(h.항번호, h.원칙허용) for h in r.rule_hints}


def test_prefix_plus_noun_joins():
    # 미등재 '접두사 + 자립 명사'는 붙여 씀을 안내한다(본구축 → 본+구축).
    for q in ["본구축", "본수술"]:
        r = inspect(q)
        assert r.found, q
        assert q in r.spacing_options, q  # 붙여 쓴 형이 후보에 있다
        assert ("제2항", "붙임") in _policies(r), q


def test_prefix_that_is_also_determiner_shows_both():
    # 본·맨처럼 접두사이자 관형사인 글자는 붙임(본구축)·띄움(본 구축)을 함께 보인다.
    r = inspect("본구축")
    assert "본구축" in r.spacing_options and "본 구축" in r.spacing_options
    assert ("제2항", "붙임") in _policies(r)
    assert ("제2항", "띄움") in _policies(r)


def test_prefix_not_split_as_number_unit():
    # '본구축'이 수+단위('본 구 축')로 잘못 쪼개지지 않는다(약한 한 글자 한자수 억제).
    r = inspect("본구축")
    assert "본 구 축" not in r.spacing_options
    assert "제43항" not in {h.항번호 for h in r.rule_hints}


def test_registered_compound_not_overridden_by_affix():
    # 사전에 한 단어로 등재된 파생어(본계약 등)는 affix가 아니라 사전 조회로 처리된다.
    r = inspect("본계약")
    assert r.found
    assert r.entries and any("명사" in (e.pos or "") for e in r.entries)


def test_counter_structure_not_eaten_by_affix():
    # 접두사 detector가 늦은 자리라 단위 구조(차 한 대)를 가로채지 않는다.
    assert "차 한 대" in inspect("차한대").spacing_options
    assert "사과 한 개" in inspect("사과한개").spacing_options


def test_adnominal_determiner_unchanged():
    # 관형사 목록(한·새·첫…)은 종전대로 띄움(한 잎)으로 처리된다.
    assert inspect("한잎").spacing_options == ["한 잎"]


def test_non_noun_rest_stays_silent():
    # 뒤가 자립 명사가 아니면 침묵(정밀도 우선).
    r = inspect("풋고추맛")  # '고추맛'은 자립 명사 미등재
    assert not r.spacing_options

"""관형사+명사(제2항) 인식 및 조사 연쇄 과분해 방지 end-to-end (dict.db 필요)."""

from __future__ import annotations

from core import inspect


def _clauses(r):
    return {h.항번호 for h in r.rule_hints}


def test_adnominal_noun_spacing():
    # 한잎: '한'(관형사) + '잎'(자립 명사) → 띄어 씀(제2항)
    r = inspect("한잎")
    assert r.found
    assert r.spacing_options == ["한 잎"]
    assert "제2항" in _clauses(r)
    roles = {(e.role, e.word) for e in r.entries}
    assert ("관형사", "한") in roles
    assert any(role == "명사" and word == "잎" for role, word in roles)


def test_adnominal_noun_more():
    for joined, spaced in [("새책", "새 책"), ("헌옷", "헌 옷")]:
        r = inspect(joined)
        assert r.spacing_options == [spaced], joined
        assert "제2항" in _clauses(r), joined


def test_demonstrative_determiner_spaces():
    # 지시관형사 '이/그/저' + 자립 명사(사전 미등재)는 띄움(이 사람)으로 판정한다.
    # '이'가 접요사 '-이-' 때문에 접두사 결합(이사람 붙임)으로 잘못 잡히던 회귀를 막는다.
    for joined, spaced in [("이사람", "이 사람"), ("저사람", "저 사람")]:
        r = inspect(joined)
        assert r.spacing_options == [spaced], joined
        assert "제2항" in _clauses(r), joined


def test_demonstrative_compound_protected_by_dictionary():
    # 굳어진 합성어·파생어('저혈압', '저비용')는 adnoun보다 먼저 사전 조회 단계에서 잡혀
    # 붙임이 보호된다 → '저 혈압'으로 잘못 띄우지 않는다.
    for q in ["저혈압", "저비용"]:
        r = inspect(q)
        assert r.found, q
        assert any("등재됨" in p for p in r.inspection_path), q  # 사전 조회로 처리됨
        assert f"{q[0]} {q[1:]}" not in r.spacing_options, q


def test_particle_chain_longest_root():
    # 하나도: '도'만 떼면 '하나'(등재어) → '하+나+도'로 과분해하지 않는다.
    r = inspect("하나도")
    assert r.spacing_options == ["하나도"]
    assert "제41항" in _clauses(r)
    words = {e.word for e in r.entries}
    assert "하나" in words and "도" in words
    assert "하" not in words and "나" not in words


def test_particle_not_dependent_noun():
    # 너도: '도'는 조사다(의존명사 아님) → 너 + 도, 제41항
    r = inspect("너도")
    assert r.spacing_options == ["너도"]
    assert "제41항" in _clauses(r)


def test_leaf_is_not_dependent_noun():
    # '잎'은 일반 명사이지 의존 명사가 아니므로 의존명사(제42항) 분해가 일어나면 안 된다.
    r = inspect("한잎")
    assert "제42항" not in _clauses(r)

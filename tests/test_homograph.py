"""동형이의 대비 카드(의존명사 vs 조사/어미) end-to-end (dict.db 필요)."""

from __future__ import annotations

from core import inspect


def _clauses(r):
    return {h.항번호 for h in r.rule_hints}


def test_particle_resolves_to_attach_when_prefix_nominal():
    # 법대로: '법'은 체언 전용 → 조사(제41) '붙임'으로 확정, 정답 하나만 제시
    r = inspect("법대로")
    assert r.found
    assert _clauses(r) == {"제41항"}
    assert r.spacing_options == ["법대로"]
    assert any("체언" in n and "붙여" in n for n in r.notes)


def test_particle_resolves_to_space_when_prefix_predicate():
    # 아는만큼: '아는'은 용언 활용형 전용 → 의존명사(제42) '띄움'으로 확정
    r = inspect("아는만큼")
    assert r.found
    assert _clauses(r) == {"제42항"}
    assert r.spacing_options == ["아는 만큼"]
    assert any("용언" in n and "띄어" in n for n in r.notes)


def test_particle_keeps_both_when_prefix_ambiguous():
    # 본대로: '본'은 체언이면서 용언 활용형(보다)도 가능 → 두 해석 모두 제시
    r = inspect("본대로")
    assert _clauses(r) == {"제42항", "제41항"}
    assert r.spacing_options == ["본 대로", "본대로"]


def test_ending_type_meaning_hint():
    # 데/지: 의존명사(제42) vs 어미(제2), 의미로 구별 안내
    r = inspect("아는데")
    assert _clauses(r) == {"제42항", "제2항"}
    assert any("의미로 구별" in n for n in r.notes)


def test_bound_noun_type():
    # 중: 의존명사(띄움) vs 굳은 합성어(붙임)
    r = inspect("회의중")
    assert _clauses(r) == {"제42항", "제2항"}
    assert "회의 중" in r.spacing_options


def test_homograph_does_not_steal_other_paths():
    # 보조용언/의존명사 결합형·단위는 동형이의 카드가 가로채면 안 됨
    assert any(h.항번호 == "제47항" for h in inspect("할만하다").rule_hints)
    assert any(h.항번호 == "제42항" for h in inspect("먹을것").rule_hints)
    assert any(h.항번호 == "제43항" for h in inspect("차한대").rule_hints)

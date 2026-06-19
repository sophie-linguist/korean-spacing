"""미등록 합성명사·전문용어·고유명사 인식(제50/49항) end-to-end (dict.db 필요)."""

from __future__ import annotations

from core import inspect


def test_specialized_compound_recognized():
    # 사전 미등재 전문용어 → 제50항, 붙임형은 항상 제시
    r = inspect("인공지능위원회")
    assert r.found
    assert any(h.항번호 == "제50항" for h in r.rule_hints)
    assert "인공지능위원회" in r.spacing_options  # 붙임형
    # 구성 예시: '인공^지능'은 사전상 띄어 쓰는 합성어이므로 '인공 지능'으로 펼친다.
    assert "인공 지능 위원회" in r.spacing_options


def test_caret_compound_piece_expands_to_spaced():
    # '나선^은하'처럼 조각이 사전상 띄어 쓰는 합성어면 그 표기로 펼친다.
    r = inspect("정상나선은하")
    assert r.found
    assert "정상 나선 은하" in r.spacing_options


def test_hyphen_piece_stays_joined():
    # '위원-회'의 '-'(접사 경계)는 띄우지 않는다 → '위원 회'로 갈라지면 안 됨.
    r = inspect("인공지능위원회")
    assert not any("위원 회" in opt for opt in r.spacing_options)


def test_org_suffix_triggers_without_clean_cover():
    # 기관 접미부('학회')로 인식하되, 깔끔한 분절이 없으면 붙임형만(분절 침묵)
    r = inspect("대한의학회")
    assert r.found
    assert any(h.항번호 == "제50항" for h in r.rule_hints)
    assert r.spacing_options == ["대한의학회"]


def test_program_suffix_recognized():
    # '과정' 등 전문/교육 접미부로 끝나는 미등록어도 제50항으로 인식
    r = inspect("인재양성과정")
    assert r.found
    assert any(h.항번호 == "제50항" for h in r.rule_hints)


def test_mixed_script_recognized_but_not_segmented():
    # 로마자 혼합('AI…')은 접미부로 인식하되 분절은 생략, 붙임형만 제시
    r = inspect("AI전문인재양성과정")
    assert r.found
    assert any(h.항번호 == "제50항" for h in r.rule_hints)
    assert r.spacing_options == ["AI전문인재양성과정"]


def test_nonsense_is_silent():
    # 무의미어는 모든 조각이 전문분야가 아니므로 침묵(오탐 방지)
    assert inspect("아무거나말").found is False


def test_registered_word_uses_normal_path():
    # 표제어로 등재된 말은 합성어 경로가 아니라 일반 경로
    r = inspect("큰집")
    assert r.found
    assert any(h.항번호 == "제2항" for h in r.rule_hints)

"""결합형 분리 + 머리 검증 게이트의 end-to-end 동작(dict.db 필요)."""

from __future__ import annotations

from core import inspect


def _seg(result):
    if result.segmentation and result.segmentation.candidates:
        c = result.segmentation.candidates[0]
        return c.left, c.right
    return None


def test_auxiliary_predicate_split():
    # 용언 활용형 + 보조용언 → 제47항(원칙 띄움/허용 붙임)
    r = inspect("할만하다")
    assert r.found
    assert _seg(r) == ("할", "만하다")
    assert any(h.항번호 == "제47항" for h in r.rule_hints)
    assert r.spacing_options == ["할 만하다", "할만하다"]


def test_main_verb_connective_split():
    # 본용언 연결형 + 보조용언(먹어 보다 / 읽고 싶다)
    assert _seg(inspect("먹어보다")) == ("먹어", "보다")
    assert _seg(inspect("읽고싶다")) == ("읽고", "싶다")


def test_dependent_noun_split():
    # 관형사형 + 의존명사 → 제42항
    r = inspect("할수")
    assert _seg(r) == ("할", "수")
    assert any(h.항번호 == "제42항" for h in r.rule_hints)
    assert _seg(inspect("할것")) == ("할", "것")
    assert _seg(inspect("먹을줄")) == ("먹을", "줄")


def test_noun_head_is_not_split_as_auxiliary():
    # 머리가 명사면 보조용언으로 오분할하지 않음('주먹 만하다' 방지)
    assert inspect("주먹만하다").found is False
    assert inspect("사람들").found is False


def test_noun_plus_particle_goes_to_homograph_not_aux():
    # '바람만'은 조사 '만'(붙임)으로 안내되어야지, 보조용언으로 분리되면 안 됨
    r = inspect("바람만")
    clauses = {h.항번호 for h in r.rule_hints}
    assert "제47항" not in clauses  # 보조용언 오분할 아님
    assert "제41항" in clauses      # 조사 해석 제시


def test_joined_counter_is_unit_rule_not_dependent_noun():
    # 붙은 '차한대'는 제43항(단위)으로, 동사/의존명사 경로가 '대'를 가로채면 안 됨
    for q, spaced in [("차한대", "차 한 대"), ("사과두개", "사과 두 개"), ("연필세자루", "연필 세 자루")]:
        r = inspect(q)
        assert any(h.항번호 == "제43항" for h in r.rule_hints), q
        assert spaced in r.spacing_options, q


def test_existing_paths_intact():
    # 기존 경로 회귀: 표제어/수량사+단위
    assert inspect("큰집").found is True
    assert _seg(inspect("차 한 대")) == ("한", "대")

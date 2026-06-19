"""InspectResult 직렬화 — 얇은 셸(webui·mcp 등)이 공유한다.

로직은 core에, 표현(JSON/텍스트 변환)은 여기 한곳에 모은다. UI 의존(조항 전문 펼치기
등)은 각 셸이 따로 덧붙인다 — 여기서는 InspectResult 필드만 다룬다.
"""

from __future__ import annotations

from core.schema import InspectResult


def result_to_dict(r: InspectResult) -> dict:
    """InspectResult(중첩 dataclass)를 ascii 키 dict로 변환한다."""
    return {
        "input": r.input,
        "found": r.found,
        "hint": r.hint,
        "spacing_options": list(r.spacing_options),
        "rule_hints": [
            {"clause": h.항번호, "policy": h.원칙허용, "gist": h.요지}
            for h in r.rule_hints
        ],
        "entries": [
            {
                "word": e.word,
                "pos": e.pos,
                "definition": e.definition,
                "type": e.type,
                "badge": e.spacing_badge,
                "role": e.role,
            }
            for e in r.entries
        ],
        "segmentation": (
            None
            if not r.segmentation
            else {
                "message": r.segmentation.message,
                "candidates": [
                    {"original": c.original, "left": c.left, "right": c.right, "hint": c.hint}
                    for c in r.segmentation.candidates
                ],
            }
        ),
        "notes": list(r.notes),
        "inspection_path": list(r.inspection_path),
    }


def result_to_text(r: InspectResult) -> str:
    """InspectResult를 사람·LLM이 바로 읽을 수 있는 한국어 요약 텍스트로 만든다."""
    lines: list[str] = [f"입력: {r.input}"]

    if r.found:
        if r.spacing_options:
            opts = [
                f"{o} ({'띄어 씀' if ' ' in o.strip() else '붙여 씀'})"
                for o in r.spacing_options
            ]
            lines.append("표기: " + " / ".join(opts))

        if r.rule_hints:
            lines.append("적용 규정:")
            for h in r.rule_hints:
                lines.append(f"  - {h.항번호} [{h.원칙허용}] {h.요지}")

        if r.entries:
            lines.append("사전 정보:")
            for e in r.entries:
                role = f"{e.role} · " if e.role else ""
                badge = f" [{e.spacing_badge}]" if e.spacing_badge else ""
                lines.append(f"  - {role}{e.word} ({e.pos}){badge}")

        if r.segmentation and r.segmentation.candidates:
            for c in r.segmentation.candidates:
                tail = f" — {c.hint}" if c.hint else ""
                lines.append(f"분리: {c.original} → {c.left} + {c.right}{tail}")

        for n in r.notes:
            lines.append(f"참고: {n}")
    else:
        lines.append("판정: 확신할 근거를 찾지 못했습니다(섣불리 단정하지 않음).")
        if r.hint:
            lines.append(f"안내: {r.hint}")

    if r.inspection_path:
        lines.append("탐색 경로:")
        for i, step in enumerate(r.inspection_path, 1):
            lines.append(f"  {i}. {step}")

    return "\n".join(lines)

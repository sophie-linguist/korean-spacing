from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DisplayMode = Literal["normal", "pos_compressed"]


@dataclass(slots=True)
class RuleHint:
    항번호: str
    원칙허용: str
    요지: str


@dataclass(slots=True)
class Entry:
    word: str
    pos: str
    definition: str
    type: str
    cat: str | None = None
    group_code: int | None = None
    spacing_badge: str | None = None
    target_code: int | None = None


@dataclass(slots=True)
class SegmentCandidate:
    original: str
    left: str
    right: str
    hint: str | None = None


@dataclass(slots=True)
class SegmentInfo:
    message: str
    candidates: list[SegmentCandidate] = field(default_factory=list)


@dataclass(slots=True)
class InspectResult:
    input: str
    found: bool
    display_mode: DisplayMode = "normal"
    entries: list[Entry] = field(default_factory=list)
    rule_hints: list[RuleHint] = field(default_factory=list)
    spacing_options: list[str] = field(default_factory=list)
    segmentation: SegmentInfo | None = None
    notes: list[str] = field(default_factory=list)
    hint: str | None = None

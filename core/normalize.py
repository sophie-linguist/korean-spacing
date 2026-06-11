from __future__ import annotations

import unicodedata


def normalize_query(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\u3000", " ")
    normalized = " ".join(normalized.strip().split())
    return normalized


def make_lookup_forms(text: str) -> tuple[str, str]:
    normalized = normalize_query(text)
    joined = normalized.replace(" ", "")
    return joined, normalized

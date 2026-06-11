from __future__ import annotations

import sqlite3
import os
import sys
import unicodedata
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_DB_CONN_CACHE: dict[Path, sqlite3.Connection] = {}


def _normalize_space(text: str) -> str:
    return " ".join(text.strip().split())


def _normalize_nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def normalize_lookup_forms(text: str) -> tuple[str, str]:
    normalized = _normalize_nfc(_normalize_space(text))
    joined = normalized.replace(" ", "")
    return joined, normalized


def resolve_db_path(db_path: str | Path | None = None) -> Path:
    if db_path is not None:
        p = Path(db_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"Database not found: {p}")

    env_db_path = os.getenv("KOREAN_SPACING_DB_PATH")
    if env_db_path:
        env_path = Path(env_db_path)
        if env_path.exists():
            return env_path
        raise FileNotFoundError(f"Database not found (KOREAN_SPACING_DB_PATH): {env_path}")

    candidates = [
        Path.cwd() / "dict.db",
        Path(sys.executable).parent / "dict.db",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("dict.db not found. Place dict.db next to exe or current working directory.")


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    resolved = resolve_db_path(db_path)
    if resolved not in _DB_CONN_CACHE:
        # check_same_thread=False: GUI(pywebview)는 JS 호출을 별도 스레드에서 처리하므로
        # 캐시된 연결을 스레드 간 재사용할 수 있어야 한다. 조회는 읽기 전용이고
        # 사용자 동작당 직렬로 일어나므로 안전하다.
        con = sqlite3.connect(str(resolved), check_same_thread=False)
        con.row_factory = sqlite3.Row
        _DB_CONN_CACHE[resolved] = con
    return _DB_CONN_CACHE[resolved]


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "target_code": row["target_code"],
        "word_raw": row["word_raw"],
        "word_joined": row["word_joined"],
        "word_spaced": row["word_spaced"],
        "word_unit": row["word_unit"],
        "pos": row["pos"],
        "definition": row["definition"],
        "type": row["type"],
        "cat": row["cat"],
        "group_code": row["group_code"],
        "group_order": row["group_order"],
        "has_caret": row["has_caret"],
        "caret_count": row["caret_count"],
    }


def lookup(key: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    joined, spaced = normalize_lookup_forms(key)
    con = get_connection(db_path)
    rows = con.execute(
        """
        SELECT *
        FROM entries
        WHERE word_joined = ? OR word_spaced = ?
        ORDER BY COALESCE(group_code, 2147483647), COALESCE(group_order, 2147483647), target_code
        """,
        (joined, spaced),
    ).fetchall()
    return [row_to_dict(row) for row in rows]


def exists_with_pos(word_joined: str, pos_like: str, db_path: str | Path | None = None) -> bool:
    """Return True if a dictionary entry matches word_joined and its pos LIKE pos_like.

    Used by conjugation head-validation to confirm a restored stem (e.g. "하다")
    is actually registered as a verb/adjective, without loading full rows.
    """
    joined = _normalize_nfc(word_joined).replace(" ", "")
    con = get_connection(db_path)
    row = con.execute(
        "SELECT 1 FROM entries WHERE word_joined = ? AND pos LIKE ? LIMIT 1",
        (joined, pos_like),
    ).fetchone()
    return row is not None


def group_by_group_code(entries: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    no_group: list[list[dict[str, Any]]] = []

    for entry in entries:
        group_code = entry.get("group_code")
        if isinstance(group_code, int):
            grouped.setdefault(group_code, []).append(entry)
        else:
            no_group.append([entry])

    result = [grouped[k] for k in sorted(grouped.keys())]
    result.extend(no_group)
    return result


def find_caret_joined(text: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    joined, _ = normalize_lookup_forms(text)
    con = get_connection(db_path)
    rows = con.execute(
        """
        SELECT *
        FROM entries
        WHERE has_caret = 1 AND word_joined = ?
        ORDER BY COALESCE(group_code, 2147483647), COALESCE(group_order, 2147483647), target_code
        """,
        (joined,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]

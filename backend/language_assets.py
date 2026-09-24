"""Local direction terminology, provider-result records, and usage storage."""

from __future__ import annotations

import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


DATABASE_PATH = Path.home() / ".cad_translator_language_assets.sqlite3"
AZURE_F0_MONTHLY_CHARACTER_LIMIT = 2_000_000
ACRONYM_RE = re.compile(r"[A-Za-z]+(?:[._-][A-Za-z]+)*[._-]?")


def _normalise(text: str) -> str:
    value = " ".join((text or "").strip().casefold().split())
    if ACRONYM_RE.fullmatch(value):
        parts = re.findall(r"[a-z]+", value)
        if len(parts) > 1 and all(len(part) == 1 for part in parts):
            return "".join(parts)
    return value


class LanguageAssets:
    """Small SQLite-backed assets, one terminology library per direction."""

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = Path(database_path or DATABASE_PATH)
        self._lock = threading.Lock()
        self._initialise()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _initialise(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS terms (
                    id INTEGER PRIMARY KEY,
                    mode TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_norm TEXT NOT NULL,
                    target TEXT NOT NULL,
                    layer_contains TEXT NOT NULL DEFAULT '',
                    profession TEXT NOT NULL DEFAULT 'general',
                    updated_at TEXT NOT NULL,
                    UNIQUE(mode, source_norm, profession)
                );
                CREATE TABLE IF NOT EXISTS translation_records (
                    id INTEGER PRIMARY KEY,
                    mode TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_norm TEXT NOT NULL,
                    target TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    profession TEXT NOT NULL DEFAULT 'general',
                    manual INTEGER NOT NULL DEFAULT 0,
                    hit_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(mode, source_norm, profession)
                );
                CREATE TABLE IF NOT EXISTS record_drawings (
                    record_id INTEGER NOT NULL,
                    drawing_name TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    PRIMARY KEY(record_id, drawing_name),
                    FOREIGN KEY(record_id) REFERENCES translation_records(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS usage_monthly (
                    month TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    characters INTEGER NOT NULL DEFAULT 0,
                    requests INTEGER NOT NULL DEFAULT 0,
                    quota_exceeded INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(month, provider)
                );
                """
            )
            if "profession" not in {row[1] for row in connection.execute("PRAGMA table_info(terms)")}:
                connection.executescript("""
                ALTER TABLE terms RENAME TO terms_v190;
                CREATE TABLE terms (id INTEGER PRIMARY KEY, mode TEXT NOT NULL, source TEXT NOT NULL, source_norm TEXT NOT NULL, target TEXT NOT NULL, layer_contains TEXT NOT NULL DEFAULT '', profession TEXT NOT NULL DEFAULT 'general', updated_at TEXT NOT NULL, UNIQUE(mode, source_norm, profession));
                INSERT INTO terms(id, mode, source, source_norm, target, layer_contains, profession, updated_at) SELECT id, mode, source, source_norm, target, layer_contains, 'general', updated_at FROM terms_v190;
                DROP TABLE terms_v190;
                """)
            if "profession" not in {row[1] for row in connection.execute("PRAGMA table_info(translation_records)")}:
                connection.executescript("""
                ALTER TABLE translation_records RENAME TO translation_records_v190;
                CREATE TABLE translation_records (id INTEGER PRIMARY KEY, mode TEXT NOT NULL, source TEXT NOT NULL, source_norm TEXT NOT NULL, target TEXT NOT NULL, provider TEXT NOT NULL, profession TEXT NOT NULL DEFAULT 'general', manual INTEGER NOT NULL DEFAULT 0, hit_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(mode, source_norm, profession));
                INSERT INTO translation_records(id, mode, source, source_norm, target, provider, profession, manual, hit_count, created_at, updated_at) SELECT id, mode, source, source_norm, target, provider, 'general', manual, hit_count, created_at, updated_at FROM translation_records_v190;
                DROP TABLE translation_records_v190;
                """)
            legacy_table = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='translation_memory'").fetchone()
            legacy_terms = connection.execute("SELECT mode, source, target, updated_at FROM terms WHERE layer_contains<>''").fetchall()
            for row in legacy_terms:
                connection.execute(
                    "INSERT OR IGNORE INTO terms(mode, source, source_norm, target, layer_contains, updated_at) VALUES(?,?,?,?,?,?)",
                    (row["mode"], row["source"], _normalise(row["source"]), row["target"], "", row["updated_at"]),
                )
            connection.execute("DELETE FROM terms WHERE layer_contains<>''")
            if legacy_table and connection.execute("SELECT COUNT(*) FROM translation_records").fetchone()[0] == 0:
                legacy = connection.execute(
                    "SELECT mode, source, target, provider, origin, hit_count, created_at, updated_at FROM translation_memory "
                    "ORDER BY CASE origin WHEN 'manual' THEN 0 ELSE 1 END, updated_at DESC"
                ).fetchall()
                for row in legacy:
                    connection.execute(
                        "INSERT OR IGNORE INTO translation_records(mode, source, source_norm, target, provider, manual, hit_count, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                        (row["mode"], row["source"], _normalise(row["source"]), row["target"], row["provider"], int(row["origin"] == "manual"), row["hit_count"], row["created_at"], row["updated_at"]),
                    )

    def cache_revision(self) -> int:
        return self.database_path.stat().st_mtime_ns

    def list_terms(self, mode: str = "", search: str = "", profession: str = "general") -> list[dict]:
        sql = "SELECT id, mode, source, target, updated_at FROM terms WHERE layer_contains=''"
        params: list[str] = []
        if mode:
            sql += " AND mode=?"
            params.append(mode)
        sql += " AND profession=?"
        params.append(profession)
        if search.strip():
            sql += " AND (source LIKE ? OR target LIKE ?)"
            params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])
        sql += " ORDER BY mode, source COLLATE NOCASE"
        with self._connect() as connection:
            return [dict(row) for row in connection.execute(sql, params)]

    def upsert_term(self, mode: str, source: str, target: str, term_id: int | None = None, profession: str = "general") -> None:
        if not mode or not source.strip() or not target.strip():
            raise ValueError("术语、译文和翻译方向不能为空")
        with self._lock, self._connect() as connection:
            if term_id is not None:
                connection.execute("DELETE FROM terms WHERE id=?", (term_id,))
            connection.execute(
                "INSERT INTO terms(mode, source, source_norm, target, layer_contains, profession, updated_at) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(mode, source_norm, profession) DO UPDATE SET source=excluded.source, target=excluded.target, updated_at=excluded.updated_at",
                (mode, source.strip(), _normalise(source), target.strip(), "", profession, self._now()),
            )

    def delete_term(self, term_id: int) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM terms WHERE id=?", (term_id,))

    def lookup_term(self, source: str, mode: str, profession: str = "general") -> str | None:
        with self._connect() as connection:
            row = connection.execute("SELECT target FROM terms WHERE mode=? AND source_norm=? AND profession IN (?, 'general') ORDER BY profession=? DESC LIMIT 1", (mode, _normalise(source), profession, profession)).fetchone()
        return str(row["target"]) if row else None

    def _note_drawing(self, connection, record_id: int, drawing_name: str) -> None:
        if drawing_name:
            connection.execute(
                "INSERT INTO record_drawings(record_id, drawing_name, last_seen_at) VALUES(?,?,?) "
                "ON CONFLICT(record_id, drawing_name) DO UPDATE SET last_seen_at=excluded.last_seen_at",
                (record_id, Path(drawing_name).name, self._now()),
            )

    def lookup_record(self, source: str, mode: str, drawing_name: str = "", profession: str = "general") -> str | None:
        with self._lock, self._connect() as connection:
            row = connection.execute("SELECT id, target FROM translation_records WHERE mode=? AND source_norm=? AND profession IN (?, 'general') ORDER BY profession=? DESC LIMIT 1", (mode, _normalise(source), profession, profession)).fetchone()
            if not row:
                return None
            connection.execute("UPDATE translation_records SET hit_count=hit_count+1 WHERE id=?", (row["id"],))
            self._note_drawing(connection, row["id"], drawing_name)
            return str(row["target"])

    def record_provider_result(self, source: str, target: str, mode: str, provider: str, drawing_name: str = "", profession: str = "general") -> None:
        if not source.strip() or not target.strip():
            return
        now = self._now()
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO translation_records(mode, source, source_norm, target, provider, profession, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(mode, source_norm, profession) DO UPDATE SET source=excluded.source, target=excluded.target, provider=excluded.provider, updated_at=excluded.updated_at WHERE translation_records.manual=0",
                (mode, source.strip(), _normalise(source), target.strip(), provider, profession, now, now),
            )
            row = connection.execute("SELECT id FROM translation_records WHERE mode=? AND source_norm=? AND profession=?", (mode, _normalise(source), profession)).fetchone()
            self._note_drawing(connection, row["id"], drawing_name)

    def update_record(self, record_id: int, source: str, target: str) -> None:
        if not source.strip() or not target.strip():
            raise ValueError("记录原文和译文不能为空")
        with self._lock, self._connect() as connection:
            existing = connection.execute("SELECT id FROM translation_records WHERE id=?", (record_id,)).fetchone()
            if not existing:
                raise ValueError("翻译记录不存在")
            connection.execute(
                "UPDATE translation_records SET source=?, source_norm=?, target=?, manual=1, updated_at=? WHERE id=?",
                (source.strip(), _normalise(source), target.strip(), self._now(), record_id),
            )

    def delete_record(self, record_id: int) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("DELETE FROM record_drawings WHERE record_id=?", (record_id,))
            connection.execute("DELETE FROM translation_records WHERE id=?", (record_id,))

    def list_records(self, mode: str, search: str = "", provider: str = "", manual: str = "", drawing: str = "", page: int = 1, page_size: int = 50, profession: str = "general") -> dict:
        conditions, params = ["r.mode=?"], [mode]
        conditions.append("r.profession=?")
        params.append(profession)
        if search.strip():
            conditions.append("(r.source LIKE ? OR r.target LIKE ?)")
            params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])
        if provider in {"deepl", "azure"}:
            conditions.append("r.provider=?")
            params.append(provider)
        if manual in {"true", "false"}:
            conditions.append("r.manual=?")
            params.append(int(manual == "true"))
        if drawing:
            conditions.append("EXISTS(SELECT 1 FROM record_drawings d WHERE d.record_id=r.id AND d.drawing_name=?)")
            params.append(drawing)
        where = " WHERE " + " AND ".join(conditions)
        page = max(1, page)
        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM translation_records r" + where, params).fetchone()[0]
            rows = connection.execute(
                "SELECT r.*, COALESCE((SELECT GROUP_CONCAT(d.drawing_name, '、') FROM record_drawings d WHERE d.record_id=r.id), '') AS drawings "
                "FROM translation_records r" + where + " ORDER BY r.updated_at DESC LIMIT ? OFFSET ?",
                [*params, page_size, (page - 1) * page_size],
            ).fetchall()
            drawings = connection.execute("SELECT drawing_name FROM record_drawings GROUP BY drawing_name ORDER BY MAX(last_seen_at) DESC LIMIT 10").fetchall()
        return {"items": [dict(row) for row in rows], "page": page, "page_size": page_size, "total": total, "drawings": [row["drawing_name"] for row in drawings]}

    def promote_record(self, record_id: int) -> None:
        with self._connect() as connection:
            row = connection.execute("SELECT mode, source, target, profession FROM translation_records WHERE id=?", (record_id,)).fetchone()
        if not row:
            raise ValueError("翻译记录不存在")
        self.upsert_term(row["mode"], row["source"], row["target"], profession=row["profession"])

    def record_usage(self, provider: str, characters: int, quota_exceeded: bool = False) -> None:
        if provider not in {"deepl", "azure"}:
            return
        month = datetime.now().strftime("%Y-%m")
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO usage_monthly(month, provider, characters, requests, quota_exceeded) VALUES(?,?,?,?,?) "
                "ON CONFLICT(month, provider) DO UPDATE SET characters=characters+excluded.characters, requests=requests+excluded.requests, quota_exceeded=MAX(quota_exceeded, excluded.quota_exceeded)",
                (month, provider, max(0, characters), 1, int(quota_exceeded)),
            )

    def usage(self) -> dict:
        month = datetime.now().strftime("%Y-%m")
        with self._connect() as connection:
            rows = {row["provider"]: dict(row) for row in connection.execute("SELECT provider, characters, requests, quota_exceeded FROM usage_monthly WHERE month=?", (month,))}
        azure = rows.get("azure", {"characters": 0, "requests": 0, "quota_exceeded": 0})
        deepl = rows.get("deepl", {"characters": 0, "requests": 0, "quota_exceeded": 0})
        return {"month": month, "deepl": deepl, "azure": {**azure, "limit": AZURE_F0_MONTHLY_CHARACTER_LIMIT, "remaining": max(0, AZURE_F0_MONTHLY_CHARACTER_LIMIT - azure["characters"])}}

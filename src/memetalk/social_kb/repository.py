from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from memetalk.social_kb.models import ContentAnalysis, ContentItem, MonetizationScore


class SocialContentRepository:
    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = sqlite_path

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS social_content (
                    item_id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    raw_content TEXT NOT NULL DEFAULT '',
                    source_platform TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '其他',
                    tags TEXT NOT NULL DEFAULT '[]',
                    summary TEXT NOT NULL DEFAULT '',
                    key_points TEXT NOT NULL DEFAULT '[]',
                    trend_relevance TEXT NOT NULL DEFAULT '',
                    social_score REAL NOT NULL DEFAULT 0,
                    knowledge_score REAL NOT NULL DEFAULT 0,
                    affiliate_score REAL NOT NULL DEFAULT 0,
                    consulting_score REAL NOT NULL DEFAULT 0,
                    overall_score REAL NOT NULL DEFAULT 0,
                    channels TEXT NOT NULL DEFAULT '[]',
                    content_angles TEXT NOT NULL DEFAULT '[]',
                    monetization_reasoning TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sc_score ON social_content(overall_score DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sc_category ON social_content(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sc_created ON social_content(created_at DESC)"
            )

    def save_item(self, item: ContentItem) -> None:
        m = item.analysis.monetization
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO social_content (
                    item_id, url, title, raw_content, source_platform,
                    category, tags, summary, key_points, trend_relevance,
                    social_score, knowledge_score, affiliate_score, consulting_score, overall_score,
                    channels, content_angles, monetization_reasoning,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    url=excluded.url, title=excluded.title,
                    raw_content=excluded.raw_content, source_platform=excluded.source_platform,
                    category=excluded.category, tags=excluded.tags,
                    summary=excluded.summary, key_points=excluded.key_points,
                    trend_relevance=excluded.trend_relevance,
                    social_score=excluded.social_score, knowledge_score=excluded.knowledge_score,
                    affiliate_score=excluded.affiliate_score, consulting_score=excluded.consulting_score,
                    overall_score=excluded.overall_score,
                    channels=excluded.channels, content_angles=excluded.content_angles,
                    monetization_reasoning=excluded.monetization_reasoning,
                    updated_at=excluded.updated_at
                """,
                (
                    item.item_id, item.url, item.title,
                    item.raw_content[:10000],
                    item.source_platform,
                    item.analysis.category,
                    json.dumps(item.analysis.tags, ensure_ascii=False),
                    item.analysis.summary,
                    json.dumps(item.analysis.key_points, ensure_ascii=False),
                    item.analysis.trend_relevance,
                    m.social_score, m.knowledge_score, m.affiliate_score,
                    m.consulting_score, m.overall_score,
                    json.dumps(m.channels, ensure_ascii=False),
                    json.dumps(m.content_angles, ensure_ascii=False),
                    m.reasoning,
                    item.created_at.isoformat(),
                    item.updated_at.isoformat(),
                ),
            )

    def get_item(self, item_id: str) -> ContentItem | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM social_content WHERE item_id = ?", (item_id,)
            ).fetchone()
        return self._row_to_item(row) if row else None

    def get_item_by_url(self, url: str) -> ContentItem | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM social_content WHERE url = ?", (url,)
            ).fetchone()
        return self._row_to_item(row) if row else None

    def list_items(
        self,
        categories: list[str] | None = None,
        min_score: float = 0.0,
        search_query: str = "",
        sort_by: str = "created_at",
        limit: int = 100,
    ) -> list[ContentItem]:
        conditions = ["overall_score >= ?"]
        params: list = [min_score]

        if categories:
            placeholders = ", ".join("?" * len(categories))
            conditions.append(f"category IN ({placeholders})")
            params.extend(categories)

        if search_query:
            conditions.append("(title LIKE ? OR summary LIKE ? OR tags LIKE ?)")
            like = f"%{search_query}%"
            params.extend([like, like, like])

        where = " AND ".join(conditions)
        order = "overall_score DESC" if sort_by == "score" else "created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM social_content WHERE {where} ORDER BY {order} LIMIT ?",
                (*params, limit),
            ).fetchall()

        return [self._row_to_item(row) for row in rows]

    def count_items(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM social_content").fetchone()
            return row[0] if row else 0

    def get_category_stats(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT category, COUNT(*) as cnt FROM social_content "
                "GROUP BY category ORDER BY cnt DESC"
            ).fetchall()
        return {row[0]: row[1] for row in rows}

    def delete_item(self, item_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM social_content WHERE item_id = ?", (item_id,))

    def _connect(self) -> sqlite3.Connection:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_item(self, row: sqlite3.Row) -> ContentItem:
        mon = MonetizationScore(
            social_score=row["social_score"],
            knowledge_score=row["knowledge_score"],
            affiliate_score=row["affiliate_score"],
            consulting_score=row["consulting_score"],
            overall_score=row["overall_score"],
            channels=json.loads(row["channels"] or "[]"),
            content_angles=json.loads(row["content_angles"] or "[]"),
            reasoning=row["monetization_reasoning"] or "",
        )
        analysis = ContentAnalysis(
            category=row["category"] or "其他",
            tags=json.loads(row["tags"] or "[]"),
            summary=row["summary"] or "",
            key_points=json.loads(row["key_points"] or "[]"),
            trend_relevance=row["trend_relevance"] or "",
            monetization=mon,
        )
        return ContentItem(
            item_id=row["item_id"],
            url=row["url"],
            title=row["title"] or "",
            raw_content=row["raw_content"] or "",
            source_platform=row["source_platform"] or "",
            analysis=analysis,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

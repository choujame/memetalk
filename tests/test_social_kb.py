from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from memetalk.config import AppSettings
from memetalk.social_kb.analyzer import SocialContentAnalyzer
from memetalk.social_kb.extractor import ContentExtractor
from memetalk.social_kb.generator import ArticleGenerator
from memetalk.social_kb.models import ALL_CATEGORIES, ContentAnalysis, ContentItem, MonetizationScore
from memetalk.social_kb.repository import SocialContentRepository
from memetalk.social_kb.track_analyzer import TrackAnalyzer, TrackStats


# ── Model tests ───────────────────────────────────────────────────────────────

def test_content_item_has_uuid_by_default() -> None:
    item = ContentItem(url="https://example.com")
    assert len(item.item_id) == 32


def test_monetization_score_defaults_to_zero() -> None:
    m = MonetizationScore()
    assert m.overall_score == 0.0
    assert m.channels == []


def test_all_categories_is_non_empty_tuple() -> None:
    assert len(ALL_CATEGORIES) > 0
    assert "科技/AI" in ALL_CATEGORIES
    assert "其他" in ALL_CATEGORIES


# ── Repository tests ──────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_repo(tmp_path: Path) -> SocialContentRepository:
    repo = SocialContentRepository(tmp_path / "test.sqlite3")
    repo.initialize()
    return repo


def _make_item(url: str = "https://example.com", score: float = 5.0) -> ContentItem:
    return ContentItem(
        url=url,
        title="測試文章",
        raw_content="內容",
        source_platform="其他",
        analysis=ContentAnalysis(
            category="科技/AI",
            tags=["AI", "測試"],
            summary="這是一篇測試摘要",
            key_points=["重點一", "重點二"],
            trend_relevance="趨勢說明",
            monetization=MonetizationScore(
                social_score=score,
                knowledge_score=score,
                affiliate_score=score,
                consulting_score=score,
                overall_score=score,
                channels=["社群業配"],
                content_angles=["切入角度"],
                reasoning="測試原因",
            ),
        ),
    )


def test_repository_save_and_retrieve(tmp_repo: SocialContentRepository) -> None:
    item = _make_item()
    tmp_repo.save_item(item)
    fetched = tmp_repo.get_item_by_url("https://example.com")
    assert fetched is not None
    assert fetched.title == "測試文章"
    assert fetched.analysis.category == "科技/AI"
    assert fetched.analysis.tags == ["AI", "測試"]
    assert fetched.analysis.monetization.overall_score == 5.0
    assert fetched.analysis.monetization.channels == ["社群業配"]


def test_repository_count(tmp_repo: SocialContentRepository) -> None:
    assert tmp_repo.count_items() == 0
    tmp_repo.save_item(_make_item("https://a.com"))
    tmp_repo.save_item(_make_item("https://b.com"))
    assert tmp_repo.count_items() == 2


def test_repository_get_item_by_id(tmp_repo: SocialContentRepository) -> None:
    item = _make_item()
    tmp_repo.save_item(item)
    fetched = tmp_repo.get_item(item.item_id)
    assert fetched is not None
    assert fetched.item_id == item.item_id


def test_repository_delete(tmp_repo: SocialContentRepository) -> None:
    item = _make_item()
    tmp_repo.save_item(item)
    assert tmp_repo.count_items() == 1
    tmp_repo.delete_item(item.item_id)
    assert tmp_repo.count_items() == 0


def test_repository_upsert_on_conflict(tmp_repo: SocialContentRepository) -> None:
    item = _make_item()
    tmp_repo.save_item(item)
    item.title = "更新後標題"
    tmp_repo.save_item(item)
    assert tmp_repo.count_items() == 1
    fetched = tmp_repo.get_item(item.item_id)
    assert fetched is not None
    assert fetched.title == "更新後標題"


def test_repository_list_items_by_category(tmp_repo: SocialContentRepository) -> None:
    tmp_repo.save_item(_make_item("https://a.com"))  # 科技/AI
    item2 = _make_item("https://b.com")
    item2.analysis.category = "商業/創業"
    tmp_repo.save_item(item2)
    results = tmp_repo.list_items(categories=["商業/創業"])
    assert len(results) == 1
    assert results[0].url == "https://b.com"


def test_repository_list_items_min_score(tmp_repo: SocialContentRepository) -> None:
    tmp_repo.save_item(_make_item("https://low.com", score=3.0))
    tmp_repo.save_item(_make_item("https://high.com", score=8.0))
    results = tmp_repo.list_items(min_score=7.0)
    assert len(results) == 1
    assert results[0].url == "https://high.com"


def test_repository_list_items_search_query(tmp_repo: SocialContentRepository) -> None:
    item = _make_item()
    tmp_repo.save_item(item)
    matches = tmp_repo.list_items(search_query="測試摘要")
    assert len(matches) == 1
    no_match = tmp_repo.list_items(search_query="不存在的關鍵字xyz")
    assert len(no_match) == 0


def test_repository_category_stats(tmp_repo: SocialContentRepository) -> None:
    tmp_repo.save_item(_make_item("https://a.com"))
    tmp_repo.save_item(_make_item("https://b.com"))
    item3 = _make_item("https://c.com")
    item3.analysis.category = "商業/創業"
    tmp_repo.save_item(item3)
    stats = tmp_repo.get_category_stats()
    assert stats["科技/AI"] == 2
    assert stats["商業/創業"] == 1


def test_repository_get_track_stats(tmp_repo: SocialContentRepository) -> None:
    for i in range(3):
        item = _make_item(f"https://tech{i}.com", score=8.0)
        tmp_repo.save_item(item)
    low = _make_item("https://low.com", score=3.0)
    low.analysis.category = "娛樂/文化"
    tmp_repo.save_item(low)

    tracks = tmp_repo.get_track_stats(min_high_score=7.0)
    assert len(tracks) >= 1
    tech_track = next((t for t in tracks if t.category == "科技/AI"), None)
    assert tech_track is not None
    assert tech_track.high_score_count == 3
    assert tech_track.total_count == 3


# ── Extractor tests ───────────────────────────────────────────────────────────

def test_extractor_detect_platform() -> None:
    ext = ContentExtractor()
    assert ext.detect_platform("https://www.facebook.com/post/123") == "Facebook"
    assert ext.detect_platform("https://www.instagram.com/p/abc") == "Instagram"
    assert ext.detect_platform("https://x.com/user/status/123") == "X/Twitter"
    assert ext.detect_platform("https://twitter.com/user") == "X/Twitter"
    assert ext.detect_platform("https://www.youtube.com/watch?v=abc") == "YouTube"
    assert ext.detect_platform("https://youtu.be/abc") == "YouTube"
    assert ext.detect_platform("https://medium.com/@user/article") == "Medium"
    assert ext.detect_platform("https://example.com/article") == "其他"


def test_extractor_parse_html() -> None:
    ext = ContentExtractor()
    html = """
    <html>
    <head><title>測試標題</title></head>
    <body>
      <nav>這是導航列不該出現</nav>
      <main>
        <h1>文章主標題</h1>
        <p>這是文章內容的第一段。</p>
        <p>這是第二段。</p>
      </main>
      <script>var x = 1;</script>
      <footer>頁腳不應出現</footer>
    </body>
    </html>
    """
    title, body = ext.extract_from_html(html)
    assert title == "測試標題"
    assert "文章主標題" in body
    assert "這是文章內容" in body
    assert "導航列" not in body
    assert "頁腳" not in body
    assert "var x = 1" not in body


def test_extractor_max_content_length() -> None:
    ext = ContentExtractor()
    long_html = f"<html><body><p>{'x' * 20000}</p></body></html>"
    _, body = ext.extract_from_html(long_html)
    assert len(body) <= ContentExtractor.MAX_CONTENT_LEN


# ── Analyzer mock path tests ──────────────────────────────────────────────────

def test_analyzer_mock_backend_returns_stub() -> None:
    settings = AppSettings(provider_backend="mock")
    analyzer = SocialContentAnalyzer(settings)
    result = asyncio.run(analyzer.analyze("https://example.com", "測試", "內容"))
    assert result.category == "其他"
    assert "待分析" in result.tags


def test_analyzer_parse_valid_json() -> None:
    settings = AppSettings(provider_backend="mock")
    analyzer = SocialContentAnalyzer(settings)
    raw = json.dumps({
        "category": "科技/AI",
        "tags": ["AI", "機器學習"],
        "summary": "這是摘要",
        "key_points": ["重點一"],
        "trend_relevance": "趨勢說明",
        "monetization": {
            "social_score": 7.5,
            "knowledge_score": 8.0,
            "affiliate_score": 4.0,
            "consulting_score": 6.0,
            "overall_score": 7.0,
            "channels": ["社群業配"],
            "content_angles": ["AI 實戰應用"],
            "reasoning": "AI 領域熱門",
        },
    }, ensure_ascii=False)
    result = analyzer._parse(raw)
    assert result is not None
    assert result.category == "科技/AI"
    assert result.tags == ["AI", "機器學習"]
    assert result.monetization.social_score == 7.5
    assert result.monetization.channels == ["社群業配"]


def test_analyzer_parse_json_in_code_fence() -> None:
    settings = AppSettings(provider_backend="mock")
    analyzer = SocialContentAnalyzer(settings)
    raw = '```json\n{"category": "其他", "tags": [], "summary": "x", "key_points": [], "trend_relevance": "", "monetization": {"social_score": 0, "knowledge_score": 0, "affiliate_score": 0, "consulting_score": 0, "overall_score": 0, "channels": [], "content_angles": [], "reasoning": ""}}\n```'
    result = analyzer._parse(raw)
    assert result is not None
    assert result.category == "其他"


def test_analyzer_parse_invalid_json_returns_none() -> None:
    settings = AppSettings(provider_backend="mock")
    analyzer = SocialContentAnalyzer(settings)
    result = analyzer._parse("這不是 JSON")
    assert result is None


# ── Generator mock path tests ─────────────────────────────────────────────────

def test_generator_mock_backend() -> None:
    settings = AppSettings(provider_backend="mock")
    gen = ArticleGenerator(settings)
    item = _make_item()
    result = asyncio.run(gen.generate([item, item], "部落格/Medium"))
    assert "Mock" in result.title
    assert result.intro != ""


def test_generator_word_count() -> None:
    from memetalk.social_kb.generator import GeneratedArticle
    article = GeneratedArticle(
        title="標題",
        intro="引言文字" * 10,
        sections=[{"heading": "段落", "content": "內容文字" * 20}],
        conclusion="結語",
    )
    assert article.word_count() > 0


def test_generator_to_markdown_includes_title() -> None:
    from memetalk.social_kb.generator import GeneratedArticle
    article = GeneratedArticle(
        title="測試標題",
        subtitle="副標題",
        intro="引言",
        sections=[{"heading": "段落標題", "content": "段落內容"}],
        conclusion="結語",
        hashtags=["#AI", "#測試"],
    )
    md = article.to_markdown()
    assert "# 測試標題" in md
    assert "## 段落標題" in md
    assert "#AI" in md


# ── TrackStats tests ──────────────────────────────────────────────────────────

def test_track_stats_readiness_levels() -> None:
    def icon(high: int) -> str:
        return TrackStats(category="科技/AI", high_score_count=high).readiness[0]

    assert icon(0) == "📌"
    assert icon(1) == "📌"
    assert icon(3) == "🌱"
    assert icon(5) == "🌿"
    assert icon(10) == "🌳"


def test_track_stats_best_dimension() -> None:
    stats = TrackStats(
        category="科技/AI",
        avg_social=3.0,
        avg_knowledge=9.0,
        avg_affiliate=2.0,
        avg_consulting=5.0,
    )
    dim, val = stats.best_dimension
    assert dim == "知識產品"
    assert val == 9.0


# ── TrackAnalyzer mock path ───────────────────────────────────────────────────

def test_track_analyzer_mock_backend() -> None:
    settings = AppSettings(provider_backend="mock")
    analyzer = TrackAnalyzer(settings)
    stats = TrackStats(category="科技/AI", high_score_count=5, top_items=[_make_item()])
    result = asyncio.run(analyzer.get_insight(stats))
    assert result.category == "科技/AI"
    assert len(result.common_themes) > 0
    assert result.action_plan[0]["step"] == 1

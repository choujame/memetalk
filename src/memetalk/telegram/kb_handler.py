from __future__ import annotations

import logging
import re

from memetalk.config import AppSettings
from memetalk.social_kb.analyzer import SocialContentAnalyzer
from memetalk.social_kb.extractor import ContentExtractor
from memetalk.social_kb.models import ContentItem
from memetalk.social_kb.repository import SocialContentRepository

logger = logging.getLogger(__name__)

_URL_RE = re.compile(r"https?://[^\s]+")


def _bar(score: float) -> str:
    n = round(max(0.0, min(10.0, score)))
    return "█" * n + "░" * (10 - n) + f" {score:.1f}"


def _repo(bot_data: dict) -> SocialContentRepository:
    return bot_data["kb_repo"]


def _analyzer(bot_data: dict) -> SocialContentAnalyzer:
    return bot_data["kb_analyzer"]


async def _save_url(url: str, message, repo: SocialContentRepository, analyzer: SocialContentAnalyzer) -> None:
    existing = repo.get_item_by_url(url)
    if existing:
        m = existing.analysis.monetization
        await message.reply_text(
            f"ℹ️ 此連結已在知識庫\n"
            f"📂 {existing.analysis.category}　⭐ {m.overall_score:.1f}/10\n"
            f"📝 {existing.analysis.summary[:100]}"
        )
        return

    await message.reply_text("⏳ 正在抓取並分析，請稍候...")

    extractor = ContentExtractor()
    title, content, platform = await extractor.fetch(url)
    analysis = await analyzer.analyze(url, title, content)

    item = ContentItem(url=url, title=title, raw_content=content,
                       source_platform=platform, analysis=analysis)
    repo.save_item(item)

    m = analysis.monetization
    channels = "\n".join(f"  • {c}" for c in m.channels[:3]) or "  （無建議）"
    tags = " ".join(f"#{t}" for t in analysis.tags[:5])

    await message.reply_text(
        f"✅ 已加入知識庫\n\n"
        f"📰 {title or url}\n"
        f"📂 {analysis.category}　📡 {platform}\n"
        f"🏷 {tags}\n\n"
        f"📝 {analysis.summary}\n\n"
        f"💰 變現評分\n"
        f"🔥 社群：{_bar(m.social_score)}\n"
        f"📚 知識：{_bar(m.knowledge_score)}\n"
        f"🛒 聯盟：{_bar(m.affiliate_score)}\n"
        f"💼 顧問：{_bar(m.consulting_score)}\n"
        f"⭐ 綜合：{_bar(m.overall_score)}\n\n"
        f"🚀 建議管道：\n{channels}\n\n"
        f"💡 {m.reasoning[:150]}"
    )


async def save_command(update, context) -> None:
    if update.message is None:
        return
    text = " ".join(context.args or []).strip()
    urls = _URL_RE.findall(text)
    if not urls:
        await update.message.reply_text(
            "請提供要儲存的網址。\n用法：/save https://example.com/article"
        )
        return
    await _save_url(urls[0], update.message, _repo(context.bot_data), _analyzer(context.bot_data))


async def kb_command(update, context) -> None:
    if update.message is None:
        return
    repo = _repo(context.bot_data)
    total = repo.count_items()
    if total == 0:
        await update.message.reply_text(
            "📚 知識庫目前是空的。\n傳送 /save <url> 開始收藏內容。"
        )
        return
    stats = repo.get_category_stats()
    lines = "\n".join(f"  {cat}: {cnt} 篇" for cat, cnt in list(stats.items())[:8])
    await update.message.reply_text(
        f"📚 知識庫統計\n總收藏：{total} 篇\n\n分類分布：\n{lines}\n\n"
        f"指令：\n/save <url>　收藏新內容\n/find <關鍵字>　搜尋知識庫"
    )


async def find_command(update, context) -> None:
    if update.message is None:
        return
    query = " ".join(context.args or []).strip()
    if not query:
        await update.message.reply_text("用法：/find AI 創業")
        return
    repo = _repo(context.bot_data)
    items = repo.list_items(search_query=query, sort_by="score", limit=5)
    if not items:
        await update.message.reply_text(f"找不到與「{query}」相關的內容。")
        return
    lines = [f"🔍 找到 {len(items)} 篇相關內容：\n"]
    for i, it in enumerate(items, 1):
        lines.append(
            f"{i}. [{it.analysis.category}] {it.title or it.url[:50]}\n"
            f"   ⭐ {it.analysis.monetization.overall_score:.1f}/10　"
            f"{it.analysis.summary[:60]}...\n"
            f"   🔗 {it.url}\n"
        )
    await update.message.reply_text("\n".join(lines))


def register_kb_handlers(application, settings: AppSettings) -> None:
    try:
        from telegram.ext import CommandHandler
    except ImportError:
        return

    repo = SocialContentRepository(settings.sqlite_path)
    repo.initialize()

    application.bot_data["kb_repo"] = repo
    application.bot_data["kb_analyzer"] = SocialContentAnalyzer(settings)

    application.add_handler(CommandHandler("save", save_command))
    application.add_handler(CommandHandler("kb", kb_command))
    application.add_handler(CommandHandler("find", find_command))

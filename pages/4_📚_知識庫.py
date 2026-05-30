from __future__ import annotations

import asyncio
import concurrent.futures

import streamlit as st

from memetalk.app.settings_io import load_settings
from memetalk.app.ui import setup_page
from memetalk.social_kb.analyzer import SocialContentAnalyzer
from memetalk.social_kb.extractor import ContentExtractor
from memetalk.social_kb.models import ALL_CATEGORIES, ContentItem
from memetalk.social_kb.repository import SocialContentRepository

setup_page(
    page_title="MemeTalk - 知識庫",
    page_icon="📚",
    title="社群內容知識庫",
    subtitle="收藏你在 FB、IG、X 等平台看到的好內容，AI 自動分類並評估變現潛力。",
    eyebrow="Knowledge Base",
    chips=("分類篩選", "變現評分", "關鍵字搜尋", "新增內容"),
)


def _run_async(coro):
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


@st.cache_resource
def _get_repo() -> SocialContentRepository:
    settings = load_settings()
    repo = SocialContentRepository(settings.sqlite_path)
    repo.initialize()
    return repo


def _get_analyzer() -> SocialContentAnalyzer:
    return SocialContentAnalyzer(load_settings())


def _score_icon(score: float) -> str:
    if score >= 7:
        return "🟢"
    if score >= 4:
        return "🟡"
    return "🔴"


def _score_bar(label: str, score: float) -> str:
    filled = round(max(0.0, min(10.0, score)))
    bar = "█" * filled + "░" * (10 - filled)
    return f"{_score_icon(score)} **{label}** `{bar}` {score:.1f}"


def _render_item(item: ContentItem, repo: SocialContentRepository) -> None:
    m = item.analysis.monetization
    badge = f"⭐ {m.overall_score:.1f}" if m.overall_score > 0 else "⏳"
    tags_md = " ".join(f"`#{t}`" for t in item.analysis.tags[:5])
    display_title = item.title or item.url[:70]

    with st.expander(f"**[{item.analysis.category}]** {display_title}　{badge}", expanded=False):
        col_left, col_right = st.columns([3, 2])

        with col_left:
            st.caption(
                f"📡 {item.source_platform or '未知來源'}　"
                f"🕐 {item.created_at.strftime('%Y-%m-%d %H:%M')}"
            )
            if tags_md:
                st.markdown(tags_md)
            st.markdown(f"**摘要：** {item.analysis.summary}")
            if item.analysis.key_points:
                for pt in item.analysis.key_points[:3]:
                    st.markdown(f"- {pt}")
            if item.analysis.trend_relevance:
                st.info(f"📈 {item.analysis.trend_relevance}")
            st.markdown(f"🔗 [開啟原始連結]({item.url})")

        with col_right:
            st.markdown("**💰 變現評分**")
            st.markdown(_score_bar("社群流量", m.social_score))
            st.markdown(_score_bar("知識產品", m.knowledge_score))
            st.markdown(_score_bar("聯盟行銷", m.affiliate_score))
            st.markdown(_score_bar("接案顧問", m.consulting_score))
            st.divider()
            st.markdown(f"### ⭐ {m.overall_score:.1f} / 10")
            if m.channels:
                st.markdown("**建議管道：**")
                for ch in m.channels[:3]:
                    st.markdown(f"• {ch}")

        if m.content_angles:
            st.markdown("**✍️ 內容切入角度：**")
            for angle in m.content_angles[:2]:
                st.markdown(f"→ {angle}")
        if m.reasoning:
            st.caption(f"💡 {m.reasoning}")

        if st.button("🗑️ 刪除此筆", key=f"del_{item.item_id}"):
            repo.delete_item(item.item_id)
            st.success("已刪除")
            st.rerun()


# ── Sidebar ──────────────────────────────────────────────
repo = _get_repo()

with st.sidebar:
    st.header("篩選 & 搜尋")
    search_query = st.text_input("🔍 關鍵字", placeholder="標題、摘要、標籤...")
    category_filter = st.multiselect("📂 分類", list(ALL_CATEGORIES))
    min_score = st.slider("⭐ 最低變現評分", 0.0, 10.0, 0.0, step=0.5)
    sort_by = st.radio("排序", ["最新收藏", "評分最高"], horizontal=True)

    st.divider()
    total = repo.count_items()
    stats = repo.get_category_stats()
    st.metric("📚 知識庫", f"{total} 篇")
    if stats:
        for cat, cnt in list(stats.items())[:6]:
            st.caption(f"  {cat}: {cnt}")

# ── Overview metrics ──────────────────────────────────────
col1, col2, col3 = st.columns(3)
all_for_stats = repo.list_items(limit=max(total, 1))
high_val = sum(1 for it in all_for_stats if it.analysis.monetization.overall_score >= 7)
top_cat = list(stats.keys())[0] if stats else "—"

col1.metric("總收藏", total)
col2.metric("高變現潛力 (≥7)", high_val)
col3.metric("最多分類", top_cat)

st.divider()

# ── Add new item ──────────────────────────────────────────
with st.expander("➕ 新增內容", expanded=(total == 0)):
    new_url = st.text_input("貼上 URL", placeholder="https://...")
    add_btn = st.button("🔍 分析並收藏", type="primary", disabled=not new_url)

    if add_btn and new_url:
        existing = repo.get_item_by_url(new_url)
        if existing:
            st.warning("此 URL 已在知識庫中。")
        else:
            with st.spinner("正在抓取並分析內容，請稍候..."):
                extractor = ContentExtractor()
                analyzer = _get_analyzer()
                title, content, platform = _run_async(extractor.fetch(new_url))
                analysis = _run_async(analyzer.analyze(new_url, title, content))
                item = ContentItem(
                    url=new_url, title=title,
                    raw_content=content, source_platform=platform,
                    analysis=analysis,
                )
                repo.save_item(item)
            st.success(f"✅ 已收藏：{title or new_url}")
            st.rerun()

st.divider()

# ── Item list ─────────────────────────────────────────────
sort_key = "score" if sort_by == "評分最高" else "created_at"
items = repo.list_items(
    categories=category_filter or None,
    min_score=min_score,
    search_query=search_query,
    sort_by=sort_key,
    limit=50,
)

if not items:
    if total == 0:
        st.info(
            "知識庫是空的。\n\n"
            "- 使用上方「新增內容」貼上 URL\n"
            "- 或透過 Telegram Bot 傳送 `/save <url>`"
        )
    else:
        st.info("沒有符合篩選條件的內容。")
else:
    st.caption(f"顯示 {len(items)} 筆")
    for item in items:
        _render_item(item, repo)

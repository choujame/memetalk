from __future__ import annotations

import asyncio
import concurrent.futures

import streamlit as st

from memetalk.app.settings_io import load_settings
from memetalk.app.ui import setup_page
from memetalk.social_kb.analyzer import SocialContentAnalyzer
from memetalk.social_kb.extractor import ContentExtractor
from memetalk.social_kb.generator import ARTICLE_STYLES, ArticleGenerator, GeneratedArticle
from memetalk.social_kb.models import ALL_CATEGORIES, ContentItem
from memetalk.social_kb.repository import SocialContentRepository

setup_page(
    page_title="MemeTalk - 知識庫",
    page_icon="📚",
    title="社群內容知識庫",
    subtitle="收藏 FB、IG、X 好內容，AI 自動分類 + 評估變現潛力 + 整合產出新文章。",
    eyebrow="Knowledge Base",
    chips=("分類篩選", "變現評分", "文章生成", "新增內容"),
)


# ── Helpers ──────────────────────────────────────────────────────────────────

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


def _get_generator() -> ArticleGenerator:
    return ArticleGenerator(load_settings())


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


def _toggle_select(item_id: str) -> None:
    ids: set = st.session_state.setdefault("selected_ids", set())
    if st.session_state.get(f"sel_{item_id}", False):
        ids.add(item_id)
    else:
        ids.discard(item_id)


def _render_item(item: ContentItem, repo: SocialContentRepository) -> None:
    m = item.analysis.monetization
    badge = f"⭐ {m.overall_score:.1f}" if m.overall_score > 0 else "⏳"
    tags_md = " ".join(f"`#{t}`" for t in item.analysis.tags[:5])
    display_title = item.title or item.url[:70]
    is_selected = item.item_id in st.session_state.get("selected_ids", set())

    col_check, col_card = st.columns([1, 20])

    with col_check:
        st.checkbox(
            "",
            key=f"sel_{item.item_id}",
            value=is_selected,
            on_change=_toggle_select,
            args=(item.item_id,),
            label_visibility="collapsed",
            help="選取後可與其他文章合併產生新文章",
        )

    with col_card:
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
                st.markdown("**✍️ 切入角度：**")
                for angle in m.content_angles[:2]:
                    st.markdown(f"→ {angle}")
            if m.reasoning:
                st.caption(f"💡 {m.reasoning}")

            if st.button("🗑️ 刪除", key=f"del_{item.item_id}"):
                repo.delete_item(item.item_id)
                st.session_state.get("selected_ids", set()).discard(item.item_id)
                st.rerun()


def _render_generated_article(article: GeneratedArticle, sources: list[str]) -> None:
    st.success(f"✅ 文章已生成，由 **{len(sources)} 篇**來源整合而成")

    col_a, col_b = st.columns([3, 1])
    with col_b:
        wc = article.word_count()
        st.metric("字數", f"{wc:,}")
        st.metric("預估閱讀", f"{max(1, wc // 300)} 分鐘")
        if article.formats:
            st.markdown("**建議發布平台：**")
            for fmt in article.formats:
                st.markdown(f"• {fmt}")
        if article.hashtags:
            st.markdown("**Hashtags：**")
            st.code(" ".join(article.hashtags), language=None)

    with col_a:
        st.markdown(f"# {article.title}")
        if article.subtitle:
            st.markdown(f"*{article.subtitle}*")
        st.divider()
        st.markdown(article.intro)
        for sec in article.sections:
            st.markdown(f"### {sec.get('heading', '')}")
            st.markdown(sec.get("content", ""))
        st.divider()
        st.markdown(article.conclusion)

    with st.expander("📋 複製全文（Markdown 格式）"):
        st.text_area(
            label="全文",
            value=article.to_markdown(),
            height=400,
            label_visibility="collapsed",
        )

    st.caption(f"來源文章：{'　|　'.join(sources)}")

    if st.button("🗑️ 清除文章", type="secondary"):
        st.session_state.pop("generated_article", None)
        st.session_state.pop("generated_sources", None)
        st.rerun()


# ── Sidebar ──────────────────────────────────────────────────────────────────

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

    st.divider()
    selected_ids: set = st.session_state.get("selected_ids", set())
    if selected_ids:
        st.info(f"✅ 已選取 **{len(selected_ids)}** 篇")
        if st.button("清除選取", use_container_width=True):
            st.session_state["selected_ids"] = set()
            st.rerun()
    else:
        st.caption("勾選文章後可合併產生新文章")


# ── Overview metrics ──────────────────────────────────────────────────────────

col1, col2, col3 = st.columns(3)
all_for_stats = repo.list_items(limit=max(total, 1))
high_val = sum(1 for it in all_for_stats if it.analysis.monetization.overall_score >= 7)
top_cat = list(stats.keys())[0] if stats else "—"

col1.metric("總收藏", total)
col2.metric("高變現潛力 ≥7", high_val)
col3.metric("最多分類", top_cat)

st.divider()

# ── Generated article (persisted in session_state) ────────────────────────────

if "generated_article" in st.session_state:
    with st.container(border=True):
        _render_generated_article(
            st.session_state["generated_article"],
            st.session_state.get("generated_sources", []),
        )
    st.divider()

# ── Add new item ──────────────────────────────────────────────────────────────

with st.expander("➕ 新增內容", expanded=(total == 0)):
    new_url = st.text_input("貼上 URL", placeholder="https://...")
    add_btn = st.button("🔍 分析並收藏", type="primary", disabled=not new_url)

    if add_btn and new_url:
        existing = repo.get_item_by_url(new_url)
        if existing:
            st.warning("此 URL 已在知識庫中。")
        else:
            with st.spinner("正在抓取並分析內容..."):
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

# ── Item list ─────────────────────────────────────────────────────────────────

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
        st.info("知識庫是空的。\n\n- 使用上方「新增內容」貼上 URL\n- 或透過 Telegram Bot 傳送 `/save <url>`")
    else:
        st.info("沒有符合篩選條件的內容。")
else:
    st.caption(f"顯示 {len(items)} 筆　｜　勾選後可合併產生新文章 👇")
    for item in items:
        _render_item(item, repo)

# ── Article generation panel (bottom) ─────────────────────────────────────────

current_selected_ids: set = st.session_state.get("selected_ids", set())
selected_items = [item for item in items if item.item_id in current_selected_ids]

# Also pick up items not in current filtered list but selected (from previous filter state)
rendered_ids = {it.item_id for it in items}
ghost_ids = current_selected_ids - rendered_ids
if ghost_ids:
    for gid in ghost_ids:
        ghost = repo.get_item(gid)
        if ghost:
            selected_items.append(ghost)

if selected_items:
    st.divider()
    with st.container(border=True):
        st.markdown(f"### ✍️ 已選取 {len(selected_items)} 篇，產生整合文章")
        for it in selected_items:
            st.caption(f"  • {it.title or it.url[:60]}")

        if len(selected_items) < 2:
            st.warning("請至少選取 **2 篇**文章。")
        else:
            gen_col1, gen_col2 = st.columns([3, 1])
            with gen_col1:
                style = st.selectbox(
                    "文章風格",
                    list(ARTICLE_STYLES),
                    help=(
                        "部落格/Medium：結構清晰的長文\n"
                        "LinkedIn 長文：個人觀點、有故事感\n"
                        "IG 懶人包：短段落、emoji 豐富\n"
                        "新聞稿：客觀中立格式"
                    ),
                )
            with gen_col2:
                gen_btn = st.button("🚀 產生文章", type="primary", use_container_width=True)

            if gen_btn:
                with st.spinner(f"AI 正在整合 {len(selected_items)} 篇文章，請稍候..."):
                    generator = _get_generator()
                    article = _run_async(generator.generate(selected_items, style))
                    st.session_state["generated_article"] = article
                    st.session_state["generated_sources"] = [
                        it.title or it.url[:50] for it in selected_items
                    ]
                st.success("文章已生成！")
                st.rerun()

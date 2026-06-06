from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from memetalk.config import AppSettings
from memetalk.social_kb.models import ContentItem

logger = logging.getLogger(__name__)

ARTICLE_STYLES = ("部落格/Medium", "LinkedIn 長文", "IG 懶人包", "新聞稿")

_STYLE_NOTES = {
    "部落格/Medium": "文章風格：知識性長文，有清楚的標題結構，適合 Medium 或個人部落格發布。",
    "LinkedIn 長文": "文章風格：個人觀點分享，開場有故事感，語氣親切但專業，適合 LinkedIn。",
    "IG 懶人包": "文章風格：每段極短，大量使用條列式與 emoji 增加可讀性，適合截成 IG 懶人包圖文。",
    "新聞稿": "文章風格：客觀中立的新聞稿，有引言、背景說明、分析、結語，不帶個人觀點。",
}

_PROMPT = """\
你是一位擅長整合多元觀點的繁體中文內容創作者。
請根據以下 {count} 篇文章的資訊，撰寫一篇全新的原創文章。

{style_note}

---來源文章---
{sources}
---

撰寫要求：
- 整合多篇文章的觀點，找出共同主題或創造新視角，不是逐篇摘要
- 加入自己的分析或見解，讓文章有獨特價值
- 直接輸出 JSON，不含其他文字

輸出 JSON 格式：
{{
  "title": "文章標題（吸引人，30字以內）",
  "subtitle": "副標題（說明核心價值，40字以內）",
  "intro": "引言（150字以內，點出讀者痛點或趨勢，吸引繼續閱讀）",
  "sections": [
    {{"heading": "段落標題", "content": "段落內容（200–400字）"}},
    {{"heading": "段落標題", "content": "段落內容"}},
    {{"heading": "段落標題", "content": "段落內容"}}
  ],
  "conclusion": "結語（100字以內，呼籲行動或總結重點）",
  "hashtags": ["#標籤1", "#標籤2", "#標籤3", "#標籤4", "#標籤5"],
  "formats": ["適合發布的平台或格式，如 Medium 部落格、LinkedIn 個人頁面"]
}}\
"""


@dataclass
class GeneratedArticle:
    title: str = ""
    subtitle: str = ""
    intro: str = ""
    sections: list[dict] = field(default_factory=list)
    conclusion: str = ""
    hashtags: list[str] = field(default_factory=list)
    formats: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        parts: list[str] = []
        parts.append(f"# {self.title}")
        if self.subtitle:
            parts.append(f"*{self.subtitle}*")
        parts.append("")
        parts.append(self.intro)
        for sec in self.sections:
            parts.append(f"\n## {sec.get('heading', '')}")
            parts.append(sec.get("content", ""))
        parts.append(f"\n---\n{self.conclusion}")
        if self.hashtags:
            parts.append("\n" + "  ".join(self.hashtags))
        return "\n\n".join(parts)

    def word_count(self) -> int:
        text = self.intro + self.conclusion
        text += "".join(s.get("content", "") for s in self.sections)
        return len(text)


class ArticleGenerator:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def generate(
        self,
        items: list[ContentItem],
        style: str = "部落格/Medium",
    ) -> GeneratedArticle:
        if self.settings.provider_backend == "mock":
            return GeneratedArticle(
                title=f"【Mock】整合 {len(items)} 篇文章的測試文章",
                subtitle="這是 mock provider 產生的測試文章",
                intro="這是 mock provider 產生的引言段落，實際使用時請設定 AI Provider。",
                sections=[{"heading": "主要內容", "content": "mock 內容段落。"}],
                conclusion="mock 結語。",
                hashtags=["#mock", "#測試"],
                formats=["Mock 模式，不支援實際發布"],
            )

        sources = self._format_sources(items)
        prompt = _PROMPT.format(
            count=len(items),
            style_note=_STYLE_NOTES.get(style, _STYLE_NOTES["部落格/Medium"]),
            sources=sources,
        )
        raw = ""
        try:
            if self.settings.provider_backend == "claude":
                raw = await self._call_anthropic(prompt)
            else:
                raw = await self._call_openai(prompt)
        except Exception:
            logger.exception("文章生成失敗")

        if raw:
            article = self._parse(raw)
            if article:
                return article
        return GeneratedArticle(
            title="生成失敗",
            intro="請確認 AI Provider 設定正確後再試。",
        )

    def _format_sources(self, items: list[ContentItem]) -> str:
        parts = []
        for i, item in enumerate(items, 1):
            a = item.analysis
            points = "\n".join(f"  - {p}" for p in a.key_points[:3])
            parts.append(
                f"【文章 {i}】{item.title or item.url}\n"
                f"分類：{a.category}\n"
                f"摘要：{a.summary}\n"
                f"重點：\n{points}\n"
                f"趨勢：{a.trend_relevance}"
            )
        return "\n\n".join(parts)

    async def _call_openai(self, prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            return ""

        backend = self.settings.provider_backend
        if backend == "openai":
            if not self.settings.openai_api_key:
                return ""
            client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url or None,
            )
            model = self.settings.openai_chat_model
        elif backend in ("lmstudio", "local"):
            client = AsyncOpenAI(
                base_url=self.settings.lmstudio_base_url,
                api_key=self.settings.lmstudio_api_key or "lmstudio",
            )
            model = self.settings.lmstudio_chat_model or "local"
        elif backend == "ollama":
            client = AsyncOpenAI(base_url=self.settings.ollama_base_url, api_key="ollama")
            model = self.settings.ollama_chat_model or "llama3"
        elif backend == "llama_cpp":
            client = AsyncOpenAI(base_url=self.settings.llama_cpp_base_url, api_key="llama_cpp")
            model = "local"
        elif backend == "gemini":
            if not self.settings.gemini_api_key:
                return ""
            client = AsyncOpenAI(
                api_key=self.settings.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            model = self.settings.gemini_chat_model
        else:
            return ""

        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3000,
        )
        return resp.choices[0].message.content or ""

    async def _call_anthropic(self, prompt: str) -> str:
        try:
            import anthropic
        except ImportError:
            return ""
        if not self.settings.claude_api_key:
            return ""
        client = anthropic.AsyncAnthropic(api_key=self.settings.claude_api_key)
        msg = await client.messages.create(
            model=self.settings.claude_chat_model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text if msg.content else ""

    def _parse(self, raw: str) -> GeneratedArticle | None:
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if not m:
                return None
            try:
                data = json.loads(m.group())
            except Exception:
                return None

        return GeneratedArticle(
            title=str(data.get("title", "")),
            subtitle=str(data.get("subtitle", "")),
            intro=str(data.get("intro", "")),
            sections=list(data.get("sections", [])),
            conclusion=str(data.get("conclusion", "")),
            hashtags=list(data.get("hashtags", [])),
            formats=list(data.get("formats", [])),
        )

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

from memetalk.config import AppSettings
from memetalk.social_kb.models import ContentItem

logger = logging.getLogger(__name__)

MIN_HIGH_SCORE = 7.0

# (icon, label, description)
_READINESS = [
    (10, "🌳", "素材豐富，立刻行動"),
    (5,  "🌿", "已達深耕門檻，建議啟動"),
    (3,  "🌱", "初具規模，可以開始規劃"),
    (1,  "📌", "持續收藏中，尚未達到門檻"),
]


@dataclass
class TrackStats:
    category: str
    total_count: int = 0
    high_score_count: int = 0
    avg_score: float = 0.0
    avg_social: float = 0.0
    avg_knowledge: float = 0.0
    avg_affiliate: float = 0.0
    avg_consulting: float = 0.0
    top_items: list[ContentItem] = field(default_factory=list)

    @property
    def readiness(self) -> tuple[str, str]:
        for threshold, icon, label in _READINESS:
            if self.high_score_count >= threshold:
                return icon, label
        return "📌", "尚無高分文章"

    @property
    def best_dimension(self) -> tuple[str, float]:
        dims = [
            ("社群流量", self.avg_social),
            ("知識產品", self.avg_knowledge),
            ("聯盟行銷", self.avg_affiliate),
            ("接案顧問", self.avg_consulting),
        ]
        return max(dims, key=lambda x: x[1])


@dataclass
class TrackInsight:
    category: str
    common_themes: list[str] = field(default_factory=list)
    market_opportunity: str = ""
    recommended_products: list[dict] = field(default_factory=list)
    action_plan: list[dict] = field(default_factory=list)
    competitive_advantage: str = ""


_PROMPT = """\
你是一位內容創業顧問。以下是使用者在「{category}」主題收藏的 {count} 篇高分文章：

{summaries}

請分析此賽道的變現潛力，給出具體行動建議（繁體中文，直接輸出 JSON 不含其他文字）：
{{
  "common_themes": ["共同主題1", "主題2", "主題3"],
  "market_opportunity": "市場機會說明（100字以內）",
  "recommended_products": [
    {{"type": "課程/電子書/社群訂閱/模板/顧問服務...", "title": "具體產品名稱", "description": "50字說明"}},
    {{"type": "...", "title": "...", "description": "..."}}
  ],
  "action_plan": [
    {{"step": 1, "action": "第一步具體行動", "timeline": "1個月內"}},
    {{"step": 2, "action": "第二步", "timeline": "3個月內"}},
    {{"step": 3, "action": "第三步", "timeline": "6個月內"}}
  ],
  "competitive_advantage": "在此領域的潛在競爭優勢說明（50字）"
}}\
"""


class TrackAnalyzer:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def get_insight(self, stats: TrackStats) -> TrackInsight:
        if not stats.top_items:
            return TrackInsight(category=stats.category)

        summaries = "\n\n".join(
            f"【文章 {i}】{it.title or it.url}\n"
            f"摘要：{it.analysis.summary}\n"
            f"重點：{'　/　'.join(it.analysis.key_points[:2])}\n"
            f"綜合評分：{it.analysis.monetization.overall_score:.1f}"
            for i, it in enumerate(stats.top_items[:8], 1)
        )
        prompt = _PROMPT.format(
            category=stats.category,
            count=len(stats.top_items),
            summaries=summaries,
        )
        raw = ""
        try:
            if self.settings.provider_backend == "claude":
                raw = await self._call_anthropic(prompt)
            else:
                raw = await self._call_openai(prompt)
        except Exception:
            logger.exception("賽道洞察分析失敗")

        if raw:
            insight = self._parse(raw, stats.category)
            if insight:
                return insight
        return TrackInsight(category=stats.category)

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
            temperature=0.3,
            max_tokens=1500,
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
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text if msg.content else ""

    def _parse(self, raw: str, category: str) -> TrackInsight | None:
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

        return TrackInsight(
            category=category,
            common_themes=list(data.get("common_themes", [])),
            market_opportunity=str(data.get("market_opportunity", "")),
            recommended_products=list(data.get("recommended_products", [])),
            action_plan=list(data.get("action_plan", [])),
            competitive_advantage=str(data.get("competitive_advantage", "")),
        )

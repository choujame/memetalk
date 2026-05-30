from __future__ import annotations

import json
import logging
import re

from memetalk.config import AppSettings
from memetalk.social_kb.models import ContentAnalysis, MonetizationScore

logger = logging.getLogger(__name__)

_PROMPT = """\
你是一個專業的社群內容分析師。請分析以下內容，以繁體中文回答，直接輸出 JSON 不含其他文字。

來源網址：{url}
頁面標題：{title}
內容節錄：{content}

輸出格式：
{{
  "category": "只選一個：科技/AI、商業/創業、投資/理財、健康/養生、教育/學習、行銷/自媒體、娛樂/文化、時事/社會、其他",
  "tags": ["標籤1", "標籤2", "標籤3"],
  "summary": "100字以內的內容重點摘要",
  "key_points": ["重點1", "重點2", "重點3"],
  "trend_relevance": "此主題的市場趨勢與當前時機說明（50字以內）",
  "monetization": {{
    "social_score": 評分0到10,
    "knowledge_score": 評分0到10,
    "affiliate_score": 評分0到10,
    "consulting_score": 評分0到10,
    "overall_score": 評分0到10,
    "channels": ["具體變現管道1", "管道2", "管道3"],
    "content_angles": ["內容切入角度1", "角度2"],
    "reasoning": "綜合說明變現潛力（50字以內）"
  }}
}}

評分說明（0=無潛力，10=極高潛力）：
- social_score：在 IG/FB/X/TikTok 吸粉、接業配、業配廣告的潛力
- knowledge_score：包裝成線上課程、電子書、Notion 模板、訂閱制的潛力
- affiliate_score：推薦商品服務並放聯盟連結獲利的潛力
- consulting_score：以此領域提供顧問、培訓、接案、演講的潛力
- overall_score：綜合四個面向的整體變現潛力\
"""


class SocialContentAnalyzer:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    async def analyze(self, url: str, title: str, content: str) -> ContentAnalysis:
        prompt = _PROMPT.format(
            url=url or "(未知)",
            title=title or "(無標題)",
            content=content[:3500] if content else "(無內容)",
        )
        raw = ""
        try:
            if self.settings.provider_backend == "claude":
                raw = await self._call_anthropic(prompt)
            else:
                raw = await self._call_openai(prompt)
        except Exception:
            logger.exception("社群內容分析失敗")

        if raw:
            parsed = self._parse(raw)
            if parsed:
                return parsed
        return self._stub(title)

    async def _call_openai(self, prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError:
            return ""

        backend = self.settings.provider_backend
        if backend in ("openai",):
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
            client = AsyncOpenAI(
                base_url=self.settings.ollama_base_url,
                api_key="ollama",
            )
            model = self.settings.ollama_chat_model or "llama3"
        elif backend == "llama_cpp":
            client = AsyncOpenAI(
                base_url=self.settings.llama_cpp_base_url,
                api_key="llama_cpp",
            )
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
            temperature=0.2,
            max_tokens=1200,
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
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text if msg.content else ""

    def _parse(self, raw: str) -> ContentAnalysis | None:
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

        mon = data.get("monetization", {})
        monetization = MonetizationScore(
            social_score=float(mon.get("social_score", 0)),
            knowledge_score=float(mon.get("knowledge_score", 0)),
            affiliate_score=float(mon.get("affiliate_score", 0)),
            consulting_score=float(mon.get("consulting_score", 0)),
            overall_score=float(mon.get("overall_score", 0)),
            channels=list(mon.get("channels", [])),
            content_angles=list(mon.get("content_angles", [])),
            reasoning=str(mon.get("reasoning", "")),
        )
        return ContentAnalysis(
            category=str(data.get("category", "其他")),
            tags=list(data.get("tags", [])),
            summary=str(data.get("summary", "")),
            key_points=list(data.get("key_points", [])),
            trend_relevance=str(data.get("trend_relevance", "")),
            monetization=monetization,
        )

    def _stub(self, title: str) -> ContentAnalysis:
        return ContentAnalysis(
            category="其他",
            tags=["待分析"],
            summary=f"《{title}》尚未完成 AI 分析，請確認 AI Provider 設定",
            key_points=["請在設定頁確認 API Key 與 Provider 設定"],
            trend_relevance="尚未分析",
            monetization=MonetizationScore(
                reasoning="尚未完成分析，請確認 AI Provider 設定",
            ),
        )

from __future__ import annotations

import re
from html.parser import HTMLParser


class _HTMLTextExtractor(HTMLParser):
    _SKIP = frozenset({"script", "style", "head", "nav", "footer", "aside", "noscript"})

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._texts: list[str] = []
        self._title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self._title = text
        elif self._skip_depth == 0:
            self._texts.append(text)

    @property
    def title(self) -> str:
        return self._title

    @property
    def body_text(self) -> str:
        return " ".join(self._texts)


class ContentExtractor:
    MAX_CONTENT_LEN = 8000

    def extract_from_html(self, html: str) -> tuple[str, str]:
        """Returns (title, body_text)."""
        parser = _HTMLTextExtractor()
        try:
            parser.feed(html)
        except Exception:
            pass
        body = re.sub(r"\s+", " ", parser.body_text).strip()
        return parser.title, body[: self.MAX_CONTENT_LEN]

    def detect_platform(self, url: str) -> str:
        u = url.lower()
        if "facebook.com" in u or "fb.com" in u:
            return "Facebook"
        if "instagram.com" in u:
            return "Instagram"
        if "x.com" in u or "twitter.com" in u:
            return "X/Twitter"
        if "youtube.com" in u or "youtu.be" in u:
            return "YouTube"
        if "linkedin.com" in u:
            return "LinkedIn"
        if "medium.com" in u:
            return "Medium"
        if "threads.net" in u:
            return "Threads"
        if "tiktok.com" in u:
            return "TikTok"
        return "其他"

    async def fetch(self, url: str) -> tuple[str, str, str]:
        """Returns (title, content, platform). Never raises."""
        platform = self.detect_platform(url)
        try:
            import httpx
        except ImportError:
            return "", url, platform

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        }

        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                ct = resp.headers.get("content-type", "")
                if "text/html" not in ct and "text/plain" not in ct:
                    return "", url, platform
                title, body = self.extract_from_html(resp.text)
                return title or url, body, platform
        except Exception:
            return "", url, platform

import logging
import re
import time

import praw
import google.generativeai as genai
import requests

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

SUBREDDITS = ["SaaS", "solopreneur"]
POST_LIMIT = 20
KEYWORDS = [
    r"\bcomplain\b",
    r"\bhate\b",
    r"\bstruggle\b",
    r"\banyone know\b",
    r"\balternative to\b",
    r"\bhow to\b",
]
KEYWORD_PATTERN = re.compile("|".join(KEYWORDS), re.IGNORECASE)

GEMINI_PROMPT = (
    "分析以下 Reddit 貼文，判斷這是否代表一個潛在的 Micro-SaaS 或一人公司產品機會。"
    "如果是，請輸出：1. 痛點概述 2. 潛在產品想法 3. 商業價值評估(高/中/低)。"
    "如果不是，請僅回覆 'IGNORE'。\n\n"
    "貼文內容：\n{content}"
)


def build_reddit_client() -> praw.Reddit:
    return praw.Reddit(
        client_id=config.REDDIT_CLIENT_ID,
        client_secret=config.REDDIT_CLIENT_SECRET,
        user_agent="reddit_trend_radar/1.0 (by u/trend_radar_bot)",
    )


def fetch_new_posts(reddit: praw.Reddit) -> list[dict]:
    posts = []
    for sub_name in SUBREDDITS:
        try:
            subreddit = reddit.subreddit(sub_name)
            for post in subreddit.new(limit=POST_LIMIT):
                posts.append(
                    {
                        "subreddit": sub_name,
                        "title": post.title,
                        "body": post.selftext,
                        "url": f"https://www.reddit.com{post.permalink}",
                        "author": str(post.author),
                        "score": post.score,
                    }
                )
            logger.info("從 r/%s 取得 %d 篇貼文", sub_name, POST_LIMIT)
        except praw.exceptions.PRAWException as e:
            logger.error("讀取 r/%s 失敗：%s", sub_name, e)
    return posts


def matches_keywords(post: dict) -> bool:
    combined = f"{post['title']} {post['body']}"
    return bool(KEYWORD_PATTERN.search(combined))


def analyze_with_gemini(post: dict) -> str | None:
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

    content = f"標題：{post['title']}\n\n內文：{post['body']}"
    prompt = GEMINI_PROMPT.format(content=content)

    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        logger.info("Gemini 分析完成，結果前 50 字：%s", result[:50])
        return result
    except Exception as e:
        logger.error("Gemini API 呼叫失敗：%s", e)
        return None


def send_telegram_message(text: str) -> bool:
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram 訊息發送成功")
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Telegram 發送失敗：%s", e)
        return False


def format_telegram_message(post: dict, analysis: str) -> str:
    return (
        f"*Reddit 趨勢雷達：潛在機會*\n\n"
        f"*來源*：r/{post['subreddit']}\n"
        f"*標題*：{post['title']}\n"
        f"*連結*：{post['url']}\n\n"
        f"*Gemini 分析*：\n{analysis}"
    )


def run() -> None:
    logger.info("=== Reddit 趨勢雷達啟動 ===")

    reddit = build_reddit_client()
    posts = fetch_new_posts(reddit)
    logger.info("共取得 %d 篇貼文，開始關鍵字篩選...", len(posts))

    matched = [p for p in posts if matches_keywords(p)]
    logger.info("符合關鍵字的貼文：%d 篇", len(matched))

    opportunities_found = 0
    for i, post in enumerate(matched):
        logger.info("[%d/%d] 分析貼文：%s", i + 1, len(matched), post["title"][:60])

        analysis = analyze_with_gemini(post)
        if analysis is None:
            continue

        if analysis.strip().upper() == "IGNORE":
            logger.info("Gemini 判定為非機會，跳過。")
            continue

        opportunities_found += 1
        message = format_telegram_message(post, analysis)
        send_telegram_message(message)

        # 避免連續呼叫 Gemini API 過快
        if i < len(matched) - 1:
            time.sleep(1)

    logger.info("=== 掃描完成，共發現 %d 個潛在機會 ===", opportunities_found)


if __name__ == "__main__":
    run()

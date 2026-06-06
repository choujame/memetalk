from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

ALL_CATEGORIES = (
    "科技/AI",
    "商業/創業",
    "投資/理財",
    "健康/養生",
    "教育/學習",
    "行銷/自媒體",
    "娛樂/文化",
    "時事/社會",
    "其他",
)


class MonetizationScore(BaseModel):
    social_score: float = 0.0     # 社群流量變現 (IG/FB/X 業配、粉絲)
    knowledge_score: float = 0.0  # 知識產品 (課程、電子書、訂閱)
    affiliate_score: float = 0.0  # 聯盟行銷 (商品推薦、導購)
    consulting_score: float = 0.0 # 接案顧問 (培訓、演講、B2B)
    overall_score: float = 0.0    # 綜合評分
    channels: list[str] = Field(default_factory=list)
    content_angles: list[str] = Field(default_factory=list)
    reasoning: str = ""


class ContentAnalysis(BaseModel):
    category: str = "其他"
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    key_points: list[str] = Field(default_factory=list)
    trend_relevance: str = ""
    monetization: MonetizationScore = Field(default_factory=MonetizationScore)


class ContentItem(BaseModel):
    item_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    url: str
    title: str = ""
    raw_content: str = ""
    source_platform: str = ""
    analysis: ContentAnalysis = Field(default_factory=ContentAnalysis)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

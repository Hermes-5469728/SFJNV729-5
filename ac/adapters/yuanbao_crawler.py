"""公众号爬取适配器 · 元宝外部信源

定位：不可信外部信源，所有内容经此入口，不直写数据库。
     初始 verified=0，经 G4(L0/L2/L5) 验证后方可采信。
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any


class YuanbaoAdapter:
    """公众号爬取适配器。所有内容经此入口，不直写数据库。"""

    def __init__(self, api_endpoint: str = ""):
        self._endpoint = api_endpoint

    # ── 公开 API ──

    def crawl_article(self, url: str) -> dict:
        raw = self._call_yuanbao_api(url)
        content = (raw.get("content") or "").strip()
        return {
            "url": url,
            "title": (raw.get("title") or "").strip(),
            "content": content,
            "publish_time": raw.get("publish_time") or datetime.now(timezone.utc).isoformat(),
            "source": "yuanbao",
            "verified": 0,
            "hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "raw_metadata": raw,
        }

    def batch_crawl(self, urls: list[str]) -> list[dict]:
        return [self.crawl_article(u) for u in urls]

    def is_available(self) -> bool:
        return bool(self._endpoint)

    # ── 内部方法 ──

    def _call_yuanbao_api(self, url: str) -> dict:
        """调用真实元宝 API（子类重写或配置 endpoint 后使用）
        
        默认返回 mock 数据供测试和架构验证。
        """
        if self._endpoint:
            import urllib.request
            try:
                req = urllib.request.Request(
                    self._endpoint,
                    json.dumps({"url": url}).encode(),
                    {"Content-Type": "application/json"},
                )
                resp = urllib.request.urlopen(req, timeout=30)
                return json.loads(resp.read())
            except Exception as e:
                return {"title": "", "content": "", "error": str(e), "publish_time": ""}

        return self._mock_crawl(url)

    @staticmethod
    def _mock_crawl(url: str) -> dict:
        """Mock 数据：演示用。对接真实 API 后删除。"""
        return {
            "title": f"模拟公众号文章",
            "content": (
                f"这是来自 {url} 的模拟文章内容。\n\n"
                "在真实接入场景中，元宝将从微信公众号提取完整的文章正文、"
                "标题、发布时间和作者信息。这些原始数据将被标记为 verified=0，"
                "经 G4 管道验证后方可进入 ac_truth 真值库。\n\n"
                "来源：AC 驾驶舱 · 外部信源测试"
            ),
            "publish_time": datetime.now(timezone.utc).isoformat(),
        }


class YuanbaoIngestion:
    """受控入库通道：爬取 → 验证 → 写入 ac_truth

    禁止绕过此通道直写数据库 —— 猎鬼行动 R5 延伸。
    """

    def __init__(self, adapter: YuanbaoAdapter | None = None):
        self.adapter = adapter or YuanbaoAdapter()

    @staticmethod
    def _check_exists(url: str, content_hash: str) -> bool:
        """去重检查：URL 或内容哈希已存在则跳过"""
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).resolve().parent.parent / "ac_platform.db"
        if not db_path.exists():
            return False
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM ac_truth WHERE source='yuanbao' AND (tags LIKE ? OR tags LIKE ?)",
                (f"%url:{url}%", f"%hash:{content_hash}%"),
            )
            return cur.fetchone()[0] > 0
        finally:
            conn.close()

    def ingest(self, article: dict) -> dict:
        """单篇入库：先查重 → store_truth（自带 L0/L2/L5 验证）"""
        from ac.guard import store_truth

        if self._check_exists(article["url"], article["hash"]):
            return {
                "status": "duplicate",
                "title": article["title"],
                "url": article["url"],
            }

        tags = f"yuanbao,wechat,url:{article['url']},hash:{article['hash']}"
        if article.get("publish_time"):
            tags += f",pub:{article['publish_time'][:10]}"

        result = store_truth(
            title=article["title"],
            category="external",
            source="yuanbao",
            content=article["content"],
            tags=tags,
        )

        return {
            "status": "ingested",
            "title": article["title"],
            "url": article["url"],
            "verified": result.get("verified", 0),
            "validation": result.get("validation", "?"),
            "score": result.get("score", 0),
            "truth_id": result.get("rowid"),
            "error": result.get("error"),
        }

    def batch_ingest(self, urls: list[str]) -> list[dict]:
        """批量爬取→入库"""
        articles = self.adapter.batch_crawl(urls)
        return [self.ingest(a) for a in articles]

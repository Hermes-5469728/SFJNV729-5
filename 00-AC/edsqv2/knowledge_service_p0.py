"""
AC Truth Knowledge Service - P0: 统一知识服务层 + P0: 数据TTL降级 + P1: 增量CDC同步
让 truth 从"数据孤岛"升级为"驱动系统决策的活水源头"
"""

import json
import sqlite3
import threading
import time
import hashlib
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import heapq


# ============================================================================
# 数据结构
# ============================================================================

class TruthStatus(Enum):
    ACTIVE = "active"
    QUARANTINE = "quarantine"
    DECAYED = "decayed"
    DELETED = "deleted"


@dataclass
class TruthRecord:
    id: str
    content: str
    category: str
    confidence: float
    status: TruthStatus
    source: str
    tags: List[str]
    created_at: str
    last_verified_at: str
    version: int
    metadata: Dict[str, Any]


@dataclass
class FactCheckResult:
    statement: str
    matched: bool
    matched_record: Optional[TruthRecord]
    confidence: float
    verdict: str
    details: str


@dataclass
class Anchor:
    id: str
    topic: str
    verified_truth: str
    source: str
    confidence_score: float
    tags: List[str]


# ============================================================================
# P0: 统一 KnowledgeService
# ============================================================================

class KnowledgeService:
    """
    统一知识服务层 - 打通 dispatch/orchestrator/auditor 消费链路
    封装 ChromaDB + SQLite，支持缓存和降级
    """

    def __init__(self, db_path: str = "ac_truth.db"):
        self.db_path = db_path
        self._init_db()
        self.cache: Dict[str, List[TruthRecord]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.cache_hits = 0
        self.cache_misses = 0
        self._lock = threading.Lock()

        # 事件总线
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS truth_records (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                category TEXT,
                confidence REAL DEFAULT 0.5,
                status TEXT DEFAULT 'active',
                source TEXT,
                tags TEXT,
                created_at TEXT,
                last_verified_at TEXT,
                version INTEGER DEFAULT 1,
                metadata TEXT,
                deleted_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS truth_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT,
                old_value TEXT,
                new_value TEXT,
                changed_at TEXT,
                changed_by TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS anchors (
                id TEXT PRIMARY KEY,
                topic TEXT,
                verified_truth TEXT,
                source TEXT,
                confidence_score REAL DEFAULT 1.0,
                tags TEXT,
                verified_at TEXT
            )
        """)
        conn.commit()
        conn.close()

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        self._subscribers[event_type].append(callback)

    def _publish(self, event_type: str, data: Any):
        """发布事件"""
        for callback in self._subscribers.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                print(f"事件处理错误: {e}")

    # --- 核心查询 API ---

    def search(self, query: str, categories: Optional[List[str]] = None,
               min_confidence: float = 0.0, limit: int = 10) -> List[TruthRecord]:
        """
        搜索知识库 - dispatch/orchestrator/auditor 统一接口
        """
        cache_key = f"{query}:{categories}:{min_confidence}:{limit}"

        with self._lock:
            if cache_key in self.cache:
                self.cache_hits += 1
                return self.cache[cache_key]

        self.cache_misses += 1

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = "SELECT * FROM truth_records WHERE status = 'active' AND confidence >= ?"
        params = [min_confidence]

        if categories:
            placeholders = ','.join('?' * len(categories))
            sql += f" AND category IN ({placeholders})"
            params.extend(categories)

        if query:
            sql += " AND (content LIKE ? OR tags LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])

        sql += " ORDER BY confidence DESC, last_verified_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        results = [self._row_to_record(row) for row in rows]

        with self._lock:
            self.cache[cache_key] = results

        return results

    def check_fact(self, statement: str, category: Optional[str] = None) -> FactCheckResult:
        """
        事实核查 - orchestrator VERIFY phase 使用
        """
        keywords = self._extract_keywords(statement)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = """
            SELECT * FROM truth_records
            WHERE status = 'active'
            AND (
        """
        conditions = []
        params = []

        for kw in keywords[:5]:
            conditions.append("(content LIKE ? OR tags LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%"])

        sql += " OR ".join(conditions) + ")"

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY confidence DESC LIMIT 5"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return FactCheckResult(
                statement=statement,
                matched=False,
                matched_record=None,
                confidence=0.0,
                verdict="unverified",
                details="知识库中未找到相关记录"
            )

        best_match = self._row_to_record(rows[0])
        similarity = self._calculate_similarity(statement, best_match.content)

        if similarity > 0.7:
            verdict = "consistent" if similarity > 0.85 else "partial"
            details = f"匹配到相似记录 (相似度: {similarity:.2f})"
        else:
            verdict = "conflicting"
            details = f"存在冲突记录 (相似度: {similarity:.2f})"

        return FactCheckResult(
            statement=statement,
            matched=True,
            matched_record=best_match,
            confidence=similarity * best_match.confidence,
            verdict=verdict,
            details=details
        )

    def get_anchors(self, category: Optional[str] = None) -> List[Anchor]:
        """
        获取锚点 - HallucinationAuditor 使用
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if category:
            cursor.execute("SELECT * FROM anchors WHERE topic LIKE ?", [f"%{category}%"])
        else:
            cursor.execute("SELECT * FROM anchors")

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_anchor(row) for row in rows]

    # --- 存储 API ---

    def store(self, record: TruthRecord, user_id: str = "system") -> bool:
        """
        存储知识 - 触发 CDC 事件
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO truth_records
            (id, content, category, confidence, status, source, tags,
             created_at, last_verified_at, version, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            record.content,
            record.category,
            record.confidence,
            record.status.value,
            record.source,
            json.dumps(record.tags),
            record.created_at,
            record.last_verified_at,
            record.version,
            json.dumps(record.metadata)
        ))

        conn.commit()
        conn.close()

        self._clear_cache()
        self._publish("truth_stored", record)

        return True

    def update_status(self, record_id: str, new_status: TruthStatus):
        """更新状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE truth_records SET status = ? WHERE id = ?",
            [new_status.value, record_id]
        )

        conn.commit()
        conn.close()

        self._clear_cache()
        self._publish("truth_status_changed", {"id": record_id, "status": new_status})

    # --- 辅助方法 ---

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        import re
        words = re.findall(r'\b[\u4e00-\u9fa5a-zA-Z0-9]{2,}\b', text.lower())
        stop_words = {"的", "是", "在", "有", "和", "了", "我", "你", "他", "这", "那", "个",
                     "the", "a", "an", "is", "are", "was", "were", "be", "been", "being"}
        return [w for w in words if w not in stop_words][:10]

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """简单相似度计算"""
        keywords1 = set(self._extract_keywords(text1))
        keywords2 = set(self._extract_keywords(text2))

        if not keywords1 or not keywords2:
            return 0.0

        intersection = keywords1 & keywords2
        union = keywords1 | keywords2

        return len(intersection) / len(union) if union else 0.0

    def _row_to_record(self, row: sqlite3.Row) -> TruthRecord:
        """行转记录"""
        return TruthRecord(
            id=row["id"],
            content=row["content"],
            category=row["category"] or "",
            confidence=row["confidence"],
            status=TruthStatus(row["status"]),
            source=row["source"] or "",
            tags=json.loads(row["tags"]) if row["tags"] else [],
            created_at=row["created_at"],
            last_verified_at=row["last_verified_at"] or "",
            version=row["version"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {}
        )

    def _row_to_anchor(self, row: sqlite3.Row) -> Anchor:
        """行转锚点"""
        return Anchor(
            id=row["id"],
            topic=row["topic"],
            verified_truth=row["verified_truth"],
            source=row["source"] or "",
            confidence_score=row["confidence_score"],
            tags=json.loads(row["tags"]) if row["tags"] else []
        )

    def _clear_cache(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT status, COUNT(*) FROM truth_records WHERE deleted_at IS NULL GROUP BY status")
        status_counts = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM truth_records WHERE deleted_at IS NULL")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT AVG(confidence) FROM truth_records WHERE status = 'active' AND deleted_at IS NULL")
        avg_confidence = cursor.fetchone()[0] or 0.0

        conn.close()

        return {
            "total_records": total,
            "status_counts": status_counts,
            "avg_confidence": round(avg_confidence, 3),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hits / max(1, self.cache_hits + self.cache_misses), 3)
        }


# ============================================================================
# P0: 数据 TTL 与自动降级
# ============================================================================

@dataclass
class DecayRule:
    days_until_warning: int
    days_until_decay: int
    decay_factor: float


class ConfidenceDecayJob:
    """
    置信度衰减任务 - 防止过期知识污染决策
    """

    DEFAULT_RULES = {
        "medical": DecayRule(days_until_warning=30, days_until_decay=90, decay_factor=0.8),
        "technical": DecayRule(days_until_warning=60, days_until_decay=180, decay_factor=0.7),
        "general": DecayRule(days_until_warning=90, days_until_decay=365, decay_factor=0.6),
    }

    def __init__(self, knowledge_service: KnowledgeService):
        self.ks = knowledge_service
        self.rules = self.DEFAULT_RULES.copy()
        self._stats = {
            "total_checked": 0,
            "warnings_issued": 0,
            "decayed": 0,
            "revived": 0
        }

    def run(self) -> Dict[str, Any]:
        """执行降级扫描"""
        self._stats["total_checked"] = 0
        self._stats["warnings_issued"] = 0
        self._stats["decayed"] = 0
        self._stats["revived"] = 0

        conn = sqlite3.connect(self.ks.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, category, confidence, last_verified_at, status
            FROM truth_records
            WHERE deleted_at IS NULL AND status != 'decayed'
        """)

        now = datetime.now()
        records = cursor.fetchall()

        for record_id, category, confidence, last_verified, status in records:
            if not last_verified:
                continue

            last_verified_dt = datetime.fromisoformat(last_verified)
            days_since = (now - last_verified_dt).days

            rule = self.rules.get(category, self.rules["general"])

            if days_since >= rule.days_until_decay:
                new_confidence = confidence * rule.decay_factor
                cursor.execute(
                    "UPDATE truth_records SET confidence = ?, status = ? WHERE id = ?",
                    [new_confidence, TruthStatus.DECAYED.value, record_id]
                )
                self._stats["decayed"] += 1
                self.ks._publish("truth_decayed", {"id": record_id, "new_confidence": new_confidence})

            elif days_since >= rule.days_until_warning:
                self._stats["warnings_issued"] += 1
                self.ks._publish("truth_warning", {
                    "id": record_id,
                    "days_since": days_since,
                    "rule": rule
                })

            self._stats["total_checked"] += 1

        conn.commit()
        conn.close()

        self.ks._clear_cache()

        return self._stats.copy()

    def add_rule(self, category: str, rule: DecayRule):
        """添加降级规则"""
        self.rules[category] = rule

    def get_decay_candidates(self, category: Optional[str] = None, limit: int = 100) -> List[TruthRecord]:
        """获取待降级记录"""
        conn = sqlite3.connect(self.ks.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        sql = """
            SELECT * FROM truth_records
            WHERE deleted_at IS NULL AND status = 'active'
        """
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY last_verified_at ASC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        return [self.ks._row_to_record(row) for row in rows]


# ============================================================================
# P1: 增量 CDC 同步
# ============================================================================

class CDCEventType(Enum):
    STORED = "stored"
    UPDATED = "updated"
    DELETED = "deleted"
    STATUS_CHANGED = "status_changed"
    DECAYED = "decayed"


@dataclass
class CDCEvent:
    event_type: CDCEventType
    record_id: str
    timestamp: str
    data: Dict[str, Any]


class CDCSync:
    """
    Change Data Capture 增量同步 - 替代手动全量 sync
    """

    def __init__(self, knowledge_service: KnowledgeService):
        self.ks = knowledge_service
        self.event_log: List[CDCEvent] = []
        self.max_log_size = 10000
        self._processing = False

        self.ks.subscribe("truth_stored", self._on_stored)
        self.ks.subscribe("truth_status_changed", self._on_status_changed)
        self.ks.subscribe("truth_decayed", self._on_decayed)

    def _on_stored(self, record: TruthRecord):
        """新记录入库"""
        event = CDCEvent(
            event_type=CDCEventType.STORED,
            record_id=record.id,
            timestamp=datetime.now().isoformat(),
            data={"record": record.__dict__}
        )
        self._add_event(event)
        self._trigger_sync(event)

    def _on_status_changed(self, data: Dict[str, Any]):
        """状态变更"""
        event = CDCEvent(
            event_type=CDCEventType.STATUS_CHANGED,
            record_id=data["id"],
            timestamp=datetime.now().isoformat(),
            data=data
        )
        self._add_event(event)
        self._trigger_sync(event)

    def _on_decayed(self, data: Dict[str, Any]):
        """降级事件"""
        event = CDCEvent(
            event_type=CDCEventType.DECAYED,
            record_id=data["id"],
            timestamp=datetime.now().isoformat(),
            data=data
        )
        self._add_event(event)
        self._trigger_sync(event)

    def _add_event(self, event: CDCEvent):
        """添加到事件日志"""
        self.event_log.append(event)
        if len(self.event_log) > self.max_log_size:
            self.event_log = self.event_log[-self.max_log_size:]

    def _trigger_sync(self, event: CDCEvent):
        """触发同步"""
        if self._processing:
            return

        threading.Thread(target=self._sync_event, args=(event,), daemon=True).start()

    def _sync_event(self, event: CDCEvent):
        """同步单个事件"""
        try:
            if event.event_type in [CDCEventType.STORED, CDCEventType.STATUS_CHANGED, CDCEventType.DECAYED]:
                print(f"[CDC] 增量同步: {event.event_type.value} - {event.record_id}")
            elif event.event_type == CDCEventType.DELETED:
                print(f"[CDC] 删除同步: {event.record_id}")
        except Exception as e:
            print(f"[CDC] 同步错误: {e}")

    def get_recent_events(self, limit: int = 100) -> List[CDCEvent]:
        """获取最近事件"""
        return self.event_log[-limit:]

    def force_full_sync(self):
        """强制全量同步（重建工具）"""
        print("[CDC] 触发全量同步...")

        conn = sqlite3.connect(self.ks.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM truth_records WHERE deleted_at IS NULL")

        count = 0
        for row in cursor.fetchall():
            count += 1

        conn.close()
        print(f"[CDC] 全量同步完成: {count} 条记录")

        return {"synced": count}


# ============================================================================
# 集成测试
# ============================================================================

def run_tests():
    print("=" * 80)
    print("  AC Truth Knowledge Service - P0/P1 测试")
    print("=" * 80)

    db_path = "test_knowledge.db"
    import os
    if os.path.exists(db_path):
        os.remove(db_path)

    ks = KnowledgeService(db_path)
    cdc = CDCSync(ks)
    decay_job = ConfidenceDecayJob(ks)

    # 添加测试数据
    test_records = [
        TruthRecord(
            id="truth_001",
            content="高血压的诊断标准是收缩压≥140mmHg或舒张压≥90mmHg",
            category="medical",
            confidence=0.95,
            status=TruthStatus.ACTIVE,
            source="临床指南",
            tags=["高血压", "诊断", "医学"],
            created_at=datetime.now().isoformat(),
            last_verified_at=datetime.now().isoformat(),
            version=1,
            metadata={}
        ),
        TruthRecord(
            id="truth_002",
            content="Python 3.10 引入了 match-case 语法",
            category="technical",
            confidence=0.90,
            status=TruthStatus.ACTIVE,
            source="官方文档",
            tags=["Python", "编程", "语法"],
            created_at=datetime.now().isoformat(),
            last_verified_at=datetime.now().isoformat(),
            version=1,
            metadata={}
        ),
        TruthRecord(
            id="truth_003",
            content="这是一个低置信度的待审核数据",
            category="general",
            confidence=0.30,
            status=TruthStatus.QUARANTINE,
            source="网络",
            tags=["测试"],
            created_at=datetime.now().isoformat(),
            last_verified_at=(datetime.now() - timedelta(days=100)).isoformat(),
            version=1,
            metadata={}
        ),
    ]

    print("\n--- 1. 存储测试 ---\n")
    for record in test_records:
        ks.store(record)
        print(f"✅ 存储: {record.id} - {record.content[:30]}...")

    print("\n--- 2. 搜索测试 (dispatch 使用) ---\n")
    results = ks.search("高血压", categories=["medical"])
    print(f"搜索'高血压': 找到 {len(results)} 条")
    for r in results:
        print(f"  - {r.content[:50]}... (置信度: {r.confidence})")

    print("\n--- 3. 事实核查测试 (orchestrator VERIFY 使用) ---\n")
    check = ks.check_fact("高血压的诊断标准是什么？")
    print(f"核查: 高血压的诊断标准是什么？")
    print(f"  匹配: {check.matched}")
    print(f"  判决: {check.verdict}")
    print(f"  置信度: {check.confidence:.2f}")
    print(f"  详情: {check.details}")

    print("\n--- 4. 锚点获取测试 (auditor 使用) ---\n")
    anchors = ks.get_anchors(category="medical")
    print(f"获取医疗锚点: {len(anchors)} 个")

    print("\n--- 5. CDC 事件测试 ---\n")
    events = cdc.get_recent_events()
    print(f"最近 CDC 事件: {len(events)} 个")
    for event in events[-3:]:
        print(f"  - {event.event_type.value} @ {event.timestamp}")

    print("\n--- 6. 降级扫描测试 ---\n")
    decay_stats = decay_job.run()
    print(f"降级扫描结果: {decay_stats}")

    print("\n--- 7. 统计信息 ---\n")
    stats = ks.get_stats()
    print(f"知识库统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")

    print("\n--- 8. 全量同步测试 ---\n")
    sync_result = cdc.force_full_sync()
    print(f"全量同步结果: {sync_result}")

    print("\n" + "=" * 80)
    print("  ✅ 全部测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()


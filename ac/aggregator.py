"""
跨对话全自动聚合引擎
聚合源：Opencode交接文件 / Trae操作日志 / AC治理事件 / 猎鬼档案
输出：统一时间轴视图
"""

import os
import json
import re
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional


AC_DIR = Path(__file__).resolve().parent
HANDOFF_DIR = AC_DIR / "00-AC" / "handoffs"
EVIDENCE_DIR = AC_DIR / "00-AC" / "evidence"
DB_PATH = AC_DIR / "ac_platform.db"


class CrossSessionAggregator:
    """跨对话聚合器"""

    def __init__(self, handoff_dir: Path = None, evidence_dir: Path = None, db_path: str = None):
        self.handoff_dir = handoff_dir or HANDOFF_DIR
        self.evidence_dir = evidence_dir or EVIDENCE_DIR
        self.db_path = db_path or str(DB_PATH)

    def aggregate_all(self, date: str = None) -> Dict:
        """
        聚合所有来源，生成统一时间轴
        date: 日期字符串 YYYY-MM-DD，不传则今天
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        timeline = []

        timeline.extend(self._from_handoffs(date))
        timeline.extend(self._from_governance_events(date))
        timeline.extend(self._from_schedule_events(date))
        timeline.extend(self._from_guard_events(date))
        timeline.extend(self._from_evidence(date))

        timeline.sort(key=lambda x: x.get("timestamp", ""))

        content_hash = hashlib.sha256(
            json.dumps(timeline, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        source_counts = {}
        for e in timeline:
            src = e.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        return {
            "date": date,
            "total_events": len(timeline),
            "sources": source_counts,
            "timeline": timeline,
            "hash": content_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _from_handoffs(self, date: str) -> List[Dict]:
        """从 Opencode 交接文件提取事件"""
        events = []
        handoff_file = self.handoff_dir / f"{date}.md"

        if not handoff_file.exists():
            return events

        try:
            content = handoff_file.read_text(encoding="utf-8")
        except Exception:
            return events

        sections = {"architecture_decision": [], "ghost_update": [], "file_change": [], "tomorrow_task": []}
        current_section = None

        for line in content.split("\n"):
            line_stripped = line.strip()
            if "今日架构决策" in line or "architecture" in line.lower():
                current_section = "architecture_decision"
                continue
            elif "猎鬼更新" in line or "ghost" in line.lower():
                current_section = "ghost_update"
                continue
            elif "文件变更" in line or "file change" in line.lower():
                current_section = "file_change"
                continue
            elif "明日起始任务" in line or "tomorrow" in line.lower() or "起始任务" in line:
                current_section = "tomorrow_task"
                continue

            if current_section and line_stripped.startswith("-"):
                item = line_stripped[1:].strip()
                if item:
                    sections[current_section].append(item)

        icon_map = {
            "architecture_decision": "\U0001F4D0",
            "ghost_update": "\U0001F47B",
            "file_change": "\U0001F4C4",
            "tomorrow_task": "\U0001F3AF",
        }
        type_map = {
            "architecture_decision": "architecture_decision",
            "ghost_update": "ghost_hunt_update",
            "file_change": "file_change",
            "tomorrow_task": "tomorrow_task",
        }

        offset = 0
        for section_key, items in sections.items():
            for i, item in enumerate(items):
                hour = 8 + offset % 16
                events.append({
                    "timestamp": f"{date}T{hour:02d}:{(i * 5) % 60:02d}:00",
                    "source": "opencode",
                    "type": type_map.get(section_key, section_key),
                    "summary": item,
                    "reference": f"{date}.md",
                    "icon": icon_map.get(section_key, "\U0001F4CC"),
                })
                offset += 1

        if events:
            events.append({
                "timestamp": f"{date}T23:59:00",
                "source": "opencode",
                "type": "daily_handoff",
                "summary": "日终交接归档完成",
                "reference": f"{date}.md",
                "icon": "\U0001F4E6",
            })

        return events

    def _from_governance_events(self, date: str) -> List[Dict]:
        """从治理日志表提取事件"""
        events = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, session_id, command, input_preview, passed, corrected, encoding_sanitized, created_at "
                "FROM ac_governance_log WHERE date(created_at) = ? ORDER BY created_at",
                (date,),
            )
            rows = cursor.fetchall()
            conn.close()

            icon_map = {True: "\U0001F7E2", False: "\U0001F534", "corrected": "\U0001F7E0"}

            for row in rows:
                passed = bool(row["passed"])
                corrected = bool(row["corrected"])
                status = "passed" if passed else ("corrected" if corrected else "blocked")
                icon = icon_map["corrected"] if corrected else icon_map[passed]

                events.append({
                    "timestamp": row["created_at"],
                    "source": "ac_governance",
                    "type": "governance_check",
                    "summary": f"[{row['command']}] {row['input_preview'][:60]} — {status}",
                    "reference": f"gov_log:{row['id'][:8]}",
                    "icon": icon,
                    "detail": {
                        "command": row["command"],
                        "passed": passed,
                        "corrected": corrected,
                        "encoding_sanitized": bool(row["encoding_sanitized"]),
                    },
                })
        except sqlite3.OperationalError:
            pass
        except Exception:
            pass

        return events

    def _from_schedule_events(self, date: str) -> List[Dict]:
        """从调度日志提取事件（Trae 调度记录）"""
        events = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT log_id, session_id, query_preview, matched_expert, response_mode, created_at "
                "FROM ac_schedule_log WHERE date(created_at) = ? ORDER BY created_at",
                (date,),
            )
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                events.append({
                    "timestamp": row["created_at"],
                    "source": "trae",
                    "type": "dispatch_event",
                    "summary": f"调度: {row['query_preview'][:60]} → {row['matched_expert']} ({row['response_mode']})",
                    "reference": f"schedule:{row['log_id'][:8]}",
                    "icon": "\U0001F4E1",
                })
        except sqlite3.OperationalError:
            pass
        except Exception:
            pass

        return events

    def _from_guard_events(self, date: str) -> List[Dict]:
        """从守卫日志提取事件"""
        events = []
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, guard, action, detail, created_at "
                "FROM ac_guard_log WHERE date(created_at) = ? ORDER BY created_at",
                (date,),
            )
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                summary = f"守卫 [{row['guard']}]: {row['action']}"
                if row['detail']:
                    summary += f" — {row['detail'][:60]}"
                events.append({
                    "timestamp": row["created_at"],
                    "source": "trae",
                    "type": "guard_event",
                    "summary": summary,
                    "reference": f"guard:{row['id']}",
                    "icon": "\U0001F6E1",
                })
        except sqlite3.OperationalError:
            pass
        except Exception:
            pass

        return events

    def _from_evidence(self, date: str) -> List[Dict]:
        """从猎鬼档案提取事件"""
        events = []
        if not self.evidence_dir.is_dir():
            return events

        for entry in sorted(self.evidence_dir.rglob("*")):
            if entry.is_file() and entry.suffix in (".txt", ".md", ".json"):
                try:
                    mtime = datetime.fromtimestamp(entry.stat().st_mtime, tz=timezone.utc)
                    mtime_str = mtime.isoformat()
                    if not mtime_str.startswith(date):
                        continue

                    content = entry.read_text(encoding="utf-8", errors="replace")
                    preview = content[:200].replace("\n", " ").strip()
                    if len(content) > 200:
                        preview += "..."

                    events.append({
                        "timestamp": mtime_str,
                        "source": "ghost_hunt",
                        "type": "evidence_file",
                        "summary": f"猎鬼档案: {entry.name} — {preview}",
                        "reference": str(entry.relative_to(self.evidence_dir.parent)),
                        "icon": "\U0001F47B",
                    })
                except Exception:
                    pass

        return events

    def get_date_range(self) -> List[str]:
        """获取所有有数据的日期列表（从 handoff 文件反向推导）"""
        dates = set()
        if self.handoff_dir.is_dir():
            for f in self.handoff_dir.glob("*.md"):
                name = f.stem
                if re.match(r"^\d{4}-\d{2}-\d{2}$", name):
                    dates.add(name)
        return sorted(dates)

    def get_ai_tasks(self) -> Dict:
        """从 handoff 文件和 task_graphs 表提取所有 AI 任务及其状态

        AI 任务格式约定:
          - [x] task_name → done
          - [~] task_name → in_progress
          - [!] task_name → blocked
          - [ ] task_name → pending
        """
        tasks = []

        if self.handoff_dir.exists():
            for f in sorted(self.handoff_dir.glob("*.md"), reverse=True):
                content = f.read_text(encoding="utf-8")
                for status, pattern in [
                    ("done", r'-\s*\[x\]\s*(.+)'),
                    ("in_progress", r'-\s*\[~\]\s*(.+)'),
                    ("blocked", r'-\s*\[!\]\s*(.+)'),
                    ("pending", r'-\s*\[\s*\]\s*(.+)'),
                ]:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for task in matches:
                        tasks.append({
                            "task": task.strip(),
                            "status": status,
                            "source_file": f.name,
                            "source": "handoff",
                            "ai": "opencode",
                        })

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT description, status, assigned_agent, created_at "
                "FROM task_graphs ORDER BY created_at DESC LIMIT 100"
            )
            rows = cursor.fetchall()
            conn.close()

            for row in rows:
                tasks.append({
                    "task": row[0],
                    "status": row[1] or "unknown",
                    "assigned_ai": row[2] or "unassigned",
                    "created_at": row[3],
                    "source": "task_graph",
                    "ai": row[2] or "unassigned",
                })
        except Exception:
            pass

        ai_stats: dict[str, dict[str, int]] = {}
        for t in tasks:
            ai = t.get("ai") or t.get("assigned_ai") or "unknown"
            if ai not in ai_stats:
                ai_stats[ai] = {"total": 0, "done": 0, "pending": 0,
                                "blocked": 0, "in_progress": 0}
            ai_stats[ai]["total"] += 1
            status = t["status"]
            if status in ai_stats[ai]:
                ai_stats[ai][status] += 1

        return {
            "total_tasks": len(tasks),
            "by_status": {
                "done": sum(1 for t in tasks if t["status"] == "done"),
                "pending": sum(1 for t in tasks if t["status"] == "pending"),
                "in_progress": sum(1 for t in tasks if t["status"] == "in_progress"),
                "blocked": sum(1 for t in tasks if t["status"] == "blocked"),
                "unknown": sum(1 for t in tasks if t["status"] == "unknown"),
            },
            "by_ai": ai_stats,
            "tasks": tasks,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def aggregate_range(self, start_date: str, end_date: str = None) -> Dict:
        """聚合指定日期范围"""
        end_date = end_date or datetime.now().strftime("%Y-%m-%d")

        all_timeline = []
        for date in self.get_date_range():
            if start_date <= date <= end_date:
                result = self.aggregate_all(date)
                all_timeline.extend(result["timeline"])

        all_timeline.sort(key=lambda x: x.get("timestamp", ""))

        content_hash = hashlib.sha256(
            json.dumps(all_timeline, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
        ).hexdigest()

        source_counts = {}
        for e in all_timeline:
            src = e.get("source", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_events": len(all_timeline),
            "sources": source_counts,
            "timeline": all_timeline,
            "hash": content_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_progress(self) -> Dict:
        """
       获取多对话任务进度
       从 handoff 文件和 task_graphs 表提取待办/已完成任务
        """
        tasks = []

        # 源1：从 handoff 文件提取任务
        if self.handoff_dir.exists():
            import re
            for f in sorted(self.handoff_dir.glob("*.md")):
                content = f.read_text(encoding="utf-8")

                for status, pattern in [
                    ("done", r'-\s*\[x\]\s*(.+)'),
                    ("pending", r'-\s*\[\s*\]\s*(.+)'),
                    ("in_progress", r'-\s*\[~\]\s*(.+)'),
                ]:
                    for task in re.findall(pattern, content):
                        tasks.append({
                            "task": task.strip(),
                            "status": status,
                            "date": f.stem,
                            "source": "opencode"
                        })

        # 源2：从 task_graphs 表提取任务
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT description, status FROM task_graphs WHERE status != 'completed' ORDER BY created_at DESC LIMIT 50"
            )
            for row in cursor.fetchall():
                tasks.append({
                    "task": row[0],
                    "status": row[1],
                    "date": "today",
                    "source": "trae"
                })
            conn.close()
        except:
            pass

        return {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t["status"] == "pending"),
            "done": sum(1 for t in tasks if t["status"] == "done"),
            "in_progress": sum(1 for t in tasks if t["status"] == "in_progress"),
            "tasks": tasks,
            "generated_at": datetime.now().isoformat()
        }


def get_aggregator(**kwargs) -> CrossSessionAggregator:
    return CrossSessionAggregator(**kwargs)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="跨对话聚合引擎")
    parser.add_argument("--date", "-d", default=None, help="日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--start", default=None, help="起始日期")
    parser.add_argument("--end", default=None, help="结束日期")
    parser.add_argument("--format", "-f", choices=["json", "text"], default="json", help="输出格式")
    parser.add_argument("--list-dates", action="store_true", help="列出所有有数据的日期")

    args = parser.parse_args()
    agg = CrossSessionAggregator()

    if args.list_dates:
        dates = agg.get_date_range()
        print(json.dumps(dates, ensure_ascii=False, indent=2))
        return

    if args.start:
        result = agg.aggregate_range(args.start, args.end)
    else:
        result = agg.aggregate_all(args.date)

    if args.format == "text":
        _print_timeline_text(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def _print_timeline_text(result: Dict):
    print(f"=== 聚合时间轴 · {result['date']} ===")
    print(f"事件总数: {result['total_events']}")
    print(f"来源分布: {json.dumps(result['sources'], ensure_ascii=False)}")
    print(f"完整性哈希: {result['hash'][:16]}...")
    print()
    for event in result.get("timeline", []):
        ts = event["timestamp"]
        icon = event.get("icon", "?")
        summary = event["summary"]
        src = event["source"]
        print(f"  {icon} [{ts}] ({src}) {summary}")


if __name__ == "__main__":
    main()

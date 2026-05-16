"""MemoryManager · 向量数据库记忆管理器"""

import asyncio
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

# 尝试导入ChromaDB
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# ==================== 数据结构 ====================

@dataclass
class Experience:
    """经验记录"""
    experience_id: str
    task_type: str
    goal: str
    summary: str
    success: bool
    duration: float
    timestamp: float = field(default_factory=lambda: time.time())
    solution: Optional[str] = None
    failure_reason: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MemoryRetrieval:
    """记忆检索结果"""
    experience: Experience
    similarity: float

# ==================== 记忆管理器核心 ====================

class MemoryManager:
    """记忆管理器"""
    
    def __init__(self, db_path: str = "./ac_memory"):
        """
        初始化记忆管理器
        
        Args:
            db_path: 向量数据库存储路径
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.collection = None
        
        if CHROMADB_AVAILABLE:
            self._init_chromadb()
    
    def _init_chromadb(self):
        """初始化ChromaDB客户端（使用新API）"""
        try:
            # 使用ChromaDB新API
            self.client = chromadb.PersistentClient(path=str(self.db_path))
            
            # 获取或创建经验集合
            self.collection = self.client.get_or_create_collection(
                name="experiences",
                metadata={"hnsw:space": "cosine"}
            )
            
            print(f"[AC] 向量数据库初始化成功: {self.db_path}")
        except Exception as e:
            print(f"[AC] 向量数据库初始化失败: {e}")
            self.client = None
            self.collection = None
    
    async def store_experience(self, experience: Experience) -> bool:
        """
        存储经验到向量数据库
        
        Args:
            experience: 经验记录
            
        Returns:
            bool: 是否存储成功
        """
        if not CHROMADB_AVAILABLE or not self.collection:
            print("[WARN] ChromaDB不可用，跳过经验存储")
            return False
        
        try:
            # 构建嵌入文本
            embedding_text = f"""
            任务类型：{experience.task_type}
            目标：{experience.goal}
            摘要：{experience.summary}
            解决方案：{experience.solution or ''}
            失败原因：{experience.failure_reason or ''}
            """
            
            # 构建元数据
            metadata = {
                "experience_id": experience.experience_id,
                "task_type": experience.task_type,
                "goal": experience.goal,
                "success": experience.success,
                "duration": experience.duration,
                "timestamp": experience.timestamp,
                "solution": experience.solution or "",
                "failure_reason": experience.failure_reason or "",
                "metrics": json.dumps(experience.metrics)
            }
            
            # 添加到向量数据库
            self.collection.add(
                documents=[embedding_text.strip()],
                metadatas=[metadata],
                ids=[experience.experience_id]
            )
            
            print(f"[OK] 经验已存储: {experience.experience_id}")
            return True
        except Exception as e:
            print(f"[FAIL] 经验存储失败: {e}")
            return False
    
    async def retrieve_similar(self, query: str, top_k: int = 3) -> List[MemoryRetrieval]:
        """
        检索相似任务经验
        
        Args:
            query: 查询文本
            top_k: 返回前k个相似结果
            
        Returns:
            List[MemoryRetrieval]: 相似经验列表
        """
        if not CHROMADB_AVAILABLE or not self.collection:
            print("[WARN] ChromaDB不可用，跳过经验检索")
            return []
        
        try:
            # 执行向量检索
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where={"success": True}  # 优先检索成功经验
            )
            
            # 转换结果
            retrievals = []
            for i in range(len(results["ids"][0])):
                metadata = results["metadatas"][0][i]
                similarity = 1.0 - results["distances"][0][i]  # 距离转相似度
                
                experience = Experience(
                    experience_id=metadata["experience_id"],
                    task_type=metadata["task_type"],
                    goal=metadata["goal"],
                    summary=results["documents"][0][i],
                    success=metadata["success"],
                    duration=metadata["duration"],
                    timestamp=metadata["timestamp"],
                    solution=metadata["solution"],
                    failure_reason=metadata["failure_reason"],
                    metrics=json.loads(metadata.get("metrics", "{}"))
                )
                
                retrievals.append(MemoryRetrieval(
                    experience=experience,
                    similarity=similarity
                ))
            
            # 按相似度排序
            retrievals.sort(key=lambda x: x.similarity, reverse=True)
            
            print(f"[OK] 检索到 {len(retrievals)} 条相似经验")
            return retrievals
        except Exception as e:
            print(f"[FAIL] 经验检索失败: {e}")
            return []
    
    async def get_experience_by_id(self, experience_id: str) -> Optional[Experience]:
        """
        根据ID获取经验
        
        Args:
            experience_id: 经验ID
            
        Returns:
            Optional[Experience]: 经验记录
        """
        if not CHROMADB_AVAILABLE or not self.collection:
            return None
        
        try:
            results = self.collection.get(ids=[experience_id])
            
            if results and results["ids"]:
                metadata = results["metadatas"][0][0]
                return Experience(
                    experience_id=metadata["experience_id"],
                    task_type=metadata["task_type"],
                    goal=metadata["goal"],
                    summary=results["documents"][0][0],
                    success=metadata["success"],
                    duration=metadata["duration"],
                    timestamp=metadata["timestamp"],
                    solution=metadata["solution"],
                    failure_reason=metadata["failure_reason"],
                    metrics=json.loads(metadata.get("metrics", "{}"))
                )
            return None
        except Exception as e:
            print(f"[FAIL] 获取经验失败: {e}")
            return None
    
    async def delete_experience(self, experience_id: str) -> bool:
        """
        删除经验
        
        Args:
            experience_id: 经验ID
            
        Returns:
            bool: 是否删除成功
        """
        if not CHROMADB_AVAILABLE or not self.collection:
            return False
        
        try:
            self.collection.delete(ids=[experience_id])
            print(f"[OK] 经验已删除: {experience_id}")
            return True
        except Exception as e:
            print(f"[FAIL] 删除经验失败: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not CHROMADB_AVAILABLE or not self.collection:
            return {"count": 0, "available": False}
        
        try:
            count = self.collection.count()
            return {
                "count": count,
                "available": True,
                "path": str(self.db_path)
            }
        except Exception as e:
            return {"count": 0, "available": False, "error": str(e)}

# ==================== CLI测试入口 ====================

async def main():
    """测试记忆管理器"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MemoryManager · 记忆管理器")
    subparsers = parser.add_subparsers(dest="command")
    
    # store命令
    store_parser = subparsers.add_parser("store", help="存储经验")
    store_parser.add_argument("--task-type", required=True, help="任务类型")
    store_parser.add_argument("--goal", required=True, help="任务目标")
    store_parser.add_argument("--summary", required=True, help="摘要")
    store_parser.add_argument("--success", action="store_true", help="是否成功")
    store_parser.add_argument("--duration", type=float, default=0.0, help="耗时")
    store_parser.add_argument("--solution", help="解决方案")
    store_parser.add_argument("--failure-reason", help="失败原因")
    
    # retrieve命令
    retrieve_parser = subparsers.add_parser("retrieve", help="检索相似经验")
    retrieve_parser.add_argument("--query", required=True, help="查询文本")
    retrieve_parser.add_argument("--top-k", type=int, default=3, help="返回数量")
    
    # stats命令
    stats_parser = subparsers.add_parser("stats", help="获取统计信息")
    
    args = parser.parse_args()
    
    manager = MemoryManager()
    
    if args.command == "store":
        experience = Experience(
            experience_id=f"exp_{int(time.time())}",
            task_type=args.task_type,
            goal=args.goal,
            summary=args.summary,
            success=args.success,
            duration=args.duration,
            solution=args.solution,
            failure_reason=args.failure_reason
        )
        await manager.store_experience(experience)
    
    elif args.command == "retrieve":
        results = await manager.retrieve_similar(args.query, args.top_k)
        print(f"\n[BOOK] 检索结果 ({len(results)}条):")
        for i, retrieval in enumerate(results, 1):
            exp = retrieval.experience
            print(f"\n{i}. [相似度: {retrieval.similarity:.2f}]")
            print(f"   ID: {exp.experience_id}")
            print(f"   类型: {exp.task_type}")
            print(f"   目标: {exp.goal}")
            print(f"   摘要: {exp.summary[:50]}...")
            print(f"   成功: {'是' if exp.success else '否'}")
            print(f"   耗时: {exp.duration:.1f}秒")
    
    elif args.command == "stats":
        stats = manager.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
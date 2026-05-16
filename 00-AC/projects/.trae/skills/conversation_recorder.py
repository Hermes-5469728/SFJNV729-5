"""
Conversation Recorder - 对话记录器
自动将对话内容保存到 opencode 仓库

功能：
1. 自动记录每一条对话（用户输入 + AI 响应）
2. 按日期分组存储
3. 支持多种输出格式（MD/TXT/JSON）
4. 自动同步到本地文件

OpenCode Hooks:
  /conversation list           # 列出对话记录
  /conversation view <date>    # 查看指定日期的对话
  /conversation export <date>  # 导出对话记录
  /conversation clear          # 清空对话记录（需授权）
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any
from loguru import logger

class ConversationRecorder:
    """对话记录器"""
    
    def __init__(self, records_dir: str = None):
        self.records_dir = records_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'conversation_records'
        )
        os.makedirs(self.records_dir, exist_ok=True)
        logger.info(f"对话记录器初始化完成，存储目录: {self.records_dir}")
    
    def _get_today_file(self) -> str:
        """获取今日对话记录文件路径"""
        today = datetime.now().strftime('%Y-%m-%d')
        return os.path.join(self.records_dir, f'conversation_{today}.json')
    
    def record_conversation(self, user_input: str, ai_response: str, metadata: Dict[str, Any] = None):
        """
        记录对话
        
        :param user_input: 用户输入
        :param ai_response: AI 响应
        :param metadata: 元数据（可选）
        """
        record = {
            'timestamp': datetime.now().isoformat(),
            'user_input': user_input,
            'ai_response': ai_response,
            'metadata': metadata or {}
        }
        
        # 读取现有记录
        records = self._load_records()
        
        # 添加新记录
        records.append(record)
        
        # 保存
        self._save_records(records)
        
        logger.info(f"对话记录已保存，当前记录数: {len(records)}")
    
    def _load_records(self) -> List[Dict[str, Any]]:
        """加载今日对话记录"""
        file_path = self._get_today_file()
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载对话记录失败: {e}")
                return []
        return []
    
    def _save_records(self, records: List[Dict[str, Any]]):
        """保存对话记录"""
        file_path = self._get_today_file()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    
    def get_today_records(self) -> List[Dict[str, Any]]:
        """获取今日对话记录"""
        return self._load_records()
    
    def get_records_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """
        获取指定日期的对话记录
        
        :param date_str: 日期字符串，格式 YYYY-MM-DD
        """
        file_path = os.path.join(self.records_dir, f'conversation_{date_str}.json')
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载指定日期对话记录失败: {e}")
                return []
        return []
    
    def list_record_dates(self) -> List[str]:
        """列出有记录的日期"""
        dates = []
        for filename in os.listdir(self.records_dir):
            if filename.startswith('conversation_') and filename.endswith('.json'):
                date_str = filename.replace('conversation_', '').replace('.json', '')
                dates.append(date_str)
        return sorted(dates, reverse=True)
    
    def export_to_markdown(self, date_str: str = None) -> str:
        """
        导出对话记录为 Markdown 格式
        
        :param date_str: 日期（默认今日）
        :return: Markdown 内容
        """
        if date_str:
            records = self.get_records_by_date(date_str)
            title = f"对话记录 - {date_str}"
        else:
            records = self.get_today_records()
            title = f"对话记录 - {datetime.now().strftime('%Y-%m-%d')}"
        
        if not records:
            return "# 无对话记录"
        
        md_lines = [
            f"# {title}",
            "",
            f"生成时间: {datetime.now().isoformat()}",
            f"对话数量: {len(records)}",
            "",
            "---"
        ]
        
        for i, record in enumerate(records, 1):
            md_lines.append(f"## 对话 {i}")
            md_lines.append(f"**时间**: {record['timestamp']}")
            md_lines.append("")
            md_lines.append("### 用户")
            md_lines.append(record['user_input'])
            md_lines.append("")
            md_lines.append("### AI")
            md_lines.append(record['ai_response'])
            md_lines.append("")
            
            if record.get('metadata'):
                md_lines.append("### 元数据")
                for key, value in record['metadata'].items():
                    md_lines.append(f"- {key}: {value}")
                md_lines.append("")
            
            md_lines.append("---")
        
        return '\n'.join(md_lines)
    
    def save_markdown_export(self, date_str: str = None) -> str:
        """
        导出对话记录为 Markdown 文件
        
        :param date_str: 日期（默认今日）
        :return: 文件路径
        """
        if date_str:
            records = self.get_records_by_date(date_str)
            filename = f'conversation_{date_str}.md'
        else:
            records = self.get_today_records()
            filename = f'conversation_{datetime.now().strftime("%Y-%m-%d")}.md'
        
        if not records:
            return "无对话记录可导出"
        
        md_content = self.export_to_markdown(date_str)
        file_path = os.path.join(self.records_dir, filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        logger.info(f"对话记录已导出为 Markdown: {file_path}")
        return file_path
    
    def clear_records(self, date_str: str = None) -> bool:
        """
        清空对话记录
        
        :param date_str: 日期（默认清空所有）
        :return: 是否成功
        """
        if date_str:
            file_path = os.path.join(self.records_dir, f'conversation_{date_str}.json')
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已清空 {date_str} 的对话记录")
                return True
            return False
        else:
            # 清空所有记录
            for filename in os.listdir(self.records_dir):
                if filename.startswith('conversation_'):
                    os.remove(os.path.join(self.records_dir, filename))
            logger.info("已清空所有对话记录")
            return True
    
    def get_status(self) -> Dict[str, Any]:
        """获取记录器状态"""
        dates = self.list_record_dates()
        total_records = 0
        
        for date_str in dates:
            records = self.get_records_by_date(date_str)
            total_records += len(records)
        
        return {
            'records_dir': self.records_dir,
            'dates_with_records': len(dates),
            'total_conversations': total_records,
            'available_dates': dates[:10]  # 最近10天
        }

# 创建全局记录器实例
_conversation_recorder = None

def get_conversation_recorder() -> ConversationRecorder:
    """获取对话记录器单例"""
    global _conversation_recorder
    if _conversation_recorder is None:
        _conversation_recorder = ConversationRecorder()
    return _conversation_recorder

# 便捷函数：记录对话
def record(user_input: str, ai_response: str, **kwargs):
    """记录对话的便捷函数"""
    recorder = get_conversation_recorder()
    recorder.record_conversation(user_input, ai_response, kwargs)

# 测试
if __name__ == "__main__":
    recorder = get_conversation_recorder()
    
    # 测试记录
    recorder.record_conversation(
        user_input="你好，这是一条测试消息",
        ai_response="你好！这是测试响应。",
        metadata={"test_mode": True}
    )
    
    # 查看状态
    status = recorder.get_status()
    print("记录器状态:")
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    # 导出 Markdown
    md_path = recorder.save_markdown_export()
    print(f"\nMarkdown 导出路径: {md_path}")
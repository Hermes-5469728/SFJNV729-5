"""API文档自动生成器"""

import os
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime


def extract_api_routes(module_path: str) -> List[Dict[str, Any]]:
    """从模块中提取API路由信息"""
    routes = []
    
    try:
        with open(module_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 简单的正则匹配提取路由
            import re
            route_pattern = r'@router\.(get|post|put|delete)\(["\'](.+?)["\']\)'
            matches = re.findall(route_pattern, content)
            
            for method, path in matches:
                routes.append({
                    'method': method.upper(),
                    'path': path,
                    'module': Path(module_path).stem
                })
    except Exception as e:
        print(f"Error reading {module_path}: {e}")
    
    return routes


def generate_api_docs() -> str:
    """生成API文档Markdown"""
    routes = []
    
    # 扫描所有模块的API文件
    api_files = list(Path('src').rglob('*api.py'))
    for api_file in api_files:
        routes.extend(extract_api_routes(str(api_file)))
    
    # 按模块分组
    modules: Dict[str, List[Dict[str, Any]]] = {}
    for route in routes:
        module = route['module']
        if module not in modules:
            modules[module] = []
        modules[module].append(route)
    
    # 生成Markdown
    md = f"""---
title: "API文档"
date: {datetime.now().strftime('%Y-%m-%d')}
tags: [api, documentation]
category: 技术文档
---

# 🚀 API文档

> 本文档由系统自动生成，请勿手动修改

## 路由总览

| 模块 | 路由数量 |
|------|----------|
"""
    
    for module, module_routes in modules.items():
        md += f"| {module} | {len(module_routes)} |\n"
    
    md += "\n---\n\n"
    
    # 详细路由列表
    for module, module_routes in modules.items():
        md += f"## {module}\n\n"
        md += "| 方法 | 路径 |\n"
        md += "|------|------|\n"
        
        for route in module_routes:
            md += f"| {route['method']} | `{route['path']}` |\n"
        
        md += "\n"
    
    return md


def main():
    """主函数"""
    docs = generate_api_docs()
    
    # 确保文档目录存在
    docs_dir = Path('Hermes/Docs')
    docs_dir.mkdir(parents=True, exist_ok=True)
    
    # 写入文档
    docs_path = docs_dir / 'API文档.md'
    with open(docs_path, 'w', encoding='utf-8') as f:
        f.write(docs)
    
    print(f"API文档已更新: {docs_path}")


if __name__ == '__main__':
    main()

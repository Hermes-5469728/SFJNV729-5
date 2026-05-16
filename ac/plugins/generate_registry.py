"""读取 CSV → 生成 docker-compose + 注册表 + 启动脚本
用法: python plugins/generate_registry.py
输出: config/docker-compose.generated.yml + plugins/registry_generated.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "config" / "plugin_registry.csv"

def load_csv():
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r["port"] = int(r["port"]) if r["port"].strip() else 0
            rows.append(r)
    return rows

def gen_docker_compose(rows):
    """只为有端口且非 IDE/CLI 的项目生成 docker-compose 条目"""
    active = [r for r in rows if r["status"] == "active" and r["port"] > 0]
    standby = [r for r in rows if r["status"] == "standby" and r["port"] > 0]

    lines = ['# 由 plugins/generate_registry.py 自动生成，勿手动编辑',
             'version: "3.8"', '', 'services:']
    for r in active + standby:
        name = r["name"].lower().replace(" ", "-").replace("/", "-")
        lines.append(f'  {name}:')
        lines.append(f'    image: {name}:latest  # {r["url"] or "无镜像"}')
        lines.append(f'    ports:')
        lines.append(f'      - "{r["port"]}:{r["port"]}"')
        lines.append(f'    profiles:')
        lines.append(f'      - {r["status"]}  # {r["category"]} | {r["layer"]}')
        lines.append(f'    restart: unless-stopped')
        lines.append('')
    return '\n'.join(lines)

def gen_registry(rows):
    """生成 Python 注册表，每个项目一行"""
    lines = ['# 由 plugins/generate_registry.py 自动生成，勿手动编辑',
             '"""AC Plugin Registry — 所有 55+ 项目的注册入口"""',
             'from plugins.base import ACPlugin, PluginStatus', '',
             'REGISTRY = {', '']
    for r in rows:
        port = f'port={r["port"]}, ' if r["port"] else ''
        url = f'url="{r["url"]}", ' if r["url"] else ''
        lines.append(
            f'    "{r["name"]}": ACPlugin('
            f'name="{r["name"]}", {port}{url}'
            f'category="{r["category"]}", '
            f'status=PluginStatus.{r["status"].upper()}, '
            f'layer="{r["layer"]}"),'
        )
    lines.extend(['', '}', '',
                  'def list_active():',
                  '    return {k:v for k,v in REGISTRY.items() if v.status == PluginStatus.ACTIVE}',
                  '',
                  'def list_by_layer(layer):',
                  '    return {k:v for k,v in REGISTRY.items() if v.layer == layer}',
                  '',
                  'def mount(name):',
                  '    p = REGISTRY.get(name)',
                  '    if not p: return f"插件 {name} 未注册"',
                  '    if p.status == PluginStatus.ACTIVE: return f"{name} 已活跃"',
                  '    return p.mount_cmd()',
                  '',
                  'def unmount(name):',
                  '    p = REGISTRY.get(name)',
                  '    if not p: return f"插件 {name} 未注册"',
                  '    if p.status != PluginStatus.ACTIVE: return f"{name} 未在运行"',
                  '    return p.unmount_cmd()',
                  '',
                  'def stats():',
                  '    active = sum(1 for v in REGISTRY.values() if v.status == PluginStatus.ACTIVE)',
                  '    standby = sum(1 for v in REGISTRY.values() if v.status == PluginStatus.STANDBY)',
                  '    return f"活跃 {active} | 待命 {standby} | 总计 {len(REGISTRY)}"',])
    return '\n'.join(lines)

def main():
    rows = load_csv()
    docker_txt = gen_docker_compose(rows)
    registry_txt = gen_registry(rows)

    out_dc = ROOT / "config" / "docker-compose.generated.yml"
    out_reg = ROOT / "plugins" / "registry_generated.py"

    out_dc.write_text(docker_txt, encoding="utf-8")
    out_reg.write_text(registry_txt, encoding="utf-8")

    active = sum(1 for r in rows if r["status"] == "active")
    standby = sum(1 for r in rows if r["status"] == "standby")
    print(f"[OK] {out_dc.name} ({active+standby} services)")
    print(f"[OK] {out_reg.name} (active={active}, standby={standby})")
    print(f"[OK] 活跃 {active} → 内存预估 < 8GB | 全量 standby {standby} → 按需挂载")

if __name__ == "__main__":
    main()

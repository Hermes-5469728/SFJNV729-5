"""原子性前端构建脚本"""
import shutil
import sys
from pathlib import Path

SITE_DIR = Path(__file__).resolve().parent / "site"
TMP_DIR = SITE_DIR / ".tmp"


def build():
    if not TMP_DIR.is_dir():
        print(f"[atomic] .tmp/ 不存在，跳过构建")
        return

    files = list(TMP_DIR.iterdir())
    if not files:
        print(f"[atomic] .tmp/ 为空，跳过构建")
        TMP_DIR.rmdir()
        return

    print(f"[atomic] 发现 {len(files)} 个文件，准备发布")

    for f in files:
        dest = SITE_DIR / f.name
        shutil.move(str(f), str(dest))
        print(f"  → {f.name}")

    TMP_DIR.rmdir()
    print(f"[atomic] 发布完成")


def clean():
    if TMP_DIR.is_dir():
        shutil.rmtree(str(TMP_DIR))
        print(f"[atomic] .tmp/ 已清理")
    else:
        print(f"[atomic] .tmp/ 不存在，无需清理")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"

    if cmd == "build":
        build()
    elif cmd == "clean":
        clean()
    else:
        print(f"用法: atomic_build.py [build|clean]")

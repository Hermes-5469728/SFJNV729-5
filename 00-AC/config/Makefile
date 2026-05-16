.PHONY: help install-dev install-pre-commit lint format type-check test build clean backup restore

help:
	@echo "AC Platform - 工程化命令"
	@echo ""
	@echo "可用命令:"
	@echo "  install-dev       安装开发依赖"
	@echo "  install-pre-commit 安装 pre-commit 钩子"
	@echo "  lint              运行代码检查 (ruff)"
	@echo "  format            格式化代码 (ruff format)"
	@echo "  type-check        类型检查 (mypy)"
	@echo "  test              运行测试 (pytest)"
	@echo "  build             构建项目"
	@echo "  clean             清理构建产物"
	@echo "  backup            创建项目备份"
	@echo "  restore           从备份恢复"
	@echo "  hooks            运行所有 pre-commit 钩子"

install-dev:
	@echo "安装开发依赖..."
	pip install -e .[dev]

install-pre-commit:
	@echo "安装 pre-commit 钩子..."
	pre-commit install
	pre-commit autoupdate

lint:
	@echo "运行代码检查..."
	ruff check . --exclude=.trae --exclude=__pycache__

format:
	@echo "格式化代码..."
	ruff format . --exclude=.trae --exclude=__pycache__

type-check:
	@echo "类型检查..."
	mypy . --ignore-missing-imports --exclude=.trae

test:
	@echo "运行测试..."
	pytest tests/ -v

build:
	@echo "构建项目..."
	python -m build

clean:
	@echo "清理构建产物..."
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

backup:
	@echo "创建项目备份..."
	python -m src.utils.backup_manager --backup

restore:
	@echo "从备份恢复..."
	python -m src.utils.backup_manager --restore

hooks:
	@echo "运行所有 pre-commit 钩子..."
	pre-commit run --all-files
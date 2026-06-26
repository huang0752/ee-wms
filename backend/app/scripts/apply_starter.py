"""Product Starter Preset 精简脚本。

默认只展示清单并要求输入 yes 才执行；使用 --dry-run 可只预览。
"""

from __future__ import annotations

import argparse
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config.path_conf import BASE_DIR

REPO_ROOT = BASE_DIR.parent


@dataclass(frozen=True)
class StarterPreset:
    name: str
    description: str
    remove_paths: tuple[str, ...]


PRESETS: dict[str, StarterPreset] = {
    "minimal": StarterPreset(
        name="minimal",
        description="保留核心后台底座，清理模板展示、演示模块和上传样例。",
        remove_paths=(
            "frontend/web/src/views/fastlink/article",
            "frontend/web/src/views/fastlink/pricing",
            "frontend/web/src/views/fastlink/tutorial",
            "frontend/web/src/views/fastlink/fachat",
            "frontend/web/src/views/module_example",
            "frontend/web/src/views/module_ai",
            "frontend/web/src/views/module_generator",
            "frontend/web/src/views/module_task",
            "frontend/web/src/mock/temp",
            "backend/static/upload",
        ),
    ),
    "business-admin": StarterPreset(
        name="business-admin",
        description="保留任务、通知、代码生成等常见后台能力，清理演示内容。",
        remove_paths=(
            "frontend/web/src/views/fastlink/article",
            "frontend/web/src/views/fastlink/pricing",
            "frontend/web/src/views/fastlink/tutorial",
            "frontend/web/src/views/fastlink/fachat",
            "frontend/web/src/views/module_example",
            "frontend/web/src/views/module_ai",
            "frontend/web/src/mock/temp",
            "backend/static/upload",
        ),
    ),
    "saas-admin": StarterPreset(
        name="saas-admin",
        description="保留 SaaS 底座能力，清理演示内容。",
        remove_paths=(
            "frontend/web/src/views/fastlink/article",
            "frontend/web/src/views/fastlink/pricing",
            "frontend/web/src/views/fastlink/tutorial",
            "frontend/web/src/views/module_example",
            "frontend/web/src/mock/temp",
            "backend/static/upload",
        ),
    ),
}


def _resolve_repo_path(path: str) -> Path:
    target = (REPO_ROOT / path).resolve()
    if not target.is_relative_to(REPO_ROOT.resolve()):
        raise ValueError(f"非法路径，超出仓库范围: {path}")
    return target


def apply_preset(preset: StarterPreset, *, dry_run: bool) -> None:
    print(f"Preset: {preset.name}")
    print(preset.description)
    print("\n将处理以下路径:")
    for item in preset.remove_paths:
        target = _resolve_repo_path(item)
        marker = "exists" if target.exists() else "missing"
        print(f" - [{marker}] {item}")

    if dry_run:
        print("\nDry run complete. 未删除任何文件。")
        return

    confirm = input("\n输入 yes 确认执行精简操作: ").strip().lower()
    if confirm != "yes":
        print("已取消。")
        return

    removed = 0
    for item in preset.remove_paths:
        target = _resolve_repo_path(item)
        if not target.exists():
            continue
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        removed += 1
        print(f"removed: {item}")
    print(f"\n完成。删除路径数: {removed}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply product starter preset.")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="minimal")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    apply_preset(PRESETS[args.preset], dry_run=args.dry_run)


if __name__ == "__main__":
    main()

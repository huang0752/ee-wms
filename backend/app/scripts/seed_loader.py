"""Seed pack manifest 加载器。"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from app.config.path_conf import SCRIPT_DIR, SEEDS_DIR
from app.core.assembly import get_assembly
from app.core.logger import logger


def _legacy_seed_files() -> dict[str, Path]:
    return {path.stem: path for path in SCRIPT_DIR.glob("*.json")}


def _read_manifest(pack: str) -> tuple[list[str], list[dict[str, Any]], Path]:
    manifest = SEEDS_DIR / pack / "seed.toml"
    if not manifest.exists():
        raise FileNotFoundError(f"seed pack 不存在: {pack} ({manifest})")

    with manifest.open("rb") as f:
        raw = tomllib.load(f)
    depends = raw.get("depends") or []
    if isinstance(depends, str):
        depends = [depends]
    if not isinstance(depends, list):
        raise TypeError(f"seed pack {pack} 的 depends 必须是字符串列表")
    tables = raw.get("tables") or []
    if not isinstance(tables, list):
        raise TypeError(f"seed pack {pack} 的 tables 必须是数组")
    return [str(item) for item in depends], tables, manifest


def _resolve_pack_order(packs: list[str]) -> list[str]:
    ordered: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(pack: str) -> None:
        if pack in visited or pack == "legacy":
            return
        if pack in visiting:
            raise ValueError(f"seed pack 依赖存在循环: {pack}")
        visiting.add(pack)
        depends, _, _ = _read_manifest(pack)
        for dep in depends:
            visit(dep)
        visiting.remove(pack)
        visited.add(pack)
        ordered.append(pack)

    for pack in packs:
        visit(pack)
    return ordered


def resolve_seed_files() -> dict[str, Path]:
    """返回 table_name -> JSON 文件路径。"""
    packs = get_assembly().seed_packs
    if not packs or "legacy" in packs:
        logger.info("✅ Seed packs 使用 legacy 兼容模式")
        return _legacy_seed_files()

    seed_files: dict[str, Path] = {}
    for pack in _resolve_pack_order(packs):
        _, tables, manifest = _read_manifest(pack)
        base_dir = manifest.parent
        for item in tables:
            table = str(item.get("table") or "").strip()
            filename = str(item.get("file") or "").strip()
            if not table or not filename:
                raise ValueError(f"seed pack {pack} 存在缺少 table/file 的 tables 配置")
            seed_file = (base_dir / filename).resolve()
            if not seed_file.exists():
                raise FileNotFoundError(f"seed 数据文件不存在: {pack}/{filename}")
            if table in seed_files:
                logger.warning("⚠️ seed table {} 被 pack {} 覆盖", table, pack)
            seed_files[table] = seed_file
    logger.info("✅ Seed packs loaded: {}", ",".join(packs))
    return seed_files

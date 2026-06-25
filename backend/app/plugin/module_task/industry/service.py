import json
from pathlib import Path

from app.config.path_conf import SCRIPT_DIR

from .schema import IndustrySamplePackOut, IndustryTermOut


class IndustrySampleService:
    """行业词库/样例包服务。"""

    @staticmethod
    def _load_json(filename: str) -> list[dict]:
        path = Path(SCRIPT_DIR) / filename
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def sample_packs(cls) -> list[IndustrySamplePackOut]:
        return [
            IndustrySamplePackOut.model_validate(item)
            for item in cls._load_json("task_industry_sample_pack.json")
        ]

    @classmethod
    def terms(cls, module: str | None = None) -> list[IndustryTermOut]:
        data = cls._load_json("task_industry_terms.json")
        if module:
            data = [item for item in data if item.get("module") == module]
        return [IndustryTermOut.model_validate(item) for item in data]

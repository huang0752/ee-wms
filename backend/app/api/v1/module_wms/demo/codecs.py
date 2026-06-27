import re

CATEGORY_CODE_MAP: dict[str, str] = {
    "变压器": "TR",
    "线圈": "COIL",
    "开关": "SW",
    "开关柜": "SWG",
    "成套设备": "ASM",
    "线缆": "CBL",
    "低压线缆": "LVC",
    "电缆终端": "TER",
    "二次": "SEC",
    "表计": "MTR",
    "电工装备": "EE",
}


def safe_category_code(category: str | None) -> str:
    if not category:
        return "GEN"
    text = category.strip()
    if text in CATEGORY_CODE_MAP:
        return CATEGORY_CODE_MAP[text]
    ascii_text = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    return ascii_text[:6] or "GEN"


def compact_parent_code(parent_code: str | None) -> str:
    if not parent_code:
        return ""
    parts = [part for part in re.split(r"[-_]", parent_code.upper()) if not re.fullmatch(r"[0-9A-F]{6}", part)]
    tokens = re.findall(r"[A-Za-z]+|[0-9]+", "".join(parts))
    return "".join(tokens)[:18]

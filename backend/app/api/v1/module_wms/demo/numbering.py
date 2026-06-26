import re
from collections import defaultdict
from datetime import datetime

from app.core.base_schema import AuthSchema

from .schema import WmsDemoNumberingProfile

DEFAULT_PREFIXES: dict[str, str] = {
    "warehouse": "WH",
    "zone": "ZN",
    "location": "LOC",
    "material": "MAT",
    "supplier": "SUP",
    "customer": "CUS",
    "barcode_rule": "BC",
    "arrival": "ARR",
    "inspection": "IQC",
    "inbound": "INB",
    "outbound": "OUT",
    "issue": "ISS",
    "transfer": "TRF",
    "stock_check": "CHK",
    "warning": "WRN",
    "stock_flow": "FL",
    "stock_lock": "LK",
    "batch": "B",
    "work_order": "MO",
}


class WmsDemoNumbering:
    def __init__(self, auth: AuthSchema, profile: WmsDemoNumberingProfile, demo_batch_id: str | None = None, now: datetime | None = None) -> None:
        self.auth = auth
        self.profile = profile
        self.demo_batch_id = demo_batch_id or ""
        self.now = now or datetime.now()
        self._seq: defaultdict[tuple[str, str], int] = defaultdict(int)
        self.tenant_short_code = self._tenant_short_code()

    def code(self, object_type: str, *, category_short: str | None = None, parent_code: str | None = None) -> str:
        seq = self._next(object_type)
        prefix = self._prefix(object_type)
        suffix = self._demo_suffix()
        if object_type == "warehouse":
            value = f"{self.tenant_short_code}-{prefix}-{seq}"
        elif object_type == "zone":
            value = f"{parent_code or self.tenant_short_code}-{prefix}{seq}"
        elif object_type == "location":
            row = ((int(seq) - 1) // 100) + 1
            col = (((int(seq) - 1) // 5) % 20) + 1
            level = ((int(seq) - 1) % 5) + 1
            value = f"{parent_code or self.tenant_short_code}-{row:02d}-{col:02d}-{level:02d}"
        elif object_type == "material":
            value = f"{self.tenant_short_code}-{prefix}-{category_short or 'GEN'}-{seq}"
        else:
            value = f"{self.tenant_short_code}-{prefix}-{seq}"
        return f"{value}-{suffix}" if suffix and object_type not in {"location"} else value

    def document_no(self, object_type: str) -> str:
        prefix = self._prefix(object_type)
        value = f"{prefix}-{self.tenant_short_code}-{self._date()}-{self._next(object_type)}"
        suffix = self._demo_suffix()
        return f"{value}-{suffix}" if suffix else value

    def batch_no(self, material_code: str) -> str:
        prefix = self._prefix("batch")
        material_short = re.sub(r"[^A-Z0-9]", "", material_code.upper())[-12:] or "MAT"
        value = f"{prefix}-{self.tenant_short_code}-{material_short}-{self._date()}-{self._next('batch')}"
        suffix = self._demo_suffix()
        return f"{value}-{suffix}" if suffix else value

    def _next(self, object_type: str) -> str:
        scope = self._date() if object_type not in {"warehouse", "zone", "location", "material", "supplier", "customer", "barcode_rule"} else "master"
        key = (object_type, scope)
        self._seq[key] += 1
        return f"{self._seq[key]:0{self.profile.sequence_digits}d}"

    def _prefix(self, object_type: str) -> str:
        raw = self.profile.prefixes.get(object_type) or DEFAULT_PREFIXES.get(object_type) or object_type[:3].upper()
        normalized = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
        return normalized[:12] or DEFAULT_PREFIXES.get(object_type, "NO")

    def _tenant_short_code(self) -> str:
        if self.profile.tenant_short_code:
            raw = self.profile.tenant_short_code
        else:
            raw = f"T{self.auth.tenant_id or 1}"
        normalized = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
        return normalized[:16] or f"T{self.auth.tenant_id or 1}"

    def _date(self) -> str:
        if self.profile.date_format == "yyMMdd":
            return self.now.strftime("%y%m%d")
        if self.profile.date_format == "yyyyMM":
            return self.now.strftime("%Y%m")
        return self.now.strftime("%Y%m%d")

    def _demo_suffix(self) -> str:
        if not self.demo_batch_id:
            return ""
        return self.demo_batch_id[-6:].upper()

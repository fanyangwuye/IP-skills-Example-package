from datetime import date
from typing import Dict, List, Optional, Tuple


TARGET_ALIAS = {
    "short_drama": "short_drama_script",
    "comic_drama": "comic_drama_script",
    "real_actor": "real_actor_script",
    "promo": "promo",
    "webnovel": "webnovel",
    "merchandise": "merchandise",
}


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        year, month, day = (int(part) for part in value.split("-"))
        return date(year, month, day)
    except Exception:
        return None


def check_license(
    license_record: Optional[Dict],
    requested_target: str,
    commercial_use: bool,
    today: Optional[date] = None,
) -> Tuple[bool, List[str]]:
    today = today or date.today()
    reasons: List[str] = []

    if not license_record:
        return False, ["未找到该 IP 的授权记录（默认拒绝）"]

    allowed = license_record.get("allowed_targets", [])
    target_norm = TARGET_ALIAS.get(requested_target, requested_target)
    if target_norm not in allowed:
        reasons.append(f"改编目标 '{requested_target}' 不在授权范围 {allowed}")

    if commercial_use and not license_record.get("commercial", False):
        reasons.append("请求商用，但该授权不允许商用")

    valid_until = _parse_date(license_record.get("valid_until"))
    if valid_until and today > valid_until:
        reasons.append(f"授权已过期（{license_record.get('valid_until')}）")

    return len(reasons) == 0, reasons


def gate(license_record, requested_target, commercial_use, today=None):
    ok, reasons = check_license(license_record, requested_target, commercial_use, today)
    if not ok:
        raise PermissionError("授权校验未通过：" + "；".join(reasons))
    return True


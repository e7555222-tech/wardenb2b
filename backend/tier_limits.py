from models import TierEnum

TIER_LEAD_LIMITS: dict[TierEnum, int | None] = {
    TierEnum.FREE: 10,
    TierEnum.PRO: 100,
    TierEnum.ENTERPRISE: None,
}


def tier_lead_limit(tier: TierEnum) -> int | None:
    return TIER_LEAD_LIMITS.get(tier)

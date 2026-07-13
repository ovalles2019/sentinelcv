"""TxDOT ITS travel-time / average-speed (TVT) client."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.models import SpeedLinkConfig, SpeedReading, congestion_level

TVT_URL = "https://its.txdot.gov/its/DistrictIts/GetTvtStatusListByDistrict"


async def fetch_tvt_index(district: str, timeout: float = 25.0) -> dict[str, dict]:
    """Return icd_Id -> raw TVT status dict for a district."""
    headers = {
        "Accept": "application/json",
        "Referer": f"https://its.txdot.gov/its/District/{district}/cameras",
        "User-Agent": "SentinelCV/0.1 (+https://github.com/ovalles2019/sentinelcv)",
    }
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        res = await client.get(TVT_URL, params={"districtCode": district}, headers=headers)
        res.raise_for_status()
        payload = res.json()
    statuses = payload.get("tvtStatuses", payload) if isinstance(payload, dict) else payload
    index: dict[str, dict] = {}
    if not isinstance(statuses, list):
        return index
    for item in statuses:
        if isinstance(item, dict) and item.get("icd_Id"):
            index[item["icd_Id"]] = item
    return index


def readings_for_links(
    index: dict[str, dict],
    links: list[SpeedLinkConfig],
) -> list[SpeedReading]:
    """Map configured speed links onto the latest TVT index."""
    now = datetime.now(timezone.utc)
    out: list[SpeedReading] = []
    for link in links:
        raw = index.get(link.id)
        if not raw:
            out.append(
                SpeedReading(
                    link_id=link.id,
                    label=link.label,
                    avg_mph=0.0,
                    travel_time_minutes=None,
                    description=None,
                    updated_at=None,
                    level="unknown",
                )
            )
            continue
        avg = raw.get("avgSpeed")
        try:
            mph = float(avg) if avg is not None else None
        except (TypeError, ValueError):
            mph = None
        tt = raw.get("travelTimeMinutes")
        try:
            minutes = float(tt) if tt is not None else None
        except (TypeError, ValueError):
            minutes = None
        desc = None
        tvt_link = raw.get("tvtLink")
        if isinstance(tvt_link, dict):
            desc = tvt_link.get("description") or tvt_link.get("dirDescription")
        out.append(
            SpeedReading(
                link_id=link.id,
                label=link.label,
                avg_mph=mph if mph is not None else 0.0,
                travel_time_minutes=minutes,
                description=desc,
                updated_at=now,
                level=congestion_level(mph),
            )
        )
    return out

"""Scrape the public contribution calendar (no token) into data/contributions.json."""
import json
import os
import re
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USERNAME = os.environ.get("GH_USERNAME", "Thi4goVcs")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"


def fetch_html() -> str:
    url = f"https://github.com/users/{USERNAME}/contributions"
    resp = requests.get(url, timeout=30, headers={"User-Agent": "profile-art-bot"})
    resp.raise_for_status()
    return resp.text


def parse_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    tips = {t.get("for"): t.get_text(strip=True) for t in soup.find_all("tool-tip")}
    days = []
    for td in soup.select("td.ContributionCalendar-day[data-date]"):
        tip = tips.get(td.get("id"), "")
        m = re.match(r"([\d,]+) contribution", tip)
        count = int(m.group(1).replace(",", "")) if m else 0
        days.append({"date": td["data-date"], "count": count, "level": int(td.get("data-level", 0))})
    days.sort(key=lambda d: d["date"])
    if not days:
        raise SystemExit("No contribution cells found - GitHub markup may have changed.")
    return days


def streaks(days: list[dict]) -> tuple[int, int]:
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)
    # Current streak: today may not have contributions yet, so allow it to be empty.
    current = 0
    tail = days[:-1] if days[-1]["count"] == 0 else days
    for d in reversed(tail):
        if d["count"] == 0:
            break
        current += 1
    return current, longest


def main() -> None:
    days = parse_days(fetch_html())
    total = sum(d["count"] for d in days)
    current, longest = streaks(days)
    best = max(days, key=lambda d: d["count"])
    monthly: OrderedDict[str, int] = OrderedDict()
    for d in days:
        monthly[d["date"][:7]] = monthly.get(d["date"][:7], 0) + d["count"]

    data = {
        "username": USERNAME,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": total,
        "current_streak": current,
        "longest_streak": longest,
        "active_days": sum(1 for d in days if d["count"] > 0),
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly,
        "days": days,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"{total} contributions, {len(days)} days, streak {current}/{longest} -> {OUT}")


if __name__ == "__main__":
    main()

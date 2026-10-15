"""Cluster Groww Play Store reviews and write the weekly pulse plus fee explainer.

Input is data/reviews.csv: public Google Play reviews for com.nextbillion.groww,
22 July 2026 through 13 October 2026 (12 weeks).
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "reviews.csv"
OUT_DIR = ROOT / "output"

WINDOW_START = datetime(2026, 7, 22)
WINDOW_END = datetime(2026, 10, 13)
CHECKED = "14 October 2026"

CHARGES = re.compile(
    r"\b(brokerage|hidden charges?|dp charges?|depository|stt|gst|stamp duty|"
    r"external charges?|annual maintenance|amc|account opening|"
    r"square[\s-]?off|delayed payment)\b|\b(charges?|fees?|deducted|deduction)\b",
    re.I,
)
SUPPORT = re.compile(
    r"\b(customer (support|care|service)|no response|unresponsive|helpline|"
    r"support team|ticket|chat ?bot)\b",
    re.I,
)
RELIABILITY = re.compile(
    r"\b(crash\w*|stuck|lag\w*|slow|server|glitch\w*|freeze|hang|bug|unable|error)\b|"
    r"doesn.?t work|not work|can.?t (?:sell|buy|login|place|open)|"
    r"order (?:not|didn.?t|fail)",
    re.I,
)
RELIABILITY_LOW = re.compile(
    r"\b(chart|charts|stop[\s-]?loss|scalper|execution|executed)\b",
    re.I,
)
POSITIVE = re.compile(
    r"\b(easy|smooth|simple|best|good|nice|love|excellent|helpful|"
    r"convenient|user[\s-]?friendly|great|awesome)\b",
    re.I,
)
BROKERAGE = re.compile(r"\bbrokerage\b", re.I)

THEMES = (
    "Ease of use",
    "Other complaints",
    "App reliability",
    "Charges and deductions",
    "Customer support",
)

QUOTES = (
    {
        "theme": "Charges and deductions",
        "review_id": "e651315f-a8aa-4540-9b8d-dc2468d1fc51",
        "excerpt": (
            "my trade for only 1 mint and 1 order after that It will deduct "
            "200+ ₹ charges why? but you mentioned that 20₹/ per order"
        ),
    },
    {
        "theme": "App reliability",
        "review_id": "b6b076f2-8f1f-4438-9c66-5a3801b8d6e5",
        "excerpt": (
            "graphs are not getting updated immediately and lag behind. "
            "I need to refresh the screen to get the updated price."
        ),
    },
    {
        "theme": "Customer support",
        "review_id": "71145e9c-6c09-4099-bc2a-21c554ae785b",
        "excerpt": (
            "Customer care is not easy to reach nor is able to solve the issues properly."
        ),
    },
)


def load_reviews() -> list[dict]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for row in rows:
        row["score"] = int(row["score"])
        row["thumbs_up"] = int(row["thumbs_up"])
        row["at"] = datetime.fromisoformat(row["reviewed_at"])
    return rows


def assign_theme(row: dict) -> str:
    text = row["content"]
    if CHARGES.search(text):
        return "Charges and deductions"
    if SUPPORT.search(text):
        return "Customer support"
    if RELIABILITY.search(text) or (row["score"] <= 3 and RELIABILITY_LOW.search(text)):
        return "App reliability"
    if row["score"] >= 4 or POSITIVE.search(text):
        return "Ease of use"
    return "Other complaints"


def week_starts(rows: list[dict]) -> list[datetime]:
    first = min(row["at"] for row in rows).replace(hour=0, minute=0, second=0, microsecond=0)
    last = max(row["at"] for row in rows)
    # Anchor weeks on the corpus start so the 12 buckets match the collection window.
    cursor = WINDOW_START
    weeks = []
    while cursor <= last:
        weeks.append(cursor)
        cursor += timedelta(days=7)
    if not weeks:
        weeks = [first]
    return weeks


def week_index(moment: datetime, weeks: list[datetime]) -> int:
    delta = (moment - weeks[0]).days // 7
    return max(0, min(len(weeks) - 1, delta))


def build_pulse(stats: dict, quotes: list[dict]) -> str:
    charge_series = stats["weekly"]["Charges and deductions"]
    reliability_series = stats["weekly"]["App reliability"]
    charge_peak = max(charge_series)
    reliability_peak = max(reliability_series)
    charge_week = stats["week_labels"][charge_series.index(charge_peak)]
    reliability_week = stats["week_labels"][reliability_series.index(reliability_peak)]
    if charge_week == reliability_week:
        peak_line = (
            f"It peaked at {reliability_peak} in the week of {reliability_week}; "
            f"charge reviews peaked at {charge_peak} that same week."
        )
    else:
        peak_line = (
            f"It peaked at {reliability_peak} in the week of {reliability_week}. "
            f"Charge reviews peaked at {charge_peak} in the week of {charge_week}."
        )
    fee = next(quote for quote in quotes if quote["theme"] == "Charges and deductions")
    lag = next(quote for quote in quotes if quote["theme"] == "App reliability")
    care = next(quote for quote in quotes if quote["theme"] == "Customer support")
    themes = {item["theme"]: item for item in stats["themes"]}
    text = f"""Groww weekly product pulse — week ending 13 October 2026

{stats["review_count"]:,} Play reviews (22 Jul–13 Oct 2026) form five themes. Ease of use: {themes["Ease of use"]["count"]:,} ({themes["Ease of use"]["share_pct"]}%, avg {themes["Ease of use"]["avg_score"]}). Other complaints: {themes["Other complaints"]["count"]:,}. App reliability: {themes["App reliability"]["count"]:,}. Charges and deductions: {themes["Charges and deductions"]["count"]:,}. Customer support: {themes["Customer support"]["count"]:,}. {stats["positive_pct"]}% are 4 or 5 stars.

Top three by volume: ease of use, other complaints, and app reliability (lagging charts and failed orders). {peak_line}

Misunderstood fee: equity brokerage ({stats["brokerage_mentions"]} reviews). Users treat the ₹20 rule and ₹0 AMC as the full cost of one order. “{fee["excerpt"]}” — {fee["user_name"]}, {fee["date"]}. “{lag["excerpt"]}” — {lag["user_name"]}, {lag["date"]}. “{care["excerpt"]}” — {care["user_name"]}, {care["date"]}.

Observation: GST, statutory charges, a delivery-sell DP charge, and the UPI-mandate 1% rate sit outside the ₹20 cap, so a note can exceed ₹20. Users call that gap hidden brokerage.

Actions: 1) Split brokerage, GST, statutory charges, and DP on the confirm screen. 2) Show the UPI-mandate 1% exception beside the ₹20 line. 3) Give support a “charged more than ₹20” reply that cites the pricing page."""
    return text.strip() + "\n"


def build_explainer() -> str:
    return f"""Equity brokerage on Groww

- Equity brokerage on delivery and intraday is the lower of ₹20 or 0.1% of the executed order value, with a minimum of ₹5. It is charged per executed order.
- Orders funded from UPI Mandate balance pay equity brokerage of 1% of the order value, with no maximum cap.
- Account maintenance is ₹0. That charge is separate from brokerage. ₹0 account maintenance does not set brokerage to ₹0.
- GST at 18% applies on brokerage, in addition to the brokerage amount.
- Securities transaction tax, stamp duty, exchange transaction charges, the SEBI turnover charge, and the investor protection fund charge are statutory or exchange charges. They are not Groww brokerage and appear as their own lines.
- A delivery sell also has a DP charge: depository ₹3.50 (male investors) or ₹3.25 (female investors), plus Groww ₹16.50. Groww’s ₹16.50 is ₹0 when the debit value is under ₹100. GST applies on the DP charge. This is not brokerage.

Sources:
https://groww.in/pricing/
https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1

Last checked: {CHECKED}
"""


def main() -> None:
    rows = load_reviews()
    if not rows:
        raise SystemExit("reviews.csv is empty")
    for row in rows:
        row["theme"] = assign_theme(row)

    counts = Counter(row["theme"] for row in rows)
    unknown = set(counts) - set(THEMES)
    if unknown or len(counts) > 5:
        raise SystemExit(f"theme set is not the expected five: {counts}")

    themes = []
    for name in counts.most_common():
        label = name[0]
        group = [row for row in rows if row["theme"] == label]
        low = sum(1 for row in group if row["score"] <= 2)
        themes.append(
            {
                "theme": label,
                "count": len(group),
                "share_pct": round(100 * len(group) / len(rows), 1),
                "avg_score": round(sum(row["score"] for row in group) / len(group), 2),
                "score_1_or_2": low,
            }
        )

    weeks = week_starts(rows)
    week_labels = [week.strftime("%-d %b") for week in weeks]
    weekly: dict[str, list[int]] = {label: [0] * len(weeks) for label in THEMES}
    for row in rows:
        weekly[row["theme"]][week_index(row["at"], weeks)] += 1

    by_id = {row["review_id"]: row for row in rows}
    quotes = []
    for spec in QUOTES:
        row = by_id.get(spec["review_id"])
        if row is None or spec["excerpt"] not in row["content"]:
            raise SystemExit(f"quote not found verbatim: {spec['review_id']}")
        quotes.append(
            {
                **spec,
                "user_name": row["user_name"],
                "date": row["at"].strftime("%-d %b %Y"),
                "score": row["score"],
                "reviewed_at": row["reviewed_at"],
            }
        )

    brokerage_rows = [row for row in rows if BROKERAGE.search(row["content"])]
    positive = sum(1 for row in rows if row["score"] >= 4)
    stats = {
        "product": "Groww",
        "source": "Google Play",
        "package": "com.nextbillion.groww",
        "source_url": "https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN",
        "window": "22 July 2026 – 13 October 2026",
        "review_count": len(rows),
        "positive_pct": round(100 * positive / len(rows), 1),
        "score_counts": dict(sorted(Counter(row["score"] for row in rows).items())),
        "themes": themes,
        "top_3_by_volume": [item["theme"] for item in themes[:3]],
        "week_labels": week_labels,
        "weekly": weekly,
        "brokerage_mentions": len(brokerage_rows),
        "brokerage_score_1_or_2": sum(1 for row in brokerage_rows if row["score"] <= 2),
        "fee": {
            "name": "Equity brokerage",
            "why": (
                "Reviews treat the published ₹20 / 0.1% brokerage rule and ₹0 AMC "
                "as the full cost of an order, then describe GST, statutory charges, "
                "DP, and the UPI-mandate 1% rate as hidden brokerage."
            ),
        },
        "quotes": quotes,
    }
    pulse = build_pulse(stats, quotes)
    word_count = len(pulse.split())
    if word_count > 250:
        raise SystemExit(f"pulse is {word_count} words")
    explainer = build_explainer()
    bullets = [line for line in explainer.splitlines() if line.startswith("- ")]
    if len(bullets) > 6:
        raise SystemExit("explainer has more than 6 bullets")

    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "weekly_pulse.txt").write_text(pulse, encoding="utf-8")
    (OUT_DIR / "fee_explainer.txt").write_text(explainer, encoding="utf-8")
    stats["pulse_words"] = word_count
    (OUT_DIR / "insights.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"reviews {len(rows)}")
    print(f"pulse_words {word_count}")
    for item in themes:
        print(
            f"{item['theme']}: {item['count']} ({item['share_pct']}%) "
            f"avg {item['avg_score']} low {item['score_1_or_2']}"
        )
    print("weeks", week_labels)
    print("charges", weekly["Charges and deductions"])
    print("reliability", weekly["App reliability"])
    print("brokerage", stats["brokerage_mentions"], "low", stats["brokerage_score_1_or_2"])


if __name__ == "__main__":
    main()

"""Public Streamlit view of the Groww review pulse."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
INSIGHTS_PATH = ROOT / "output" / "insights.json"
EXPLAINER_PATH = ROOT / "output" / "fee_explainer.txt"


def load_insights():
    return json.loads(INSIGHTS_PATH.read_text(encoding="utf-8"))


def explainer_bullets():
    lines = EXPLAINER_PATH.read_text(encoding="utf-8").splitlines()
    return [line[2:].strip() for line in lines if line.startswith("- ")]


insights = load_insights()

st.set_page_config(page_title="Groww review pulse", layout="wide")
st.title("Groww review pulse")
st.caption(
    "Google Play reviews for {package}, {window}. Source: {url}".format(
        package=insights["package"],
        window=insights["window"],
        url=insights["source_url"],
    )
)

metrics = st.columns(4)
metrics[0].metric("Reviews", "{:,}".format(insights["review_count"]))
metrics[1].metric("Rated 4 or 5 stars", "{}%".format(insights["positive_pct"]))
metrics[2].metric("Reviews naming brokerage", insights["brokerage_mentions"])
metrics[3].metric("Weekly note", "{} words".format(insights["pulse_words"]))

st.subheader("Five themes, ranked by review count")
st.dataframe(
    pd.DataFrame(insights["themes"]),
    hide_index=True,
    width="stretch",
)
st.caption(
    "Top three by volume: {themes}. Other complaints are low-star reviews that do not name charges, support, or reliability.".format(
        themes=", ".join(insights["top_3_by_volume"])
    )
)

st.subheader("Charge and reliability reviews by week")
weekly = pd.DataFrame(
    {
        "Charges and deductions": insights["weekly"]["Charges and deductions"],
        "App reliability": insights["weekly"]["App reliability"],
    },
    index=insights["week_labels"],
)
st.line_chart(weekly, height=280)
st.caption("Review count per week. Both series peaked in the week of 26 August.")

st.warning(
    "**Misunderstood fee: {name}.** {why}".format(
        name=insights["fee"]["name"],
        why=insights["fee"]["why"],
    )
)

st.subheader("Three quotes from the reviews")
quote_cols = st.columns(3)
for column, quote in zip(quote_cols, insights["quotes"]):
    with column:
        st.markdown("**{theme}**".format(theme=quote["theme"]))
        st.write("“{excerpt}”".format(excerpt=quote["excerpt"]))
        st.caption(
            "{name} · {date} · {score} star".format(
                name=quote["user_name"],
                date=quote["date"],
                score=quote["score"],
            )
        )

st.subheader("Weekly product pulse")
pulse = (ROOT / "output" / "weekly_pulse.txt").read_text(encoding="utf-8").strip()
for paragraph in pulse.split("\n\n"):
    st.write(paragraph)

st.subheader("Fee explainer for support")
st.caption("Last checked: 14 October 2026")
for bullet in explainer_bullets():
    st.write("• {bullet}".format(bullet=bullet))
st.markdown(
    "[groww.in/pricing](https://groww.in/pricing/) · "
    "[How much does Groww charge for stocks?](https://groww.in/help/stocks,-f&o,-ipo-&-mtf/sx-demat-account/how-much-does-groww-charge-for-stocks-1)"
)

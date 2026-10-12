from pathlib import Path
import json

import numpy as np
import pandas as pd

# ==================== File paths ====================

DATA_FOLDER = Path(__file__).resolve().parent
OUT = DATA_FOLDER.parent / "analysis_outputs"
T = OUT / "tables"

T.mkdir(parents=True, exist_ok=True)


def locate_dataset(stem):
    """Find a saved dataset in the project's data folder."""
    for filename in [f"{stem}.csv.gz", f"{stem}.csv"]:
        path = DATA_FOLDER / filename
        if path.is_file():
            return path

    raise FileNotFoundError(
        f"Cannot find the {stem} dataset in {DATA_FOLDER}."
    )


listing_path = locate_dataset("listings_airbnb")
review_path = locate_dataset("reviews_airbnb")

# ==================== Prepare listing features ====================

l = pd.read_csv(listing_path, low_memory=False)

l["price_aud"] = pd.to_numeric(
    l["price"].str.replace(r"[$,]", "", regex=True),
    errors="coerce"
)

l["area"] = l["neighbourhood_cleansed"]

l["quote_nights"] = (
    pd.to_datetime(l["price_quote_checkout_date"])
    - pd.to_datetime(l["price_quote_checkin_date"])
).dt.days

l["quote_lead"] = (
    pd.to_datetime(l["price_quote_checkin_date"])
    - pd.to_datetime(l["last_scraped"])
).dt.days

l["bath_num"] = pd.to_numeric(
    l["bathrooms_text"].str.extract(r"(\d+(?:\.\d+)?)")[0],
    errors="coerce"
)

l.loc[
    l["bathrooms_text"].str.contains(
        "half-bath", case=False, na=False
    ),
    "bath_num"
] = 0.5

l["property_group"] = np.select(
    [
        l["property_type"].isin([
            "Entire rental unit",
            "Entire condo",
            "Entire serviced apartment",
            "Entire loft"
        ]),
        l["property_type"].isin([
            "Entire home",
            "Entire townhouse"
        ]),
        l["property_type"].isin([
            "Entire cottage",
            "Entire cabin",
            "Entire guesthouse",
            "Entire guest suite",
            "Tiny home",
            "Farm stay"
        ])
    ],
    ["Apartment", "House/Townhouse", "Cottage/Guesthouse"],
    default="Other"
)

amenities_text = l["amenities"].map(
    lambda value: " | ".join(json.loads(value)).lower()
    if isinstance(value, str) else ""
)

patterns = {
    "Wifi": r"\bwifi\b",
    "Kitchen": r"\bkitchen\b",
    "Free parking": (
        r"\bfree parking on premises\b|\bfree driveway parking\b"
    ),
    "Self check-in": r"\bself check-in\b",
    "Pool": r"\bpool\b",
    "Fireplace": r"\b(?:indoor fireplace|fireplace)\b",
    "Hot tub": r"\bhot tub\b",
    "Pets allowed": r"\bpets allowed\b",
    "Workspace": r"\bdedicated workspace\b",
    "BBQ": r"\bbbq\b",
    "Garden": r"\bbackyard\b|\bgarden\b",
    "Air conditioning": r"air conditioning"
}

for name, pattern in patterns.items():
    l[name] = amenities_text.str.contains(
        pattern, regex=True, na=False
    ).astype(int)

# ==================== Summarize reviews ====================

# Use a common observation window for regional comparisons.
# Update these dates when using a different snapshot.
cutoff = pd.Timestamp("2026-06-16")
start = cutoff - pd.Timedelta(days=364)

theme_patterns = {
    "Walking/Transport": (
        r"\b(?:walk(?:ing|able)?|tram|train|transport|station|central|cbd)\b"
    ),
    "Quiet/Nature": (
        r"\b(?:peaceful|relax(?:ing|ation)?|quiet|tranquil|nature|"
        r"forest|retreat|wildlife|birds?|garden)\b"
    ),
    "Family/Children": (
        r"\b(?:family|families|kids|children|child|toddler)\b"
    ),
    "Couples/Celebrations": (
        r"\b(?:couple|partner|husband|wife|romantic|anniversary)\b"
    ),
    "Work/Business": r"\b(?:work|business|conference|office)\b"
}

parts = []
monthly = []
n = 0
lo = None
hi = None

with pd.read_csv(
    review_path,
    usecols=["listing_id", "date", "comments"],
    chunksize=100000
) as reader:
    for chunk in reader:
        n += len(chunk)
        dates = pd.to_datetime(chunk["date"])

        chunk_min = dates.min()
        chunk_max = dates.max()

        if pd.notna(chunk_min):
            lo = chunk_min if lo is None else min(lo, chunk_min)

        if pd.notna(chunk_max):
            hi = chunk_max if hi is None else max(hi, chunk_max)

        keep = dates.between(start, cutoff)
        r = chunk.loc[keep].copy()

        if r.empty:
            continue

        r["month"] = (
            dates.loc[keep].dt.to_period("M").astype(str)
        )
        r["text_n"] = r["comments"].notna().astype(int)

        for name, pattern in theme_patterns.items():
            r[name] = r["comments"].str.contains(
                pattern,
                case=False,
                regex=True,
                na=False
            ).astype(int)

        grouped = r.groupby("listing_id").agg(
            recent_reviews=("date", "size"),
            text_n=("text_n", "sum"),
            **{
                name: (name, "sum")
                for name in theme_patterns
            }
        )
        parts.append(grouped)

        monthly.append(
            r.groupby(["listing_id", "month"])
            .size()
            .rename("reviews")
        )

if not parts:
    raise ValueError(
        "No reviews were found within the observation window."
    )

rv = pd.concat(parts).groupby(level=0).sum()

rvm = (
    pd.concat(monthly)
    .groupby(level=[0, 1])
    .sum()
)

l = l.merge(
    rv,
    left_on="id",
    right_index=True,
    how="left",
    validate="one_to_one"
)

for name in ["recent_reviews", "text_n"] + list(theme_patterns):
    l[name] = l[name].fillna(0)

l["mature"] = pd.to_datetime(l["first_review"]).le(start)
l["has_review"] = l["recent_reviews"].gt(0)

# ==================== Define the market sample ====================

# Use listings from the current city scrape.
# Exclude records included only from previous scrapes.
c = l[l["source"].eq("city scrape")].copy()
e = c[c["room_type"].eq("Entire home/apt")].copy()

assert len(e) > 0, (
    "No entire-home listings were found. "
    "Please check the source and room_type values."
)

assert (
    pd.to_datetime(c["last_scraped"])
    .dt.to_period("M")
    .astype(str)
    .eq("2026-06")
    .mean() > 0.95
), "This dataset does not match the June 2026 snapshot."

# ==================== Save processed results ====================

l.to_csv(T / "listings_prepared.csv", index=False)
e.to_csv(T / "entire_home_listings.csv", index=False)

rv.to_csv(T / "review_summary.csv", index_label="listing_id")
rvm.to_csv(T / "monthly_reviews.csv")

review_meta = {
    "rows": n,
    "min": str(lo.date()) if lo is not None else None,
    "max": str(hi.date()) if hi is not None else None,
    "start": str(start.date()),
    "cutoff": str(cutoff.date()),
    "window_reviews": int(l["recent_reviews"].sum())
}

(OUT / "review_meta.json").write_text(
    json.dumps(review_meta, indent=2),
    encoding="utf-8"
)

print(f"Total listings: {len(l):,}")
print(f"Current city-scrape listings: {len(c):,}")
print(f"Entire-home listings: {len(e):,}")
print(f"Total review records scanned: {n:,}")
print(f"Review window: {start.date()} to {cutoff.date()}")
print(f"Processed tables saved to: {T}")

# ==================== Calendar data overview ====================

calendar_path = locate_dataset("calendar_airbnb")

# Map listing IDs to areas.z5
region = l.set_index("id")["area"].to_dict()

# Include entire-home listings from the current city scrape.
valid = set(
    l.loc[
        l["source"].eq("city scrape")
        & l["room_type"].eq("Entire home/apt"),
        "id"
    ]
)

# Use a common 90-day calendar window.
# Separate variable names preserve the earlier review window.
calendar_start = pd.Timestamp("2026-06-17")
calendar_end = calendar_start + pd.Timedelta(days=89)

calendar_parts = []
calendar_rows = 0
calendar_min = None
calendar_max = None

# Read the calendar in chunks rather than loading it all at once.
with pd.read_csv(
    calendar_path,
    usecols=[
        "listing_id",
        "date",
        "available",
        "minimum_nights",
        "maximum_nights"
    ],
    chunksize=250000
) as reader:
    for chunk in reader:
        calendar_rows += len(chunk)
        dates = pd.to_datetime(chunk["date"])

        chunk_min = dates.min()
        chunk_max = dates.max()

        if pd.notna(chunk_min):
            calendar_min = (
                chunk_min if calendar_min is None
                else min(calendar_min, chunk_min)
            )

        if pd.notna(chunk_max):
            calendar_max = (
                chunk_max if calendar_max is None
                else max(calendar_max, chunk_max)
            )

        mask = (
            chunk["listing_id"].isin(valid)
            & dates.between(calendar_start, calendar_end)
        )

        z = chunk.loc[mask].copy()

        if z.empty:
            continue

        z["is_available"] = z["available"].eq("t").astype(int)

        # Check whether each available day's rules allow a two-night stay.
        # This does not check availability across two consecutive nights.
        z["accept_2"] = (
            z["available"].eq("t")
            & z["minimum_nights"].le(2)
            & z["maximum_nights"].ge(2)
        ).astype(int)

        z["area"] = z["listing_id"].map(region)

        calendar_parts.append(
            z.groupby("area").agg(
                days=("date", "size"),
                available=("is_available", "sum"),
                accept_2=("accept_2", "sum")
            )
        )

if not calendar_parts:
    raise ValueError(
        "No matching calendar records were found "
        "within the selected observation window."
    )

s = (
    pd.concat(calendar_parts)
    .groupby(level=0)
    .sum()
)

# Return NaN when an area has no available days.
s["accept_2_share"] = (
    s["accept_2"] / s["available"].replace(0, np.nan)
)

s["open_share"] = s["available"] / s["days"]

# Preserve the variable used by subsequent analysis.
cal = s.copy()

# ==================== Save calendar results ====================

calendar_summary_path = T / "calendar_summary.csv"

cal.to_csv(
    calendar_summary_path,
    index_label="area"
)

calendar_meta = {
    "rows": calendar_rows,
    "min": (
        str(calendar_min.date())
        if calendar_min is not None else None
    ),
    "max": (
        str(calendar_max.date())
        if calendar_max is not None else None
    ),
    "window_start": str(calendar_start.date()),
    "window_end": str(calendar_end.date())
}

(OUT / "calendar_meta.json").write_text(
    json.dumps(calendar_meta, indent=2),
    encoding="utf-8"
)

print(f"Calendar records scanned: {calendar_rows:,}")
print(
    f"Calendar observation window: "
    f"{calendar_start.date()} to {calendar_end.date()}"
)
print(f"Calendar summary saved to: {calendar_summary_path}")
print(cal.to_string())

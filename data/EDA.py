# ==================== Import packages ====================

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ==================== Locate the project directory ====================

SCRIPT_DIR = Path(__file__).resolve().parent

# Support scripts stored in analysis_process, data, or the project root.
PROJECT_DIR = (
    SCRIPT_DIR.parent
    if SCRIPT_DIR.name in ["analysis_process", "data"]
    else SCRIPT_DIR
)

MODULE_DIR = PROJECT_DIR / "data"

preparation_path = MODULE_DIR / "Graph_preparation.py"

if not preparation_path.is_file():
    raise FileNotFoundError(
        f"Preparation file not found: {preparation_path}"
    )

if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


# ==================== Import plotting preparation ====================

import Graph_preparation as prep


# ==================== Set output directories ====================

OUT = PROJECT_DIR / "analysis_outputs"
F = OUT / "figures"
T = OUT / "tables"

for folder in [OUT, F, T]:
    folder.mkdir(parents=True, exist_ok=True)

if Path(prep.OUT).resolve() != OUT.resolve():
    raise ValueError(
        "Graph_preparation.py uses a different output directory. "
        f"Expected: {OUT}"
    )

export_table = prep.export_table
show_table = prep.show_table
horizontal = prep.horizontal
done = prep.done

TEAL = prep.TEAL
GOLD = prep.GOLD
GRAY = prep.GRAY


# ==================== Load prepared datasets ====================

current = prep.current.copy()
c = prep.c.copy()
e = prep.e.copy()
q = prep.q.copy()

# current: all listings from the current city scrape.
# c: confirmed non-Superhost listings from the current city scrape.
# e: non-Superhost entire-home supply sample.
# q: price-analysis and prediction sample.


# ==================== Validate EDA inputs ====================

prep.check_columns(
    current,
    [
        "id",
        "host_status",
    ],
    "Current city scrape",
)

prep.check_columns(
    c,
    [
        "price_aud",
        "bedrooms",
        "bath_num",
        "area",
    ],
    "Current non-Superhost sample",
)

prep.check_columns(
    e,
    [
        "id",
        "price_aud",
    ],
    "Entire-home supply sample",
)

prep.check_columns(
    q,
    [
        "id",
        "room_type",
        "bedrooms",
        "accommodates",
        "price_aud",
    ],
    "Price-model sample",
)

if current.empty or c.empty or e.empty or q.empty:
    raise ValueError(
        "One or more required EDA samples are empty."
    )


# ==================== Summarize sample sizes ====================

sample_summary = pd.DataFrame(
    [
        {
            "Sample": "Current city scrape",
            "Listings": len(current),
        },
        {
            "Sample": "Confirmed non-Superhost listings",
            "Listings": len(c),
        },
        {
            "Sample": "Non-Superhost entire homes",
            "Listings": len(e),
        },
        {
            "Sample": "Price-analysis and prediction sample",
            "Listings": len(q),
        },
    ]
)

export_table(
    sample_summary,
    "eda_sample_summary",
)

show_table(sample_summary)


# ==================== Summarize host-status distribution ====================

host_labels = {
    "f": "Non-Superhost",
    "t": "Superhost",
    "unknown": "Unknown",
}

host_order = [
    "Non-Superhost",
    "Superhost",
    "Unknown",
]

host_counts = (
    current["host_status"]
    .map(host_labels)
    .fillna("Unknown")
    .value_counts()
    .reindex(
        host_order,
        fill_value=0,
    )
)

host_summary = (
    host_counts
    .rename("Listings")
    .rename_axis("Host_status")
    .reset_index()
)

host_summary["Share_pct"] = (
    host_summary["Listings"]
    / len(current)
    * 100
)

export_table(
    host_summary,
    "eda_host_status_summary",
)

show_table(
    host_summary.round(2)
)


# ==================== Plot host-status distribution ====================

fig = horizontal(
    labels=host_counts.index,
    values=host_counts.values,
    title="Host status in the current city scrape",
    unit="Number of listings",
    colors=[
        TEAL,
        GRAY,
        GOLD,
    ],
)

done(
    fig,
    "eda_host_scope",
)


# ==================== Check room types in the model sample ====================

room_type_summary = (
    q.groupby("room_type")
    .size()
    .rename("Listings")
    .rename_axis("Room_type")
    .reset_index()
)

room_type_summary["Share_pct"] = (
    room_type_summary["Listings"]
    / len(q)
    * 100
)

export_table(
    room_type_summary,
    "eda_model_room_types",
)

show_table(
    room_type_summary.round(2)
)

if not q["room_type"].eq("Entire home/apt").all():
    raise ValueError(
        "The model sample contains listings outside the entire-home scope."
    )


# ==================== Calculate missing-value percentages ====================

missing_labels = {
    "price_aud": "Nightly listed price",
    "bedrooms": "Bedrooms",
    "bath_num": "Bathrooms",
    "area": "Area",
}

missing_summary = pd.DataFrame(
    {
        "Field": list(missing_labels.values()),
        "Missing_count": [
            int(c[column].isna().sum())
            for column in missing_labels
        ],
        "Sample_size": len(c),
        "Missing_pct": [
            c[column].isna().mean() * 100
            for column in missing_labels
        ],
    }
).sort_values(
    "Missing_pct",
    ascending=False,
).reset_index(drop=True)

export_table(
    missing_summary,
    "eda_missingness",
)

show_table(
    missing_summary.round(2)
)


# ==================== Plot missing-value percentages ====================

fig = horizontal(
    labels=missing_summary["Field"],
    values=missing_summary["Missing_pct"].values,
    title="Missing values in core fields",
    unit="Share of current non-Superhost listings (%)",
    fmt=lambda value: f"{value:.1f}%",
)

done(
    fig,
    "eda_missingness",
)


# ==================== Select positive listed prices ====================

prices = pd.to_numeric(
    e["price_aud"],
    errors="coerce",
)

prices = prices.loc[
    prices.gt(0)
    & np.isfinite(prices)
].copy()

if prices.empty:
    raise ValueError(
        "No finite positive listed prices are available."
    )


# ==================== Summarize nightly listed prices ====================

price_summary = (
    prices.describe(
        percentiles=[
            0.25,
            0.50,
            0.75,
            0.95,
            0.99,
        ]
    )
    .rename("Nightly_listed_price_AUD")
    .rename_axis("Statistic")
    .reset_index()
)

export_table(
    price_summary,
    "eda_price_summary",
)

show_table(
    price_summary.round(2)
)


# ==================== Define the price-distribution display range ====================

price_cap = float(
    prices.quantile(0.99)
)

median_price = float(
    prices.median()
)

display_prices = prices.loc[
    prices.le(price_cap)
]

display_check = pd.DataFrame(
    [
        {
            "Positive_price_listings": len(prices),
            "Displayed_listings": len(display_prices),
            "Listings_above_display_limit": int(
                prices.gt(price_cap).sum()
            ),
            "Display_limit_P99_AUD": price_cap,
            "Median_positive_price_AUD": median_price,
        }
    ]
)

export_table(
    display_check,
    "eda_price_display_check",
)

# The display limit affects this histogram only.
# It does not remove observations from the saved analysis samples.


# ==================== Plot nightly listed-price distribution ====================

fig, ax = plt.subplots(
    figsize=(10, 5)
)

ax.hist(
    display_prices,
    bins=42,
    color=TEAL,
    edgecolor="white",
)

ax.axvline(
    median_price,
    color=GOLD,
    linewidth=2,
    label=(
        "Median of all positive prices: "
        f"A${median_price:,.0f}"
    ),
)

ax.set_title(
    "Distribution of nightly listed prices",
    loc="left",
    pad=15,
)

ax.set_xlabel(
    "Nightly listed price (AUD)"
)

ax.set_ylabel(
    "Number of listings"
)

ax.legend()

ax.set_axisbelow(True)

ax.grid(
    axis="y",
    alpha=0.2,
)

fig.text(
    0.12,
    0.015,
    (
        "For display only, prices above the 99th percentile "
        f"(A${price_cap:,.0f}) are omitted."
    ),
    fontsize=9,
    color=prep.MUTED,
)

fig.tight_layout(
    rect=[0, 0.05, 1, 1]
)

done(
    fig,
    "eda_price_distribution",
)


# ==================== Summarize bedroom structure in the model sample ====================

bedroom_summary = (
    q.groupby("bedrooms")
    .agg(
        Listings=("id", "size"),
        Median_listed_price_AUD=(
            "price_aud",
            "median",
        ),
        Median_guest_capacity=(
            "accommodates",
            "median",
        ),
    )
    .sort_index()
    .rename_axis("Bedrooms")
    .reset_index()
)

bedroom_summary["Share_of_model_sample_pct"] = (
    bedroom_summary["Listings"]
    / len(q)
    * 100
)

export_table(
    bedroom_summary,
    "eda_bedroom_summary",
)

show_table(
    bedroom_summary.round(2)
)


# ==================== Save EDA figure inventory ====================

figure_inventory = pd.DataFrame(
    [
        {
            "Figure": "eda_host_scope.png",
            "Purpose": (
                "Describe host-status composition "
                "in the current city scrape."
            ),
            "Sample": "Current city scrape",
        },
        {
            "Figure": "eda_missingness.png",
            "Purpose": (
                "Describe missingness in core analysis fields."
            ),
            "Sample": "Current confirmed non-Superhost listings",
        },
        {
            "Figure": "eda_price_distribution.png",
            "Purpose": (
                "Inspect the distribution of positive listed prices."
            ),
            "Sample": "Non-Superhost entire-home supply sample",
        },
    ]
)

export_table(
    figure_inventory,
    "eda_figure_inventory",
)


# ==================== Print completion summary ====================

print()
print("Exploratory data analysis completed.")
print()

print(f"Current city-scrape listings: {len(current):,}")
print(f"Confirmed non-Superhost listings: {len(c):,}")
print(f"Entire-home supply sample: {len(e):,}")
print(f"Price-model sample: {len(q):,}")

print()
print(f"Median positive listed price: A${median_price:,.2f}")
print(f"Histogram display limit: A${price_cap:,.2f}")

print()
print("EDA figures saved: 3")
print(f"Figure directory: {F}")
print(f"Table directory: {T}")
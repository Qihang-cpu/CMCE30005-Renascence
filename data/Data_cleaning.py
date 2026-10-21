# ==================== Import packages ====================

from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ==================== Set input and output directories ====================

from pathlib import Path

SCRIPT_DIR = (
    Path(__file__).resolve().parent
    if "__file__" in globals()
    else Path.cwd()
)

# Scripts are stored in the project's data folder.
BASE_DIR = (
    SCRIPT_DIR.parent
    if SCRIPT_DIR.name == "data"
    else SCRIPT_DIR
)

DATA_DIR = BASE_DIR / "data"

OUT = BASE_DIR / "analysis_outputs"
F = OUT / "figures"
T = OUT / "tables"
MODELS = OUT / "models"

for folder in [OUT, F, T, MODELS]:
    folder.mkdir(parents=True, exist_ok=True)

print(f"Input directory: {DATA_DIR}")
print(f"Figure directory: {F}")
print(f"Table directory: {T}")
print(f"Model directory: {MODELS}")

# ==================== Define table functions ====================

def show_table(df):
    """Print a table without its index."""
    print(df.to_string(index=False))
    print()


def export_table(df, name):
    """Save a table to analysis_outputs/tables."""
    output_path = T / f"{name}.csv"

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    return df


# ==================== Define figure export function ====================

def export_figure(fig, name):
    """Save a figure to analysis_outputs/figures."""
    output_path = F / f"{name}.png"

    fig.savefig(
        output_path,
        dpi=300,
        bbox_inches="tight",
    )

    return output_path


# ==================== Define input file locator ====================

def locate(stem):
    """Find a dataset in the data folder or script directory."""

    filenames = [
        f"{stem}_airbnb.csv",
        f"{stem}_airbnb.csv.gz",
        f"{stem}.csv",
        f"{stem}.csv.gz",
        f"{stem} (1).csv",
        f"{stem} (1).csv.gz",
    ]

    folders = [
        BASE_DIR / "data",
        BASE_DIR,
    ]

    for folder in folders:
        for filename in filenames:
            candidate = folder / filename

            if candidate.is_file():
                return candidate

    raise FileNotFoundError(
        f"Cannot find the {stem} dataset. "
        f"Expected one of: {', '.join(filenames)}. "
        "Place the file in the script directory or its data folder."
    )


# ==================== Define required-column checker ====================

def check_columns(df, required, dataset_name):
    """Check whether a dataset contains the required columns."""

    missing = sorted(set(required) - set(df.columns))

    if missing:
        raise ValueError(
            f"The {dataset_name} dataset is missing required columns: "
            + ", ".join(missing)
        )


# ==================== Define amenity parser ====================

def parse_amenities(value):
    """Convert a JSON amenity list to lowercase text."""

    if not isinstance(value, str) or not value.strip():
        return ""

    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value.lower()

    if isinstance(parsed, list):
        return " | ".join(str(item) for item in parsed).lower()

    return str(parsed).lower()


# ==================== Load source data ====================

listing_path = locate("listings")
review_path = locate("reviews")
calendar_path = locate("calendar")

# Read IDs as strings to preserve their exact values.
raw = pd.read_csv(
    listing_path,
    dtype={"id": "string", "host_id": "string"},
    low_memory=False,
)

review_header = pd.read_csv(
    review_path,
    nrows=0,
)

calendar_header = pd.read_csv(
    calendar_path,
    nrows=0,
)

print(f"Listings file: {listing_path.name}")
print(f"Reviews file: {review_path.name}")
print(f"Calendar file: {calendar_path.name}")
print()


# ==================== Check required source columns ====================

required_listing_columns = [
    "id",
    "last_scraped",
    "price",
    "bedrooms",
    "beds",
    "accommodates",
    "minimum_nights",
    "maximum_nights",
    "latitude",
    "longitude",
    "review_scores_rating",
    "neighbourhood_cleansed",
    "host_is_superhost",
    "price_quote_checkin_date",
    "price_quote_checkout_date",
    "bathrooms_text",
    "property_type",
    "amenities",
    "first_review",
    "source",
    "room_type",
]

check_columns(
    raw,
    required_listing_columns,
    "listings",
)

check_columns(
    review_header,
    ["listing_id", "date", "comments"],
    "reviews",
)

check_columns(
    calendar_header,
    ["listing_id", "date"],
    "calendar",
)


# ==================== Summarize source files ====================

file_overview = pd.DataFrame(
    [
        [
            "listings",
            len(raw),
            raw.shape[1],
            "Listing",
        ],
        [
            "reviews",
            "Counted during chunk processing",
            len(review_header.columns),
            "Review",
        ],
        [
            "calendar",
            "Processed separately in calendar analysis",
            len(calendar_header.columns),
            "Listing-date",
        ],
    ],
    columns=[
        "Dataset",
        "Rows",
        "Columns",
        "Observation_unit",
    ],
)

show_table(file_overview)
export_table(file_overview, "file_overview")


# ==================== Check and clean listing IDs ====================

# Preserve the original dataset.
l = raw.copy()

l["id"] = l["id"].str.strip()
l["id"] = l["id"].replace("", pd.NA)

missing_id = int(l["id"].isna().sum())

duplicate_id = int(
    l.loc[l["id"].notna(), "id"].duplicated().sum()
)

l = l.dropna(subset=["id"]).copy()

l["_scraped_order"] = pd.to_datetime(
    l["last_scraped"],
    errors="coerce",
)

# Keep the most recently scraped record for each listing.
# Missing scrape dates are placed first so valid newer dates take priority.
l = (
    l.sort_values(
        "_scraped_order",
        kind="stable",
        na_position="first",
    )
    .drop_duplicates("id", keep="last")
    .sort_index()
    .drop(columns="_scraped_order")
)


# ==================== Clean prices and numeric fields ====================

# Missing or unreadable prices remain missing.
l["price_aud"] = pd.to_numeric(
    l["price"]
    .astype("string")
    .str.replace(r"[$,]", "", regex=True)
    .str.strip(),
    errors="coerce",
)

numeric_columns = [
    "bedrooms",
    "beds",
    "accommodates",
    "minimum_nights",
    "maximum_nights",
    "latitude",
    "longitude",
]

review_columns = [
    column
    for column in l.columns
    if column.startswith("review_scores_")
]

additional_numeric_columns = [
    "number_of_reviews",
    "estimated_revenue_l365d",
    "estimated_occupancy_l365d",
]

for column in (
    numeric_columns
    + review_columns
    + additional_numeric_columns
):
    if column in l.columns:
        l[column] = pd.to_numeric(
            l[column],
            errors="coerce",
        )

# Retain overall ratings only within the valid range.
l["review_scores_rating"] = l["review_scores_rating"].where(
    l["review_scores_rating"].between(1, 5)
)


# ==================== Standardize area and host status ====================

l["area"] = (
    l["neighbourhood_cleansed"]
    .astype("string")
    .str.strip()
)

host_status = (
    l["host_is_superhost"]
    .astype("string")
    .str.strip()
    .str.lower()
)

# Support both t/f and true/false representations.
l["host_status"] = (
    host_status.map(
        {
            "f": "f",
            "false": "f",
            "t": "t",
            "true": "t",
        }
    )
    .fillna("unknown")
)

# Unknown status is not classified as non-Superhost.


# ==================== Calculate quote duration and lead time ====================

checkin = pd.to_datetime(
    l["price_quote_checkin_date"],
    errors="coerce",
)

checkout = pd.to_datetime(
    l["price_quote_checkout_date"],
    errors="coerce",
)

scraped_date = pd.to_datetime(
    l["last_scraped"],
    errors="coerce",
)

l["quote_nights"] = (checkout - checkin).dt.days
l["quote_lead"] = (checkin - scraped_date).dt.days


# ==================== Extract bathroom counts ====================

bathroom_text = l["bathrooms_text"].astype("string")

l["bath_num"] = pd.to_numeric(
    bathroom_text.str.extract(
        r"(\d+(?:\.\d+)?)",
        expand=False,
    ),
    errors="coerce",
)

half_bath_mask = bathroom_text.str.contains(
    r"half[\s-]?bath",
    case=False,
    regex=True,
    na=False,
)

# Assign 0.5 only when no numeric bathroom count was extracted.
l.loc[
    half_bath_mask & l["bath_num"].isna(),
    "bath_num",
] = 0.5


# ==================== Group property types ====================

l["property_group"] = np.select(
    [
        l["property_type"].isin(
            [
                "Entire rental unit",
                "Entire condo",
                "Entire serviced apartment",
                "Entire loft",
            ]
        ),
        l["property_type"].isin(
            [
                "Entire home",
                "Entire townhouse",
            ]
        ),
        l["property_type"].isin(
            [
                "Entire cottage",
                "Entire cabin",
                "Entire guesthouse",
                "Entire guest suite",
                "Tiny home",
                "Farm stay",
            ]
        ),
    ],
    [
        "Apartment",
        "House/Townhouse",
        "Cottage/Guesthouse",
    ],
    default="Other",
)


# ==================== Extract listed amenities ====================

amenity_text = l["amenities"].map(parse_amenities)

patterns = {
    "Wifi": r"\bwifi\b",
    "Kitchen": r"\bkitchen\b",
    "Free_parking": (
        r"\bfree parking on premises\b"
        r"|\bfree driveway parking\b"
    ),
    "Self_check_in": r"\bself check-in\b",
    "Pool": r"\bpool\b",
    "Fireplace": r"\b(?:indoor fireplace|fireplace)\b",
    "Hot_tub": r"\bhot tub\b",
    "Pets_allowed": r"\bpets allowed\b",
    "Workspace": r"\bdedicated workspace\b",
    "BBQ": r"\bbbq\b",
    "Garden": r"\bbackyard\b|\bgarden\b",
    "Air_conditioning": r"air conditioning",
}

amen = list(patterns)

for feature, pattern in patterns.items():
    l[feature] = (
        amenity_text.str.contains(
            pattern,
            regex=True,
            na=False,
        )
        .astype(int)
    )

# Zero means the amenity was not explicitly listed.
l["Air_purifier_listed"] = (
    amenity_text.str.contains(
        r"air purifier|air purification",
        regex=True,
        na=False,
    )
    .astype(int)
)


# ==================== Record listing-cleaning results ====================

cleaning_log = pd.DataFrame(
    [
        [
            "Original listings",
            len(raw),
            "Preserve original data",
        ],
        [
            "Missing listing IDs",
            missing_id,
            "Exclude because records cannot be linked",
        ],
        [
            "Duplicate listing IDs",
            duplicate_id,
            "Keep the most recently scraped record",
        ],
        [
            "Missing or unreadable prices",
            int(l["price_aud"].isna().sum()),
            "Retain for supply statistics; exclude from price models",
        ],
        [
            "Non-positive prices",
            int(l["price_aud"].le(0).sum()),
            "Do not treat as valid quotes",
        ],
        [
            "Unique listings after cleaning",
            len(l),
            "One row per listing",
        ],
    ],
    columns=[
        "Check",
        "Count",
        "Treatment",
    ],
)

show_table(cleaning_log)
export_table(cleaning_log, "cleaning_log")


# ==================== Define the review observation window ====================

cutoff = pd.Timestamp("2026-06-16")
start = cutoff - pd.Timedelta(days=364)

theme_patterns = {
    "Walking_transport": (
        r"\b(?:walk(?:ing|able)?|tram|train|transport|station|central|cbd)\b"
    ),
    "Quiet_nature": (
        r"\b(?:peaceful|relax(?:ing|ation)?|quiet|tranquil|nature|forest|"
        r"retreat|wildlife|birds?|garden)\b"
    ),
    "Family_children": (
        r"\b(?:family|families|kids|children|child|toddler)\b"
    ),
    "Couples_celebrations": (
        r"\b(?:couple|partner|husband|wife|romantic|anniversary)\b"
    ),
    "Work_business": (
        r"\b(?:work|business|conference|office)\b"
    ),
}

review_count_columns = [
    "recent_reviews",
    "text_n",
] + list(theme_patterns)

parts = []
monthly = []

n = 0
lo = None
hi = None


# ==================== Process reviews in chunks ====================

for review_chunk in pd.read_csv(
    review_path,
    usecols=[
        "listing_id",
        "date",
        "comments",
    ],
    dtype={
        "listing_id": "string",
        "comments": "string",
    },
    chunksize=100000,
):
    n += len(review_chunk)

    review_chunk["listing_id"] = (
        review_chunk["listing_id"]
        .str.strip()
        .replace("", pd.NA)
    )

    dates = pd.to_datetime(
        review_chunk["date"],
        errors="coerce",
    )

    chunk_min = dates.min()
    chunk_max = dates.max()

    if pd.notna(chunk_min):
        lo = (
            chunk_min
            if lo is None
            else min(lo, chunk_min)
        )

    if pd.notna(chunk_max):
        hi = (
            chunk_max
            if hi is None
            else max(hi, chunk_max)
        )

    keep = (
        dates.between(start, cutoff)
        & review_chunk["listing_id"].notna()
    )

    if not keep.any():
        continue

    r = review_chunk.loc[keep].copy()

    r["month"] = (
        dates.loc[keep]
        .dt.to_period("M")
        .astype(str)
    )

    # Count non-missing comments, following the original definition.
    r["text_n"] = (
        r["comments"]
        .notna()
        .astype(int)
    )

    # Keywords indicate mentions, not sentiment or guest identity.
    for theme, pattern in theme_patterns.items():
        r[theme] = (
            r["comments"].str.contains(
                pattern,
                case=False,
                regex=True,
                na=False,
            )
            .astype(int)
        )

    grouped = r.groupby("listing_id").agg(
        recent_reviews=("date", "size"),
        text_n=("text_n", "sum"),
        **{
            theme: (theme, "sum")
            for theme in theme_patterns
        },
    )

    parts.append(grouped)

    monthly.append(
        r.groupby(["listing_id", "month"])
        .size()
        .rename("reviews")
    )


# ==================== Aggregate reviews by listing ID ====================

if n == 0:
    raise ValueError(
        "The reviews file contains no data rows."
    )

if not parts:
    raise ValueError(
        "No reviews with valid listing IDs were found "
        f"between {start.date()} and {cutoff.date()}. "
        "Check the dataset and observation window."
    )

rv = (
    pd.concat(parts)
    .groupby(level=0)
    .sum()
    .astype("int64")
)

rvm = (
    pd.concat(monthly)
    .groupby(level=[0, 1])
    .sum()
    .astype("int64")
)


# ==================== Merge review summaries with listings ====================

l = l.merge(
    rv,
    left_on="id",
    right_index=True,
    how="left",
    validate="one_to_one",
)

for column in review_count_columns:
    l[column] = (
        l[column]
        .fillna(0)
        .astype("int64")
    )

# An early first review indicates at least one year of review history.
# It does not establish continuous operation throughout the year.
l["mature"] = pd.to_datetime(
    l["first_review"],
    errors="coerce",
).le(start)

l["has_review"] = l["recent_reviews"].gt(0)


# ==================== Save review processing metadata ====================

review_meta = {
    "rows_processed": n,
    "earliest_review_date": (
        str(lo.date())
        if lo is not None
        else None
    ),
    "latest_review_date": (
        str(hi.date())
        if hi is not None
        else None
    ),
    "window_start": str(start.date()),
    "window_end": str(cutoff.date()),
    "window_reviews_all_listing_ids": int(
        rv["recent_reviews"].sum()
    ),
    "window_reviews_matched_to_listings": int(
        l["recent_reviews"].sum()
    ),
}

(T / "review_meta.json").write_text(
    json.dumps(
        review_meta,
        indent=2,
    ),
    encoding="utf-8",
)

export_table(
    pd.DataFrame([review_meta]),
    "review_processing_summary",
)

# Update the source-file overview with the processed review count.
file_overview.loc[
    file_overview["Dataset"].eq("reviews"),
    "Rows",
] = n

export_table(file_overview, "file_overview")

print(
    f"Review rows processed: {n:,}. "
    f"Observation window: {start.date()} to {cutoff.date()}."
)

print(
    "Review counts and theme mentions have been linked by listing ID."
)
print()


# ==================== Select the current city scrape ====================

current = l[
    l["source"].eq("city scrape")
].copy()

if current.empty:
    raise ValueError(
        "No records have source='city scrape'. "
        "Check the source values in the listings dataset."
    )

scrape_month = (
    pd.to_datetime(
        current["last_scraped"],
        errors="coerce",
    )
    .dt.to_period("M")
    .astype(str)
)

if scrape_month.eq("2026-06").mean() <= 0.95:
    raise ValueError(
        "The current city scrape does not match the expected "
        "June 2026 batch. Check the dataset before continuing."
    )


# ==================== Summarize Superhost status ====================

status_table = pd.DataFrame(
    {
        "All_listings": (
            l["host_status"]
            .value_counts()
        ),
        "Current_city_scrape": (
            current["host_status"]
            .value_counts()
        ),
    }
)

status_table = (
    status_table
    .reindex(["f", "t", "unknown"])
    .fillna(0)
    .astype(int)
)

status_table.index = [
    "Non-Superhost: eligible for scope screening",
    "Superhost: outside scope",
    "Unknown: not classified as non-Superhost",
]

status_table = (
    status_table
    .rename_axis("Host_status")
    .reset_index()
)

show_table(status_table)
export_table(status_table, "host_status_summary")


# ==================== Select non-Superhost entire homes ====================

c = current[
    current["host_status"].eq("f")
].copy()

e = c[
    c["room_type"].eq("Entire home/apt")
].copy()

scope_rows = [
    [
        "Unique listings after cleaning",
        len(l),
    ],
    [
        "Current city scrape",
        len(current),
    ],
    [
        "Confirmed non-Superhost listings",
        len(c),
    ],
    [
        "Entire homes/apartments",
        len(e),
    ],
]


# ==================== Apply the price-analysis scope ====================

q = e.copy()

conditions = [
    (
        "Valid listed price: AUD 20-2,000 per night",
        lambda x: x["price_aud"].between(20, 2000),
    ),
    (
        "1-3 bedrooms and capacity of 1-8 guests",
        lambda x: (
            x["bedrooms"].between(1, 3)
            & x["accommodates"].between(1, 8)
        ),
    ),
    (
        "Minimum stay requirement: 1-7 nights",
        lambda x: x["minimum_nights"].between(1, 7),
    ),
    (
        "Quoted stay duration: 1-7 nights",
        lambda x: x["quote_nights"].between(1, 7),
    ),
    (
        "Quoted check-in lead time: 0-30 days",
        lambda x: x["quote_lead"].between(0, 30),
    ),
]

for label, condition in conditions:
    mask = condition(q).fillna(False)
    q = q.loc[mask].copy()

    scope_rows.append(
        [
            label,
            len(q),
        ]
    )


# ==================== Create quote-date features ====================

quote_date = pd.to_datetime(
    q["price_quote_checkin_date"],
    errors="coerce",
)

# Weekend means Saturday or Sunday check-in.
q["quote_weekend"] = (
    quote_date
    .dt.dayofweek
    .ge(5)
    .astype(int)
)

q["quote_month"] = (
    quote_date
    .dt.month
    .astype("Int64")
    .astype("string")
)


# ==================== Record the sample-selection process ====================

scope_table = pd.DataFrame(
    scope_rows,
    columns=[
        "Sequential_filter",
        "Listings_retained",
    ],
)

scope_table["Listings_excluded_at_step"] = (
    scope_table["Listings_retained"]
    .shift(1)
    .sub(scope_table["Listings_retained"])
    .fillna(0)
    .astype(int)
)

show_table(scope_table)
export_table(scope_table, "scope_flow")


# ==================== Validate cleaned samples ====================

if q.empty:
    raise ValueError(
        "No listings remain in the price-model sample. "
        "Check scope_flow.csv and the source data."
    )

assert l["id"].notna().all()
assert l["id"].is_unique

assert e["id"].is_unique
assert q["id"].is_unique

assert e["host_status"].eq("f").all()
assert q["host_status"].eq("f").all()

assert e["room_type"].eq("Entire home/apt").all()
assert q["room_type"].eq("Entire home/apt").all()

assert q["price_aud"].between(20, 2000).all()
assert q["bedrooms"].between(1, 3).all()
assert q["accommodates"].between(1, 8).all()

assert q["minimum_nights"].between(1, 7).all()
assert q["quote_nights"].between(1, 7).all()
assert q["quote_lead"].between(0, 30).all()

assert set(q["id"]).issubset(set(e["id"]))


# ==================== Save cleaned datasets ====================

# All CSV outputs are saved to analysis_outputs/tables.
# The price-model sample is a subset of the supply sample.

export_table(
    l,
    "listings_cleaned_all",
)

export_table(
    e,
    "non_superhost_entire_supply",
)

export_table(
    q,
    "price_model_sample",
)

export_table(
    rv.rename_axis("listing_id").reset_index(),
    "review_summary_by_listing",
)

export_table(
    rvm.rename_axis(
        ["listing_id", "month"]
    ).reset_index(),
    "monthly_reviews_by_listing",
)


# ==================== Print completion summary ====================

print("Data cleaning completed.")
print()

print(
    f"Unique cleaned listings: {len(l):,}"
)

print(
    f"Non-Superhost entire-home supply sample: {len(e):,}"
)

print(
    f"Price-analysis and model sample: {len(q):,}"
)

print()

print(f"Figure directory: {F}")
print(f"Table directory: {T}")
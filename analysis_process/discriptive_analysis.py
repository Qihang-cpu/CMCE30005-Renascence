# ==================== Import packages ====================

from pathlib import Path
import sys
import json

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ==================== Locate the project directory ====================

SCRIPT_DIR = Path(__file__).resolve().parent

PROJECT_DIR = SCRIPT_DIR.parent
MODULE_DIR = PROJECT_DIR / "data"

required_modules = [
    MODULE_DIR / "Graph_preparation.py",
    MODULE_DIR / "Data_Visualization.py",
]

for module_path in required_modules:
    if not module_path.is_file():
        raise FileNotFoundError(
            f"Required Python file not found: {module_path}"
        )


# ==================== Configure the module search path ====================

if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


# ==================== Import preparation and visualization modules ====================

import Graph_preparation as prep
import Data_Visualization as viz

# ==================== Import prepared data and configuration ====================

BASE_DIR = prep.BASE_DIR

DATA_DIR = BASE_DIR / "data"

OUT = BASE_DIR / "analysis_outputs"
F = OUT / "figures"
T = OUT / "tables"

for folder in [OUT, F, T]:
    folder.mkdir(parents=True, exist_ok=True)

# ==================== Import prepared datasets ====================

l = prep.l
e = prep.e
q = prep.q

rvm = prep.rvm

AMENITY_COLUMNS = prep.AMENITY_COLUMNS
THEME_COLUMNS = prep.THEME_COLUMNS
SCORE_LABELS = prep.SCORE_LABELS

export_table = prep.export_table
show_table = prep.show_table

pd.set_option("display.max_columns", 30)
pd.set_option("display.width", 180)


# ==================== Define input file locator ====================

def locate_dataset(stem):
    """Find an input dataset in the project's data folder."""

    filenames = [
        f"{stem}_airbnb.csv",
        f"{stem}_airbnb.csv.gz",
        f"{stem}.csv",
        f"{stem}.csv.gz",
        f"{stem} (1).csv",
        f"{stem} (1).csv.gz",
    ]

    for folder in [DATA_DIR, BASE_DIR]:
        for filename in filenames:
            path = folder / filename

            if path.is_file():
                return path

    raise FileNotFoundError(
        f"Cannot find the {stem} dataset in "
        f"{DATA_DIR} or {BASE_DIR}."
    )


# ==================== Validate descriptive-analysis inputs ====================

prep.check_columns(
    e,
    [
        "id",
        "area",
        "property_group",
        "host_status",
        "text_n",
    ] + AMENITY_COLUMNS + THEME_COLUMNS,
    "Entire-home supply sample",
)

prep.check_columns(
    q,
    [
        "id",
        "host_id",
        "area",
        "property_group",
        "bedrooms",
        "accommodates",
        "price_aud",
        "mature",
        "has_review",
        "recent_reviews",
    ],
    "Price-analysis sample",
)

if not e["id"].is_unique:
    raise ValueError(
        "The supply sample contains duplicate listing IDs."
    )

if not q["id"].is_unique:
    raise ValueError(
        "The price-analysis sample contains duplicate listing IDs."
    )

if not e["host_status"].eq("f").all():
    raise ValueError(
        "The supply sample must contain only confirmed non-Superhosts."
    )

if not q["host_status"].eq("f").all():
    raise ValueError(
        "The price-analysis sample must contain only confirmed non-Superhosts."
    )


# ==================== Summarize supply by area ====================

supply = (
    e.groupby("area")
    .size()
    .rename("Listings")
    .sort_values(ascending=False)
    .rename_axis("Area")
    .reset_index()
)

supply["Share_of_supply_sample_pct"] = (
    supply["Listings"] / len(e) * 100
)

export_table(
    supply,
    "01_supply",
)

show_table(supply.round(2))


# ==================== Summarize property composition by area ====================

property_mix_counts = pd.crosstab(
    e["area"],
    e["property_group"],
).reindex(
    columns=prep.PROPERTY_ORDER,
    fill_value=0,
)

property_mix_pct = (
    property_mix_counts.div(
        property_mix_counts.sum(axis=1).replace(0, np.nan),
        axis=0,
    )
    * 100
)

export_table(
    property_mix_counts.reset_index(),
    "02_property_mix_counts",
)

export_table(
    property_mix_pct.round(2).reset_index(),
    "02_property_mix_pct",
)


# ==================== Summarize listed amenities by area ====================

amenity_counts = (
    e.groupby("area")[AMENITY_COLUMNS]
    .sum()
)

amenity_rates_pct = (
    e.groupby("area")[AMENITY_COLUMNS]
    .mean()
    * 100
)

export_table(
    amenity_counts.reset_index(),
    "03_amenity_counts",
)

export_table(
    amenity_rates_pct.round(2).reset_index(),
    "03_amenities_pct",
)


# ==================== Summarize review-theme mentions by area ====================

theme_counts = (
    e.groupby("area")[THEME_COLUMNS]
    .sum()
)

theme_denominators = (
    e.groupby("area")["text_n"]
    .sum()
)

theme_rates_pct = (
    theme_counts.div(
        theme_denominators.replace(0, np.nan),
        axis=0,
    )
    * 100
)

export_table(
    theme_counts.reset_index(),
    "04_review_theme_counts",
)

export_table(
    theme_rates_pct.round(2).reset_index(),
    "04_review_themes_pct",
)

export_table(
    theme_denominators
    .rename("Non_missing_comments")
    .reset_index(),
    "04_review_theme_denominators",
)


# ==================== Construct comparable market segments ====================

segment_rows = []

for (area, property_group, bedrooms), peers in q.groupby(
    ["area", "property_group", "bedrooms"],
    observed=True,
):
    historical = peers.loc[
        peers["mature"].fillna(False)
    ]

    segment_rows.append(
        {
            "area": area,
            "property_group": property_group,
            "bedrooms": int(bedrooms),
            "n": len(peers),
            "hosts": peers["host_id"].nunique(),
            "mature_n": len(historical),
            "median": peers["price_aud"].median(),
            "p25": peers["price_aud"].quantile(0.25),
            "p75": peers["price_aud"].quantile(0.75),
            "capacity": peers["accommodates"].median(),
            "reviews": historical["recent_reviews"].median(),
            "active": historical["has_review"].mean(),
        }
    )

sc = pd.DataFrame(segment_rows)

if sc.empty:
    raise ValueError(
        "No comparable market segments are available."
    )

sc = sc.sort_values(
    ["area", "property_group", "bedrooms"]
).reset_index(drop=True)

export_table(
    sc,
    "descriptive_segment_summary",
)

# Historical review activity is calculated only for listings
# whose first review predates the observation window.
# This does not establish continuous operation or occupancy.


# ==================== Compare urban one-bedroom apartments ====================

urban_onebed = sc.loc[
    sc["area"].isin(prep.URBAN_AREAS)
    & sc["property_group"].eq("Apartment")
    & sc["bedrooms"].eq(1),
    [
        "area",
        "n",
        "hosts",
        "mature_n",
        "median",
        "p25",
        "p75",
        "capacity",
        "reviews",
        "active",
    ],
].copy()

export_table(
    urban_onebed,
    "05_urban_onebed_comparison",
)

show_table(urban_onebed.round(2))


# ==================== Compare one-bedroom and two-bedroom apartments ====================

size_comparison = sc.loc[
    sc["area"].isin(["Melbourne", "Yarra"])
    & sc["property_group"].eq("Apartment")
    & sc["bedrooms"].isin([1, 2]),
    [
        "area",
        "bedrooms",
        "n",
        "mature_n",
        "median",
        "capacity",
        "reviews",
    ],
].copy()

export_table(
    size_comparison,
    "descriptive_apartment_size_comparison",
)

show_table(size_comparison.round(2))


# ==================== Compare listed price relative to capacity ====================

capacity_comparison = sc.loc[
    sc["area"].eq("Melbourne")
    & sc["property_group"].eq("Apartment")
    & sc["bedrooms"].isin([1, 2, 3])
    & sc["capacity"].gt(0)
].copy()

capacity_comparison["Price_per_capacity_AUD"] = (
    capacity_comparison["median"]
    / capacity_comparison["capacity"]
)

export_table(
    capacity_comparison,
    "descriptive_price_per_capacity",
)

# This is a ratio of group medians.
# It is not the median of listing-level per-person prices.


# ==================== Prepare comparable two-bedroom map statistics ====================

map_comparables = q.loc[
    q["property_group"].eq("Apartment")
    & q["bedrooms"].eq(2)
    & q["accommodates"].between(4, 5)
].copy()

map_statistics = (
    map_comparables.groupby("area")["price_aud"]
    .agg(
        n="size",
        median="median",
    )
)

map_statistics["Eligible_for_map"] = (
    map_statistics["n"].ge(
        prep.MIN_MAP_COMPARABLES
    )
)

export_table(
    map_statistics.reset_index(),
    "descriptive_twobed_map_sample_check",
)

export_table(
    map_statistics.loc[
        map_statistics["Eligible_for_map"],
        ["n", "median"],
    ].reset_index(),
    "07_twobed_map_comparables",
)


# ==================== Define the calendar observation window ====================

calendar_path = locate_dataset("calendar")

CALENDAR_START = pd.Timestamp("2026-06-17")
CALENDAR_END = CALENDAR_START + pd.Timedelta(days=89)

valid_ids = set(
    e["id"].dropna().astype(str)
)

region_lookup = (
    l.set_index("id")["area"]
    .to_dict()
)

calendar_parts = []

calendar_rows = 0
calendar_min_date = None
calendar_max_date = None


# ==================== Aggregate calendar rules by area ====================

for chunk in pd.read_csv(
    calendar_path,
    usecols=[
        "listing_id",
        "date",
        "available",
        "minimum_nights",
        "maximum_nights",
    ],
    dtype={
        "listing_id": "string",
        "available": "string",
    },
    chunksize=250000,
):
    calendar_rows += len(chunk)

    chunk["listing_id"] = (
        chunk["listing_id"]
        .str.strip()
    )

    dates = pd.to_datetime(
        chunk["date"],
        errors="coerce",
    )

    chunk_min = dates.min()
    chunk_max = dates.max()

    if pd.notna(chunk_min):
        calendar_min_date = (
            chunk_min
            if calendar_min_date is None
            else min(calendar_min_date, chunk_min)
        )

    if pd.notna(chunk_max):
        calendar_max_date = (
            chunk_max
            if calendar_max_date is None
            else max(calendar_max_date, chunk_max)
        )

    keep = (
        chunk["listing_id"].isin(valid_ids)
        & dates.between(
            CALENDAR_START,
            CALENDAR_END,
        )
    )

    if not keep.any():
        continue

    selected_dates = chunk.loc[keep].copy()

    for column in ["minimum_nights", "maximum_nights"]:
        selected_dates[column] = pd.to_numeric(
            selected_dates[column],
            errors="coerce",
        )

    availability = (
        selected_dates["available"]
        .str.strip()
        .str.lower()
    )

    selected_dates["is_available"] = (
        availability.isin(["t", "true", "1"])
        .astype(int)
    )

    selected_dates["accept_2"] = (
        selected_dates["is_available"].eq(1)
        & selected_dates["minimum_nights"].le(2)
        & selected_dates["maximum_nights"].ge(2)
    ).astype(int)

    selected_dates["area"] = (
        selected_dates["listing_id"]
        .map(region_lookup)
    )

    area_summary = (
        selected_dates.groupby("area")
        .agg(
            days=("date", "size"),
            available=("is_available", "sum"),
            accept_2=("accept_2", "sum"),
        )
    )

    calendar_parts.append(area_summary)

if not calendar_parts:
    raise ValueError(
        "No matching calendar records were found "
        "for the supply sample and observation window."
    )

cal = (
    pd.concat(calendar_parts)
    .groupby(level=0)
    .sum()
)

cal["accept_2_share"] = (
    cal["accept_2"]
    / cal["available"].replace(0, np.nan)
)

cal["open_share"] = (
    cal["available"]
    / cal["days"].replace(0, np.nan)
)

export_table(
    cal.rename_axis("area").reset_index(),
    "calendar_summary",
)

show_table(cal.reset_index().round(3))

# A compatible daily rule does not guarantee that two consecutive
# nights are available or that a two-night booking can be completed.


# ==================== Save calendar processing metadata ====================

calendar_meta = {
    "rows_processed": calendar_rows,
    "earliest_calendar_date": (
        str(calendar_min_date.date())
        if calendar_min_date is not None
        else None
    ),
    "latest_calendar_date": (
        str(calendar_max_date.date())
        if calendar_max_date is not None
        else None
    ),
    "window_start": str(CALENDAR_START.date()),
    "window_end": str(CALENDAR_END.date()),
    "matched_listing_dates": int(cal["days"].sum()),
}

(T / "calendar_meta.json").write_text(
    json.dumps(
        calendar_meta,
        indent=2,
    ),
    encoding="utf-8",
)


# ==================== Calculate monthly review activity ====================

cohort = q.loc[
    q["mature"].fillna(False)
    & q["area"].isin(prep.REVIEW_TREND_AREAS)
].copy()

monthly_data = (
    rvm.rename("reviews")
    .reset_index()
)

monthly_data = monthly_data.merge(
    cohort[["id", "area"]],
    left_on="listing_id",
    right_on="id",
    how="inner",
    validate="many_to_one",
)

months = pd.period_range(
    "2025-07",
    "2026-05",
    freq="M",
).astype(str)

cohort_sizes = cohort.groupby("area").size()

trend_areas = [
    area
    for area in prep.REVIEW_TREND_AREAS
    if area in cohort_sizes.index
]

if trend_areas:
    monthly_table = (
        monthly_data.groupby(
            ["month", "area"]
        )["reviews"]
        .sum()
        .unstack("area")
        .reindex(
            index=months,
            columns=trend_areas,
        )
        .fillna(0)
    )

    monthly_per_100 = (
        monthly_table.div(
            cohort_sizes.reindex(trend_areas),
            axis=1,
        )
        * 100
    )

    export_table(
        monthly_per_100
        .rename_axis("Month")
        .reset_index(),
        "06_monthly_reviews_per100",
    )

    export_table(
        cohort_sizes
        .rename("Cohort_listings")
        .rename_axis("Area")
        .reset_index(),
        "descriptive_monthly_review_cohort",
    )


# ==================== Summarize ratings and estimated annual revenue ====================

prep.check_columns(
    q,
    [
        "review_scores_rating",
        "number_of_reviews",
        "estimated_revenue_l365d",
    ],
    "Rating-analysis inputs",
)

rated = q.loc[
    q["review_scores_rating"].between(1, 5)
    & q["number_of_reviews"].ge(5)
].copy()

rated["Rating_group"] = pd.cut(
    rated["review_scores_rating"],
    bins=[0, 4.5, 4.8, 5],
    labels=prep.RATING_ORDER,
)

rating_summary = (
    rated.groupby(
        "Rating_group",
        observed=True,
    )
    .agg(
        Listings=("id", "size"),
        Valid_revenue_observations=(
            "estimated_revenue_l365d",
            "count",
        ),
        Median_listed_price_AUD=(
            "price_aud",
            "median",
        ),
        Median_estimated_annual_revenue_AUD=(
            "estimated_revenue_l365d",
            "median",
        ),
        Median_annual_reviews=(
            "recent_reviews",
            "median",
        ),
    )
    .reindex(prep.RATING_ORDER)
)

export_table(
    rating_summary.reset_index(),
    "rating_summary",
)

show_table(rating_summary.reset_index().round(2))

# These are descriptive group comparisons.
# They do not establish causation or measure actual profit.
# Estimated revenue is retained as a source-dataset estimate.


# ==================== Summarize service-score priorities ====================

service_rows = []

for column, label in SCORE_LABELS.items():
    if column not in rated.columns:
        continue

    values = rated.loc[
        rated[column].between(1, 5),
        column,
    ].dropna()

    if values.empty:
        continue

    service_rows.append(
        {
            "Service": label,
            "Valid_listings": len(values),
            "Median_score": values.median(),
            "Below_4_5_pct": (
                values.lt(4.5).mean() * 100
            ),
        }
    )

service = pd.DataFrame(
    service_rows,
    columns=[
        "Service",
        "Valid_listings",
        "Median_score",
        "Below_4_5_pct",
    ],
).sort_values(
    "Below_4_5_pct",
    ascending=False,
)

export_table(
    service,
    "service_priority",
)

show_table(service.round(2))


# ==================== Summarize facility listing evidence ====================

facility_labels = {
    "Air_conditioning": "Air conditioning",
    "Wifi": "Wi-Fi",
    "Self_check_in": "Self check-in",
    "Air_purifier_listed": "Air purifier",
}

prep.check_columns(
    q,
    list(facility_labels),
    "Facility-analysis inputs",
)

facility = pd.DataFrame(
    [
        {
            "Facility": label,
            "Listed_count": int(
                q[column].eq(1).sum()
            ),
            "Sample_size": len(q),
            "Listed_pct": (
                q[column].eq(1).mean() * 100
            ),
        }
        for column, label in facility_labels.items()
    ]
)

export_table(
    facility,
    "facility_evidence",
)

show_table(facility.round(2))

# Not explicitly listed does not mean physically absent.
# Listing prevalence does not establish an investment return.


# ==================== Generate descriptive-analysis charts ====================

DESCRIPTIVE_CHARTS = [
    ("01_market_map", viz.plot_market_map),
    ("02_supply", viz.plot_area_supply),
    ("03_property_mix", viz.plot_property_mix),
    (
        "04_comparable_price_map",
        viz.plot_comparable_price_map,
    ),
    ("05_onebed_price", viz.plot_onebed_prices),
    ("06_onebed_reviews", viz.plot_onebed_reviews),
    ("07_size_price", viz.plot_size_prices),
    ("08_per_person", viz.plot_price_per_person),
    ("09_review_themes", viz.plot_review_themes),
    ("10_family_mentions", viz.plot_family_mentions),
    ("11_pool", viz.plot_pool_rates),
    (
        "12_retreat_amenities",
        viz.plot_retreat_amenities,
    ),
    ("13_two_nights", viz.plot_two_night_rules),
    ("14_monthly_reviews", viz.plot_monthly_reviews),
    (
        "20_rating_estimated_revenue",
        viz.plot_rating_revenue,
    ),
    (
        "21_service_priorities",
        viz.plot_service_priorities,
    ),
    (
        "22_facility_evidence",
        viz.plot_facility_evidence,
    ),
]

chart_results = []

for name, function in DESCRIPTIVE_CHARTS:
    try:
        function()

    except (
        FileNotFoundError,
        KeyError,
        ValueError,
        TypeError,
        IndexError,
    ) as error:
        plt.close("all")

        chart_results.append(
            {
                "Chart": name,
                "Status": "Skipped",
                "Details": str(error),
            }
        )

        print(f"Skipped {name}: {error}")

    else:
        chart_results.append(
            {
                "Chart": name,
                "Status": "Saved",
                "Details": "",
            }
        )

        print(f"Saved {name}")


# ==================== Save descriptive chart-generation report ====================

chart_report = pd.DataFrame(chart_results)

export_table(
    chart_report,
    "descriptive_chart_generation_report",
)

saved_count = int(
    chart_report["Status"].eq("Saved").sum()
)

skipped_count = int(
    chart_report["Status"].eq("Skipped").sum()
)


# ==================== Print completion summary ====================

print()
print("Descriptive analysis completed.")
print()

print(f"Supply sample: {len(e):,} listings")
print(f"Price-analysis sample: {len(q):,} listings")
print(f"Comparable segments: {len(sc):,}")
print(f"Rating-analysis sample: {len(rated):,} listings")

print()
print(f"Charts saved: {saved_count}")
print(f"Charts skipped: {skipped_count}")

print()
print(f"Figure directory: {F}")
print(f"Table directory: {T}")

# ==================== Install missing packages ====================
import importlib.util
import subprocess
import sys

for package in ["numpy", "pandas", "statsmodels"]:
    if importlib.util.find_spec(package) is None:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", package]
        )


# ==================== Import packages ====================
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


# ==================== Define output folders ====================
OUTPUT_DIR = Path("analysis_outputs")
MODEL_DIR = OUTPUT_DIR / "models"
TABLE_DIR = OUTPUT_DIR / "tables"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)


# ==================== Prepare the analysis sample ====================
# q must be created by the project's earlier cleaning steps.
# Apply the same rating and review-count rules as D6.

column_mapping = {
    "estimated_revenue_l365d": "annual_revenue",
    "review_scores_rating": "rating",
    "number_of_reviews": "review_count",
    "bedrooms": "bedrooms",
    "accommodates": "accommodates",
    "bath_num": "bathrooms",
    "minimum_nights": "minimum_nights",
    "area": "area",
    "property_group": "property_group",
}

missing_columns = set(column_mapping) - set(q.columns)

if missing_columns:
    raise ValueError(
        f"Required columns are missing: {sorted(missing_columns)}"
    )

data = q[list(column_mapping)].rename(
    columns=column_mapping
).copy()

numeric_columns = [
    "annual_revenue",
    "rating",
    "review_count",
    "bedrooms",
    "accommodates",
    "bathrooms",
    "minimum_nights",
]

for column in numeric_columns:
    data[column] = pd.to_numeric(data[column], errors="coerce")

data[numeric_columns] = data[numeric_columns].replace(
    [np.inf, -np.inf], np.nan
)

data = data.loc[
    data["rating"].between(1, 5)
    & data["review_count"].ge(5)
    & data["annual_revenue"].ge(0)
].copy()

sample_before_complete_cases = len(data)

# Use complete cases so both models use exactly the same observations.
data = data.dropna(subset=list(column_mapping.values())).copy()

for column in ["area", "property_group"]:
    data[column] = data[column].astype(str)

if len(data) < 30 or data["rating"].nunique() < 3:
    raise ValueError(
        "Insufficient observations or rating variation."
    )

print(f"Eligible D6 observations: {sample_before_complete_cases:,}")
print(f"Complete-case regression sample: {len(data):,}")
print(
    "Excluded due to missing model variables: "
    f"{sample_before_complete_cases - len(data):,}"
)


# ==================== Fit multiple linear regression ====================
# C() automatically creates dummy variables for categorical controls.
# HC3 provides heteroskedasticity-robust standard errors.

control_terms = (
    "bedrooms + accommodates + bathrooms + minimum_nights"
    " + C(area) + C(property_group)"
)

linear_formula = (
    "annual_revenue ~ rating + " + control_terms
)

multiple_model = smf.ols(
    formula=linear_formula,
    data=data,
).fit(cov_type="HC3")

print("\nMultiple linear regression")
print(multiple_model.summary())

# Check that the model matrix is not exactly rank deficient.
design_rank = np.linalg.matrix_rank(multiple_model.model.exog)
design_columns = multiple_model.model.exog.shape[1]

if design_rank < design_columns:
    raise ValueError(
        "The model contains exactly collinear predictors. "
        "Review the control variables before interpreting coefficients."
    )


# ==================== Check for a nonlinear rating relationship ====================
# Centering makes the squared term easier to estimate and interpret.
rating_mean = data["rating"].mean()

data["rating_centered"] = data["rating"] - rating_mean

quadratic_formula = (
    "annual_revenue ~ rating_centered"
    " + I(rating_centered ** 2) + " + control_terms
)

quadratic_model = smf.ols(
    formula=quadratic_formula,
    data=data,
).fit(cov_type="HC3")

print("\nMultiple regression with a quadratic rating term")
print(quadratic_model.summary())


# ==================== Save fitted models ====================
multiple_model.save(
    str(MODEL_DIR / "rating_revenue_multiple_ols_hc3.pkl")
)

quadratic_model.save(
    str(MODEL_DIR / "rating_revenue_multiple_quadratic_hc3.pkl")
)

(MODEL_DIR / "rating_revenue_multiple_summary.txt").write_text(
    multiple_model.summary().as_text(),
    encoding="utf-8",
)

(MODEL_DIR / "rating_revenue_multiple_quadratic_summary.txt").write_text(
    quadratic_model.summary().as_text(),
    encoding="utf-8",
)

pd.Series({
    "rating_mean": rating_mean,
    "sample_size": len(data),
    "minimum_cumulative_reviews": 5,
    "linear_formula": linear_formula,
    "quadratic_formula": quadratic_formula,
}).to_json(
    MODEL_DIR / "rating_revenue_multiple_metadata.json",
    indent=2,
    force_ascii=False,
)


# ==================== Export coefficient tables ====================
def export_coefficients(model, filename):
    confidence_interval = model.conf_int()

    results = pd.DataFrame({
        "Variable": model.params.index,
        "Coefficient": model.params.values,
        "Robust_standard_error": model.bse.values,
        "P_value": model.pvalues.values,
        "CI_95_lower": confidence_interval.iloc[:, 0].values,
        "CI_95_upper": confidence_interval.iloc[:, 1].values,
    })

    results.to_csv(
        TABLE_DIR / filename,
        index=False,
        encoding="utf-8-sig",
    )

export_coefficients(
    multiple_model,
    "rating_revenue_multiple_coefficients.csv",
)

export_coefficients(
    quadratic_model,
    "rating_revenue_multiple_quadratic_coefficients.csv",
)


# ==================== Compare model fit ====================
comparison = pd.DataFrame({
    "Model": [
        "Multiple linear regression",
        "Multiple regression with quadratic rating",
    ],
    "Sample_size": [
        int(multiple_model.nobs),
        int(quadratic_model.nobs),
    ],
    "R_squared": [
        multiple_model.rsquared,
        quadratic_model.rsquared,
    ],
    "Adjusted_R_squared": [
        multiple_model.rsquared_adj,
        quadratic_model.rsquared_adj,
    ],
})

comparison.to_csv(
    TABLE_DIR / "rating_revenue_multiple_model_comparison.csv",
    index=False,
    encoding="utf-8-sig",
)

print("\nModel comparison")
print(comparison.round(4).to_string(index=False))


# ==================== Interpret the rating coefficient ====================
coefficient = multiple_model.params["rating"]
p_value = multiple_model.pvalues["rating"]
confidence_interval = multiple_model.conf_int().loc["rating"]

print("\nAdjusted rating association")
print(f"Coefficient: {coefficient:,.2f} AUD per rating point")
print(f"P-value: {p_value:.6g}")
print(
    f"95% confidence interval: "
    f"[{confidence_interval.iloc[0]:,.2f}, "
    f"{confidence_interval.iloc[1]:,.2f}]"
)

print(
    "Holding area, property type, bedrooms, guest capacity, "
    "bathrooms and minimum stay constant, a 0.1-point higher "
    f"rating is associated with {0.1 * coefficient:,.2f} AUD "
    "difference in fitted annual revenue."
)

if p_value < 0.05:
    direction = "positive" if coefficient > 0 else "negative"
    print(
        f"The adjusted linear association is statistically "
        f"significant and {direction} at the 5% level."
    )
else:
    print(
        "The adjusted linear association is not statistically "
        "significant at the 5% level."
    )


# ==================== Interpret the curvature check ====================
squared_term = "I(rating_centered ** 2)"
curvature_p = quadratic_model.pvalues[squared_term]

print(f"\nSquared-term p-value: {curvature_p:.6g}")

if curvature_p < 0.05:
    print(
        "There is evidence of curvature after controlling for "
        "listing characteristics. A constant rating slope may "
        "not adequately describe the relationship."
    )
else:
    print(
        "No statistically significant quadratic curvature was "
        "detected. This does not prove exact linearity."
    )

print(
    "\nThe models describe associations with estimated revenue. "
    "They do not establish that increasing ratings causes revenue "
    "to rise, and estimated revenue is not profit."
)

print(f"\nModels saved in: {MODEL_DIR.resolve()}")
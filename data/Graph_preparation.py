#This part will be used to define how we will draw our graphs and install drawing tools
# ==================== Import packages ====================

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter


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


# ==================== Configure display settings ====================

pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 40)
pd.set_option("display.width", 160)

SHOW_FIGURES = True
FIGURE_DPI = 300

DEFAULT_FIGSIZE = (10, 5)
MAP_FIGSIZE = (11, 7)

BAR_HEIGHT = 0.6
BAR_WIDTH = 0.32

MIN_MAP_COMPARABLES = 30


# ==================== Define chart colors ====================

NAVY = "#183C4A"
TEAL = "#168A85"
GOLD = "#D58A39"
BLUE = "#5386AF"
RED = "#BA5E4B"

MUTED = "#617580"
PALE = "#EAF1F2"
GRAY = "#C9D2D5"

WHITE = "#FFFFFF"
GRID = "#DCE4E7"
BORDER = "#C5D1D4"
MAP_BACKGROUND = "#F7FAFB"
MAP_NO_DATA = "#E0E5E6"

PROPERTY_COLORS = {
    "Apartment": TEAL,
    "House/Townhouse": BLUE,
    "Cottage/Guesthouse": GOLD,
    "Other": GRAY,
}

HOST_COLORS = {
    "Non-Superhost": TEAL,
    "Superhost": GRAY,
    "Unknown": GOLD,
}

MODEL_COLORS = {
    "Log Ridge": BLUE,
    "Random Forest": GOLD,
    "Gradient Boosting": TEAL,
}

BASELINE_COLORS = {
    "Global median": GRAY,
    "Area-bedroom median": BLUE,
    "Selected model": TEAL,
}

AREA_COLORS = {
    "Melbourne": TEAL,
    "Yarra": BLUE,
    "Port Phillip": RED,
    "Stonnington": MUTED,
    "Yarra Ranges": GOLD,
}


# ==================== Define category orders ====================

PROPERTY_ORDER = [
    "Apartment",
    "House/Townhouse",
    "Cottage/Guesthouse",
    "Other",
]

HOST_ORDER = [
    "Non-Superhost",
    "Superhost",
    "Unknown",
]

AREAS = [
    "Melbourne",
    "Yarra",
    "Port Phillip",
    "Stonnington",
    "Yarra Ranges",
]

URBAN_AREAS = [
    "Melbourne",
    "Yarra",
    "Port Phillip",
    "Stonnington",
]

MIX_AREAS = [
    "Melbourne",
    "Yarra",
    "Port Phillip",
    "Yarra Ranges",
]

REVIEW_TREND_AREAS = [
    "Melbourne",
    "Yarra",
    "Yarra Ranges",
]

BEDROOM_ORDER = [1, 2, 3]

RATING_ORDER = [
    "Up to 4.5",
    "Above 4.5 to 4.8",
    "Above 4.8",
]

N_PROPERTY_GROUPS = len(PROPERTY_ORDER)
N_HOST_GROUPS = len(HOST_ORDER)
N_FOCUS_AREAS = len(AREAS)
N_BEDROOM_GROUPS = len(BEDROOM_ORDER)


# ==================== Define amenity labels ====================

AMENITY_LABELS = {
    "Wifi": "Wi-Fi",
    "Kitchen": "Kitchen",
    "Free_parking": "Free parking",
    "Self_check_in": "Self check-in",
    "Pool": "Pool",
    "Fireplace": "Fireplace",
    "Hot_tub": "Hot tub",
    "Pets_allowed": "Pets allowed",
    "Workspace": "Dedicated workspace",
    "BBQ": "BBQ",
    "Garden": "Garden or backyard",
    "Air_conditioning": "Air conditioning",
}

AMENITY_COLUMNS = list(AMENITY_LABELS)

# Preserve the variable name used in the analysis code.
amen = AMENITY_COLUMNS.copy()


# ==================== Define review-theme labels ====================

THEME_LABELS = {
    "Walking_transport": "Walking and transport",
    "Quiet_nature": "Quiet and nature",
    "Family_children": "Family and children",
    "Couples_celebrations": "Couples and celebrations",
    "Work_business": "Work and business",
}

THEME_COLUMNS = list(THEME_LABELS)


# ==================== Define model-feature labels ====================

FEATURE_LABELS = {
    "bedrooms": "Bedrooms",
    "accommodates": "Guest capacity",
    "bath_num": "Bathrooms",
    "minimum_nights": "Minimum stay",
    "quote_nights": "Quoted stay duration",
    "quote_lead": "Check-in lead time",
    "quote_weekend": "Weekend check-in",
    "quote_month": "Check-in month",
    "area": "Area",
    "property_group": "Property type",
    **AMENITY_LABELS,
}


# ==================== Define review-score labels ====================

SCORE_LABELS = {
    "review_scores_cleanliness": "Cleanliness",
    "review_scores_value": "Value",
    "review_scores_accuracy": "Accuracy",
    "review_scores_checkin": "Check-in",
    "review_scores_communication": "Communication",
    "review_scores_location": "Location",
}


# ==================== Configure chart style ====================

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.titleweight": "bold",
        "axes.labelsize": 11,
        "axes.labelcolor": MUTED,
        "axes.edgecolor": BORDER,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.unicode_minus": False,
        "xtick.color": MUTED,
        "ytick.color": NAVY,
        "text.color": NAVY,
        "text.parse_math": False,
        "figure.facecolor": WHITE,
        "axes.facecolor": WHITE,
        "savefig.facecolor": WHITE,
        "legend.frameon": False,
        "grid.color": GRID,
        "grid.alpha": 0.6,
        "grid.linewidth": 0.7,
    }
)


# ==================== Define output functions ====================

def show_table(df):
    """Print a table without its index."""
    print(df.to_string(index=False))
    print()


def export_table(df, name):
    """Save a CSV table to the table directory."""
    output_path = T / f"{name}.csv"

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    return df


def export_figure(fig, name, show=None):
    """Save, optionally display, and close a figure."""

    if show is None:
        show = SHOW_FIGURES

    output_path = F / f"{name}.png"

    fig.savefig(
        output_path,
        dpi=FIGURE_DPI,
        bbox_inches="tight",
    )

    if show:
        plt.show()

    plt.close(fig)

    return output_path


# Preserve the function name used in the original plotting code.
def done(fig, name, show=None):
    """Save a completed chart."""
    return export_figure(fig, name, show=show)


# ==================== Define number formatters ====================

def format_count(value):
    """Format a count."""
    return f"{value:,.0f}"


def format_percent(value):
    """Format a percentage already expressed on a 0-100 scale."""
    return f"{value:.1f}%"


def format_aud(value):
    """Format an AUD amount."""
    return f"A${value:,.0f}"


COUNT_FORMATTER = FuncFormatter(
    lambda value, position: f"{value:,.0f}"
)

AUD_FORMATTER = FuncFormatter(
    lambda value, position: f"A${value:,.0f}"
)


# ==================== Define required-column checker ====================

def check_columns(df, required, dataset_name):
    """Check that all required columns are available."""

    missing = sorted(set(required) - set(df.columns))

    if missing:
        raise ValueError(
            f"{dataset_name} is missing required columns: "
            + ", ".join(missing)
        )


# ==================== Define cleaned-data loader ====================

def load_cleaned_table(filename, required_columns=None):
    """Load a table produced by the data-cleaning script."""

    path = T / filename

    if not path.is_file():
        raise FileNotFoundError(
            f"Cannot find {path}. "
            "Run the data-cleaning script first."
        )

    df = pd.read_csv(
        path,
        dtype={
            "id": "string",
            "host_id": "string",
            "listing_id": "string",
        },
        low_memory=False,
    )

    if required_columns is not None:
        check_columns(
            df,
            required_columns,
            filename,
        )

    return df


# ==================== Load cleaned listing datasets ====================

l = load_cleaned_table(
    "listings_cleaned_all.csv",
    required_columns=[
        "id",
        "source",
        "host_status",
        "area",
        "property_group",
    ],
)

e = load_cleaned_table(
    "non_superhost_entire_supply.csv",
    required_columns=[
        "id",
        "area",
        "property_group",
        "price_aud",
        "text_n",
    ] + AMENITY_COLUMNS + THEME_COLUMNS,
)

q = load_cleaned_table(
    "price_model_sample.csv",
    required_columns=[
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
)


# ==================== Restore Boolean and numeric fields ====================

def restore_boolean(series):
    """Restore Boolean values from CSV representations."""

    values = (
        series.astype("string")
        .str.strip()
        .str.lower()
    )

    mapping = {
        "true": True,
        "false": False,
        "1": True,
        "0": False,
        "1.0": True,
        "0.0": False,
    }

    invalid = values.notna() & ~values.isin(list(mapping))

    if invalid.any():
        raise ValueError(
            f"Unexpected Boolean values in {series.name}: "
            f"{values.loc[invalid].unique().tolist()}"
        )

    return values.map(mapping).astype("boolean")


NUMERIC_COLUMNS = [
    "price_aud",
    "bedrooms",
    "beds",
    "accommodates",
    "bath_num",
    "minimum_nights",
    "maximum_nights",
    "quote_nights",
    "quote_lead",
    "quote_weekend",
    "latitude",
    "longitude",
    "recent_reviews",
    "text_n",
    "number_of_reviews",
    "estimated_revenue_l365d",
    "estimated_occupancy_l365d",
    "Air_purifier_listed",
] + AMENITY_COLUMNS + THEME_COLUMNS

for df in [l, e, q]:
    score_columns = [
        column
        for column in df.columns
        if column.startswith("review_scores_")
    ]

    for column in set(NUMERIC_COLUMNS + score_columns):
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    for column in ["mature", "has_review"]:
        if column in df.columns:
            df[column] = restore_boolean(df[column])

    if "quote_month" in df.columns:
        df["quote_month"] = (
            pd.to_numeric(
                df["quote_month"],
                errors="coerce",
            )
            .astype("Int64")
            .astype("string")
        )


# ==================== Reconstruct current research samples ====================

current = l.loc[
    l["source"].eq("city scrape")
].copy()

c = current.loc[
    current["host_status"].eq("f")
].copy()

if current.empty:
    raise ValueError(
        "No current city-scrape listings are available."
    )

if e.empty or q.empty:
    raise ValueError(
        "The supply sample or price-model sample is empty."
    )

for name, df in [
    ("Cleaned listings", l),
    ("Supply sample", e),
    ("Price-model sample", q),
]:
    if df["id"].isna().any() or not df["id"].is_unique:
        raise ValueError(
            f"{name} must contain one non-missing ID per listing."
        )

if not e["host_status"].eq("f").all():
    raise ValueError(
        "The supply sample contains listings outside the non-Superhost scope."
    )

if not q["host_status"].eq("f").all():
    raise ValueError(
        "The model sample contains listings outside the non-Superhost scope."
    )


# ==================== Load monthly review data ====================

monthly_reviews = load_cleaned_table(
    "monthly_reviews_by_listing.csv",
    required_columns=[
        "listing_id",
        "month",
        "reviews",
    ],
)

monthly_reviews["reviews"] = pd.to_numeric(
    monthly_reviews["reviews"],
    errors="raise",
)

monthly_reviews["month"] = (
    monthly_reviews["month"].astype("string")
)

if monthly_reviews.duplicated(
    ["listing_id", "month"]
).any():
    raise ValueError(
        "Monthly review data must contain one row per listing and month."
    )

# Preserve the variable name used in the original analysis.
rvm = (
    monthly_reviews
    .set_index(["listing_id", "month"])["reviews"]
    .sort_index()
)


# ==================== Calculate sample sizes ====================

SAMPLE_SIZES = {
    "Cleaned listings": len(l),
    "Current city scrape": len(current),
    "Current non-Superhost listings": len(c),
    "Non-Superhost entire-home supply": len(e),
    "Price-model sample": len(q),
}

sample_sizes = pd.DataFrame(
    SAMPLE_SIZES.items(),
    columns=[
        "Sample",
        "Listings",
    ],
)

export_table(
    sample_sizes,
    "plot_sample_sizes",
)


# ==================== Calculate host-status counts ====================

HOST_LABELS = {
    "f": "Non-Superhost",
    "t": "Superhost",
    "unknown": "Unknown",
}

host_counts = (
    current["host_status"]
    .map(HOST_LABELS)
    .fillna("Unknown")
    .value_counts()
    .reindex(HOST_ORDER, fill_value=0)
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
    "plot_host_status_counts",
)


# ==================== Calculate property-category counts ====================

property_counts = (
    e["property_group"]
    .value_counts()
    .reindex(PROPERTY_ORDER, fill_value=0)
)

property_summary = (
    property_counts
    .rename("Listings")
    .rename_axis("Property_group")
    .reset_index()
)

property_summary["Share_pct"] = (
    property_summary["Listings"]
    / len(e)
    * 100
)

export_table(
    property_summary,
    "plot_property_category_counts",
)


# ==================== Calculate area supply counts ====================

area_counts = (
    e.groupby("area")
    .size()
    .sort_values(ascending=False)
)

area_supply = (
    area_counts
    .rename("Listings")
    .rename_axis("Area")
    .reset_index()
)

area_supply["Share_of_supply_sample_pct"] = (
    area_supply["Listings"]
    / len(e)
    * 100
)

export_table(
    area_supply,
    "plot_area_supply_counts",
)


# ==================== Calculate bedroom-category counts ====================

bedroom_summary = (
    q.groupby("bedrooms")
    .agg(
        Listings=("id", "size"),
        Median_price_AUD=("price_aud", "median"),
        Median_capacity=("accommodates", "median"),
    )
    .reindex(BEDROOM_ORDER)
)

bedroom_summary["Listings"] = (
    bedroom_summary["Listings"]
    .fillna(0)
    .astype(int)
)

bedroom_summary.index.name = "Bedrooms"

export_table(
    bedroom_summary.reset_index(),
    "plot_bedroom_category_summary",
)


# ==================== Calculate property mix by area ====================

property_mix_counts = pd.crosstab(
    e["area"],
    e["property_group"],
).reindex(
    columns=PROPERTY_ORDER,
    fill_value=0,
)

property_mix = property_mix_counts.div(
    property_mix_counts.sum(axis=1).replace(0, np.nan),
    axis=0,
)

export_table(
    property_mix_counts.reset_index(),
    "plot_property_mix_counts",
)

export_table(
    (property_mix * 100)
    .round(2)
    .reset_index(),
    "plot_property_mix_pct",
)


# ==================== Calculate amenity listing rates ====================

amenity_rates = (
    e.groupby("area")[AMENITY_COLUMNS]
    .mean()
)

export_table(
    (amenity_rates * 100)
    .round(2)
    .reset_index(),
    "plot_amenity_listing_rates_pct",
)


# ==================== Calculate review-theme mention rates ====================

theme_counts = (
    e.groupby("area")[THEME_COLUMNS]
    .sum()
)

theme_denominators = (
    e.groupby("area")["text_n"]
    .sum()
)

theme_rates = (
    theme_counts.div(
        theme_denominators.replace(0, np.nan),
        axis=0,
    )
    * 100
)

export_table(
    theme_counts.reset_index(),
    "plot_review_theme_counts",
)

export_table(
    theme_denominators
    .rename("Non_missing_comments")
    .reset_index(),
    "plot_review_theme_denominators",
)

export_table(
    theme_rates
    .round(2)
    .reset_index(),
    "plot_review_theme_rates_pct",
)


# ==================== Calculate comparable-segment statistics ====================

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
        "No comparable segments could be constructed."
    )

export_table(
    sc,
    "plot_comparable_segment_statistics",
)


# ==================== Define segment selector ====================

def select_segment(area, bedrooms, property_group="Apartment"):
    """Select one area-property-bedroom segment."""

    result = sc.loc[
        sc["area"].eq(area)
        & sc["bedrooms"].eq(bedrooms)
        & sc["property_group"].eq(property_group)
    ]

    if result.empty:
        raise ValueError(
            "No matching segment: "
            f"{area}, {property_group}, {bedrooms} bedrooms."
        )

    return result.iloc[0]


# ==================== Define chart-axis styling ====================

def style_axis(ax, grid_axis="x"):
    """Apply consistent grid and tick styling."""

    ax.set_axisbelow(True)
    ax.grid(
        axis=grid_axis,
        alpha=0.6,
    )

    ax.tick_params(
        axis="y",
        length=0,
        pad=8,
    )

    return ax


# ==================== Define horizontal bar-chart function ====================

def horizontal(
    labels,
    values,
    title,
    unit="",
    colors=None,
    fmt=None,
    figsize=DEFAULT_FIGSIZE,
):
    """Create a horizontal bar chart without saving it."""

    labels = list(labels)
    values = np.asarray(values, dtype=float)

    if len(labels) != len(values):
        raise ValueError(
            "Labels and values must have the same length."
        )

    valid = np.isfinite(values)

    if not valid.any():
        raise ValueError(
            "No finite values are available for this chart."
        )

    valid_labels = [
        label
        for label, keep in zip(labels, valid)
        if keep
    ]

    valid_values = values[valid]

    if colors is None:
        bar_colors = TEAL
    elif isinstance(colors, str):
        bar_colors = colors
    else:
        colors = list(colors)

        if len(colors) != len(values):
            raise ValueError(
                "The color list must match the number of values."
            )

        bar_colors = [
            color
            for color, keep in zip(colors, valid)
            if keep
        ]

    fig, ax = plt.subplots(figsize=figsize)

    bars = ax.barh(
        valid_labels,
        valid_values,
        color=bar_colors,
        height=BAR_HEIGHT,
    )

    ax.invert_yaxis()

    ax.set_title(
        title,
        loc="left",
        pad=16,
    )

    ax.set_xlabel(unit)

    style_axis(ax, grid_axis="x")

    lower = min(0.0, float(valid_values.min()))
    upper = max(0.0, float(valid_values.max()))
    span = max(upper - lower, 1.0)

    ax.set_xlim(
        lower - (0.12 * span if lower < 0 else 0),
        upper + 0.25 * span,
    )

    formatter = fmt or format_count

    for bar, value in zip(bars, valid_values):
        offset = 0.025 * span

        ax.text(
            value + offset if value >= 0 else value - offset,
            bar.get_y() + bar.get_height() / 2,
            formatter(value),
            va="center",
            ha="left" if value >= 0 else "right",
            fontweight="bold",
        )

    fig.tight_layout()

    return fig


# ==================== Define grouped bar-chart function ====================

def grouped_bar(
    table,
    title,
    ylabel="",
    colors=None,
    value_format="{:.0f}",
    figsize=DEFAULT_FIGSIZE,
):
    """Create a grouped bar chart from a numeric DataFrame."""

    if table.empty or len(table.columns) == 0:
        raise ValueError(
            "The grouped-bar table is empty."
        )

    fig, ax = plt.subplots(figsize=figsize)

    positions = np.arange(len(table))
    n_series = len(table.columns)
    width = 0.8 / n_series

    palette = (
        list(colors)
        if colors is not None
        else [TEAL, GOLD, BLUE, RED]
    )

    if not palette:
        raise ValueError(
            "At least one color is required."
        )

    for i, column in enumerate(table.columns):
        values = pd.to_numeric(
            table[column],
            errors="coerce",
        ).to_numpy(dtype=float)

        bars = ax.bar(
            positions + (i - (n_series - 1) / 2) * width,
            values,
            width=width,
            label=str(column),
            color=palette[i % len(palette)],
        )

        labels = [
            value_format.format(value)
            if np.isfinite(value)
            else ""
            for value in values
        ]

        ax.bar_label(
            bars,
            labels=labels,
            padding=4,
            fontsize=10,
        )

    ax.set_xticks(
        positions,
        table.index.astype(str),
    )

    ax.set_title(
        title,
        loc="left",
        pad=16,
    )

    ax.set_ylabel(ylabel)
    ax.margins(y=0.2)
    ax.legend()

    style_axis(ax, grid_axis="y")

    fig.tight_layout()

    return fig


# ==================== Define property legend function ====================

def property_legend_handles():
    """Create legend handles in the standard property order."""

    return [
        Patch(
            facecolor=PROPERTY_COLORS[property_group],
            label=property_group,
        )
        for property_group in PROPERTY_ORDER
    ]


# ==================== Define available-area selector ====================

def available_areas(df, requested_areas, axis="index"):
    """Keep requested areas that exist in a table."""

    available = (
        df.index
        if axis == "index"
        else df.columns
    )

    return [
        area
        for area in requested_areas
        if area in available
    ]


# ==================== Print preparation summary ====================

print("Plot preparation completed.")
print()

show_table(sample_sizes)

print(f"Property categories: {N_PROPERTY_GROUPS}")
print(f"Host-status categories: {N_HOST_GROUPS}")
print(f"Focus areas: {N_FOCUS_AREAS}")
print(f"Bedroom categories: {N_BEDROOM_GROUPS}")
print(f"Comparable segments: {len(sc):,}")
print()

print(f"Figure directory: {F}")
print(f"Table directory: {T}")
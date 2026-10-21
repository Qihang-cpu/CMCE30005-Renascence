#This will be the process that using the method that defined in the Graph_preparation part and make data visualization 
#of our project 

#This code should run after every analysis code parts are all run. So please run the analysis process first, then this part can give 
#all the graghs we need.

# ==================== Import packages ====================



from pathlib import Path
import base64
import io
import json
import zipfile

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

from matplotlib.colors import Normalize
from matplotlib.patches import Polygon, FancyBboxPatch

from shapely.geometry import shape, box
from shapely.ops import polylabel, unary_union

# ==================== Import plotting preparation ====================

import Graph_preparation as prep


# ==================== Import output directories ====================

BASE_DIR = prep.BASE_DIR
OUT = prep.OUT
F = prep.F
T = prep.T
MODELS = prep.MODELS

# ==================== Import plotting configuration ====================

BASE_DIR = prep.BASE_DIR
OUT = prep.OUT
F = prep.F
T = prep.T

NAVY = prep.NAVY
TEAL = prep.TEAL
GOLD = prep.GOLD
BLUE = prep.BLUE
RED = prep.RED
GRAY = prep.GRAY
MUTED = prep.MUTED

PROPERTY_ORDER = prep.PROPERTY_ORDER
PROPERTY_COLORS = prep.PROPERTY_COLORS
AREA_COLORS = prep.AREA_COLORS

AREAS = prep.AREAS
URBAN_AREAS = prep.URBAN_AREAS
MIX_AREAS = prep.MIX_AREAS
REVIEW_TREND_AREAS = prep.REVIEW_TREND_AREAS

AMENITY_LABELS = prep.AMENITY_LABELS
THEME_LABELS = prep.THEME_LABELS
FEATURE_LABELS = prep.FEATURE_LABELS
SCORE_LABELS = prep.SCORE_LABELS

l = prep.l
e = prep.e
q = prep.q
c = prep.c
sc = prep.sc
rvm = prep.rvm

host_counts = prep.host_counts
area_counts = prep.area_counts
property_mix = prep.property_mix
amenity_rates = prep.amenity_rates
theme_rates = prep.theme_rates

done = prep.done
horizontal = prep.horizontal
grouped_bar = prep.grouped_bar
export_table = prep.export_table
style_axis = prep.style_axis


# ==================== Define optional analysis-output loader ====================

def load_output(filenames, required_columns=None):
    """Load an existing analysis table without refitting models."""

    for filename in filenames:
        path = T / filename

        if not path.is_file():
            continue

        table = pd.read_csv(path)

        if required_columns is not None:
            prep.check_columns(
                table,
                required_columns,
                filename,
            )

        return table

    raise FileNotFoundError(
        "Required analysis output is unavailable. Expected: "
        + ", ".join(str(T / name) for name in filenames)
    )


# ==================== Define chart execution wrapper ====================

chart_results = []


def run_chart(name, function):
    """Run a chart and report unavailable inputs."""

    try:
        function()

    except (
        FileNotFoundError,
        KeyError,
        ValueError,
        TypeError,
        IndexError,
    ) as error:
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


# ==================== Define chart-data helpers ====================

def require_rows(table, description):
    """Require at least one row."""

    if table.empty:
        raise ValueError(
            f"No valid observations are available for {description}."
        )

    return table


def select_areas(table, requested):
    """Select available areas in the requested order."""

    areas = [
        area
        for area in requested
        if area in table.index
    ]

    if not areas:
        raise ValueError(
            "None of the requested areas are available."
        )

    return table.loc[areas]


def onebed_apartments():
    """Return urban one-bedroom apartment segments."""

    data = sc.loc[
        sc["property_group"].eq("Apartment")
        & sc["bedrooms"].eq(1)
        & sc["area"].isin(URBAN_AREAS)
    ].set_index("area")

    return select_areas(data, URBAN_AREAS)


def rating_sample():
    """Return listings with valid ratings and at least five reviews."""

    prep.check_columns(
        q,
        [
            "review_scores_rating",
            "number_of_reviews",
        ],
        "Price-model sample",
    )

    return require_rows(
        q.loc[
            q["review_scores_rating"].between(1, 5)
            & q["number_of_reviews"].ge(5)
        ].copy(),
        "rating analysis",
    )


# ==================== Load geographic boundaries ====================

def load_boundaries():
    """Load GeoJSON or extract boundaries from the original notebook."""

    candidates = [
        BASE_DIR / "data" / "map" / "neighbourhoods.geojson",
        BASE_DIR / "map" / "neighbourhoods.geojson",
        BASE_DIR / "assets" / "neighbourhoods.geojson",
        BASE_DIR / "data" / "neighbourhoods.geojson",
        BASE_DIR / "neighbourhoods.geojson",
    ]

    for path in candidates:
        if path.is_file():
            return json.loads(
                path.read_text(encoding="utf-8")
            )

    notebook_paths = sorted(
        BASE_DIR.glob("Melbourne_Airbnb*.ipynb")
    )

    for notebook_path in notebook_paths:
        notebook = json.loads(
            notebook_path.read_text(encoding="utf-8")
        )

        for cell in notebook.get("cells", []):
            if cell.get("cell_type") != "code":
                continue

            source = "".join(cell.get("source", []))

            for line in source.splitlines():
                if not line.strip().startswith("_packed_assets"):
                    continue

                left, separator, right = line.partition("=")

                if not separator or left.strip() != "_packed_assets":
                    continue

                encoded = right.strip()

                if (
                    len(encoded) < 2
                    or encoded[0] not in ["'", '"']
                    or encoded[-1] != encoded[0]
                ):
                    continue

                payload = base64.b64decode(
                    encoded[1:-1],
                    validate=True,
                )

                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    return json.loads(
                        archive.read("neighbourhoods.geojson")
                    )

    raise FileNotFoundError(
        "Place neighbourhoods.geojson in the script directory "
        "or data folder, or keep the original "
        "Melbourne_Airbnb notebook in the script directory."
    )


# ==================== Define geographic plotting helpers ====================

def polygon_rings(feature):
    """Return exterior rings from Polygon or MultiPolygon geometry."""

    geometry = feature.get("geometry") or {}
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates", [])

    if geometry_type == "Polygon":
        polygons = [coordinates]

    elif geometry_type == "MultiPolygon":
        polygons = coordinates

    else:
        return []

    return [
        polygon[0]
        for polygon in polygons
        if polygon
    ]


def boundary_name(feature):
    """Read an area name from common GeoJSON properties."""

    properties = feature.get("properties", {})

    for key in [
        "neighbourhood",
        "neighbourhood_cleansed",
        "name",
        "NAME",
    ]:
        if key in properties:
            return properties[key]

    return None


def draw_base_map(
    ax,
    geo,
    values=None,
    cmap=None,
    norm=None,
    highlights=None,
    extent=None,
):
    """Draw geographic boundaries."""

    for feature in geo["features"]:
        name = boundary_name(feature)
        color = "#EFF2F0"

        if values is not None:
            value = values.get(name, np.nan)

            color = (
                cmap(norm(value))
                if pd.notna(value)
                else prep.MAP_NO_DATA
            )

        if highlights is not None:
            color = highlights.get(name, color)

        for ring in polygon_rings(feature):
            ax.add_patch(
                Polygon(
                    ring,
                    closed=True,
                    facecolor=color,
                    edgecolor="white",
                    linewidth=0.8,
                    zorder=1,
                )
            )

    if extent is None:
        extent = [
            144.38,
            146.23,
            -38.13,
            -37.39,
        ]

    ax.set_xlim(extent[0], extent[1])
    ax.set_ylim(extent[2], extent[3])

    ax.set_aspect(
        1 / np.cos(np.deg2rad(37.8))
    )

    ax.set_facecolor(prep.MAP_BACKGROUND)
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.annotate(
        "N",
        xy=(0.96, 0.96),
        xytext=(0.96, 0.81),
        xycoords="axes fraction",
        ha="center",
        color=NAVY,
        arrowprops={
            "arrowstyle": "->",
            "color": NAVY,
        },
    )


def map_note(fig, text):
    """Add a source and scope note."""

    fig.text(
        0.03,
        0.015,
        text,
        fontsize=8,
        color=MUTED,
    )


# ==================== Plot analysis framework ====================

def plot_analysis_framework():

    fig, ax = plt.subplots(figsize=(12, 7))

    ax.set_xlim(0, 12)
    ax.set_ylim(0, 7)
    ax.axis("off")

    def box(x, y, width, height, text):
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                width,
                height,
                boxstyle="round,pad=0.12",
                facecolor="#F0F6F5",
                edgecolor=TEAL,
                linewidth=1.5,
            )
        )

        ax.text(
            x + width / 2,
            y + height / 2,
            text,
            ha="center",
            va="center",
            fontsize=10,
        )

    def arrow(start, end):
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            arrowprops={
                "arrowstyle": "->",
                "color": MUTED,
                "lw": 1.4,
            },
        )

    box(
        2,
        5.9,
        8,
        0.65,
        "Business problem: product choice, listing price, and operations",
    )

    box(
        2,
        4.7,
        8,
        0.65,
        "Data understanding, cleaning, and exploratory analysis",
    )

    box(
        0.25,
        3.15,
        3.2,
        0.85,
        "Descriptive analysis\nMarket structure and differences",
    )

    box(
        4.4,
        3.15,
        3.2,
        0.85,
        "Predictive analysis\nReference listing prices",
    )

    box(
        8.55,
        3.15,
        3.2,
        0.85,
        "Prescriptive analysis\nCandidate screening and trial prices",
    )

    box(
        2,
        1.85,
        8,
        0.65,
        "Interpret results and integrate evidence",
    )

    box(
        2,
        0.65,
        8,
        0.65,
        "Recommendations, monitoring, and limitations",
    )

    arrow((6, 5.9), (6, 5.35))
    arrow((6, 4.7), (1.85, 4.0))
    arrow((3.45, 3.58), (4.4, 3.58))
    arrow((7.6, 3.58), (8.55, 3.58))
    arrow((10.15, 3.15), (6, 2.5))
    arrow((6, 1.85), (6, 1.3))

    ax.set_title(
        "Analysis framework",
        loc="left",
        pad=15,
    )

    fig.tight_layout()
    done(fig, "00_analysis_framework")


# ==================== Plot host-status distribution ====================

def plot_host_scope():

    fig = horizontal(
        host_counts.index,
        host_counts.values,
        "Host status in the current city scrape",
        "Number of listings",
        colors=[
            prep.HOST_COLORS[label]
            for label in host_counts.index
        ],
    )

    done(fig, "eda_host_scope")


# ==================== Plot missing-value percentages ====================

def plot_missingness():

    labels = {
        "price_aud": "Nightly listed price",
        "bedrooms": "Bedrooms",
        "bath_num": "Bathrooms",
        "area": "Area",
    }

    missing = (
        c[list(labels)]
        .isna()
        .mean()
        .mul(100)
        .rename(index=labels)
        .sort_values(ascending=False)
    )

    export_table(
        missing.rename("Missing_pct")
        .rename_axis("Field")
        .reset_index(),
        "eda_missingness",
    )

    fig = horizontal(
        missing.index,
        missing.values,
        "Missing values in core fields",
        "Share of current non-Superhost listings (%)",
        fmt=prep.format_percent,
    )

    done(fig, "eda_missingness")


# ==================== Plot nightly-price distribution ====================

def plot_price_distribution():

    prices = e.loc[
        e["price_aud"].gt(0),
        "price_aud",
    ].dropna()

    if prices.empty:
        raise ValueError("No positive listed prices are available.")

    cap = prices.quantile(0.99)

    export_table(
        prices.describe(
            percentiles=[0.25, 0.5, 0.75, 0.95, 0.99]
        )
        .rename("Price_AUD")
        .rename_axis("Statistic")
        .reset_index(),
        "eda_price_summary",
    )

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.hist(
        prices.loc[prices.le(cap)],
        bins=42,
        color=TEAL,
        edgecolor="white",
    )

    ax.axvline(
        prices.median(),
        color=GOLD,
        linewidth=2,
        label=f"Median of all positive prices: A${prices.median():.0f}",
    )

    ax.set_title(
        "Distribution of nightly listed prices",
        loc="left",
    )

    ax.set_xlabel("Nightly listed price (AUD)")
    ax.set_ylabel("Number of listings")
    ax.legend()

    fig.text(
        0.12,
        0.01,
        f"Display limited to the 99th percentile: A${cap:,.0f}.",
        fontsize=9,
        color=MUTED,
    )

    fig.tight_layout(rect=[0, 0.04, 1, 1])
    done(fig, "eda_price_distribution")


# ==================== Plot geographic listing distribution ====================

def plot_market_map():

    geo = load_boundaries()

    fig, ax = plt.subplots(figsize=(11, 7))
    draw_base_map(ax, geo)

    for property_group in PROPERTY_ORDER:
        points = e.loc[
            e["property_group"].eq(property_group)
        ].dropna(subset=["longitude", "latitude"])

        ax.scatter(
            points["longitude"],
            points["latitude"],
            s=3,
            alpha=0.5,
            color=PROPERTY_COLORS[property_group],
            linewidths=0,
            zorder=2,
        )

    ax.legend(
        handles=prep.property_legend_handles(),
        loc="upper left",
        fontsize=9,
        frameon=True,
    )

    ax.set_title(
        "Spatial distribution of non-Superhost entire homes",
        loc="left",
        pad=12,
    )

    map_note(
        fig,
        "Boundaries: Inside Airbnb. Listing coordinates are approximate.",
    )

    fig.tight_layout(rect=[0, 0.05, 1, 1])
    done(fig, "01_market_map")


# ==================== Plot supply by area ====================

def plot_area_supply():

    values = area_counts.head(8)

    fig = horizontal(
        values.index,
        values.values,
        "Where are entire-home listings concentrated?",
        "Non-Superhost entire-home listings",
    )

    done(fig, "02_supply")


# ==================== Plot property mix by area ====================

def plot_property_mix():

    data = select_areas(
        property_mix,
        MIX_AREAS,
    ) * 100

    fig, ax = plt.subplots(figsize=(10, 5))
    left = np.zeros(len(data))

    for property_group in PROPERTY_ORDER:
        values = data[property_group].to_numpy()

        bars = ax.barh(
            data.index,
            values,
            left=left,
            height=0.56,
            color=PROPERTY_COLORS[property_group],
            label=property_group,
        )

        for bar, value, start in zip(bars, values, left):
            if value >= 12:
                ax.text(
                    start + value / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{value:.0f}%",
                    ha="center",
                    va="center",
                    color="white",
                    fontweight="bold",
                )

        left += values

    ax.invert_yaxis()
    ax.set_xlim(0, 100)

    ax.set_xlabel("Share of local entire-home supply (%)")

    ax.set_title(
        "Property-type composition differs across areas",
        loc="left",
        pad=15,
    )

    ax.legend(
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
    )

    fig.tight_layout()
    done(fig, "03_property_mix")


# ==================== Plot comparable two-bedroom price map ====================

def plot_comparable_price_map():

    geo = load_boundaries()

    comparable = q.loc[
        q["property_group"].eq("Apartment")
        & q["bedrooms"].eq(2)
        & q["accommodates"].between(4, 5)
    ]

    statistics = comparable.groupby("area")["price_aud"].agg(
        n="size",
        median="median",
    )

    statistics = require_rows(
        statistics.loc[
            statistics["n"].ge(prep.MIN_MAP_COMPARABLES)
        ],
        "comparable price map",
    )

    export_table(
        statistics.reset_index(),
        "07_twobed_map_comparables",
    )

    lower = statistics["median"].min()
    upper = statistics["median"].max()

    if lower == upper:
        lower -= 1
        upper += 1

    norm = Normalize(vmin=lower, vmax=upper)
    cmap = mpl.colormaps["YlGnBu"]

    fig, ax = plt.subplots(figsize=(11, 7))

    draw_base_map(
        ax,
        geo,
        values=statistics["median"].to_dict(),
        cmap=cmap,
        norm=norm,
        extent=[144.77, 145.21, -37.95, -37.67],
    )

    # ==================== Find interior label positions from area boundaries ====================

    x_min, x_max = sorted(ax.get_xlim())
    y_min, y_max = sorted(ax.get_ylim())

    visible_extent = box(
        x_min,
        y_min,
        x_max,
        y_max,
    )

    area_geometries = {}

    for feature in geo["features"]:

        area = boundary_name(feature)

        if area not in statistics.index:
            continue

        geometry_data = feature.get("geometry")

        if geometry_data is None:
            continue

        geometry = shape(geometry_data)

        if not geometry.is_valid:
            geometry = geometry.buffer(0)

        if geometry.is_empty:
            continue

        area_geometries.setdefault(area, []).append(geometry)


    # ==================== Place labels inside the visible area polygons ====================

    for area, geometries in area_geometries.items():

        geometry = unary_union(geometries)

        visible_geometry = geometry.intersection(
            visible_extent
        )

        if visible_geometry.is_empty:
            continue

        if visible_geometry.geom_type == "Polygon":
            polygons = [visible_geometry]

        elif visible_geometry.geom_type in [
            "MultiPolygon",
            "GeometryCollection",
        ]:
            polygons = [
                part
                for part in visible_geometry.geoms
                if part.geom_type == "Polygon"
                and not part.is_empty
            ]

        else:
            continue

        if not polygons:
            continue

        # Use the largest visible polygon for areas with multiple parts.
        main_polygon = max(
            polygons,
            key=lambda polygon: polygon.area,
        )

        # Locate an interior point with maximum boundary clearance.
        label_point = polylabel(
            main_polygon,
            tolerance=0.0001,
        )

        median_price = statistics.loc[
            area,
            "median",
        ]

        ax.text(
            label_point.x,
            label_point.y,
            f"{area}\nA${median_price:.0f}",
            ha="center",
            va="center",
            multialignment="center",
            fontsize=8,
            fontweight="medium",
            color=NAVY,
            zorder=4,
            bbox={
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.85,
                "pad": 2,
            },
        )
        
    colorbar = fig.colorbar(
        mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
        ax=ax,
        fraction=0.036,
        pad=0.02,
        shrink=0.76,
    )

    colorbar.set_label("Median nightly listed price (AUD)")

    ax.set_title(
        "Comparable two-bedroom apartment prices by area",
        loc="left",
        pad=14,
    )

    map_note(
        fig,
        "Non-Superhost apartments; capacity 4-5; "
        "at least 30 listings per area. Gray indicates insufficient data.",
    )

    fig.tight_layout(rect=[0, 0.05, 1, 1])
    done(fig, "04_comparable_price_map")


# ==================== Plot one-bedroom apartment prices ====================

def plot_onebed_prices():

    data = onebed_apartments()

    labels = [
        f"{area} | n={int(row['n'])}"
        for area, row in data.iterrows()
    ]

    fig = horizontal(
        labels,
        data["median"].values,
        "One-bedroom apartment listed prices",
        "Median nightly listed price (AUD)",
        colors=[
            TEAL if area == "Yarra" else GRAY
            for area in data.index
        ],
        fmt=prep.format_aud,
    )

    done(fig, "05_onebed_price")


# ==================== Plot one-bedroom review activity ====================

def plot_onebed_reviews():

    data = onebed_apartments()

    labels = [
        f"{area} | historical n={int(row['mature_n'])}"
        for area, row in data.iterrows()
    ]

    fig = horizontal(
        labels,
        data["reviews"].values,
        "One-bedroom apartment review activity",
        "Median reviews per listing in the observation year",
        colors=[
            TEAL if area == "Yarra" else GRAY
            for area in data.index
        ],
        fmt=lambda value: f"{value:.1f}",
    )

    done(fig, "06_onebed_reviews")


# ==================== Plot apartment prices by bedroom count ====================

def plot_size_prices():

    data = sc.loc[
        sc["area"].isin(["Melbourne", "Yarra"])
        & sc["property_group"].eq("Apartment")
        & sc["bedrooms"].isin([1, 2])
    ]

    table = data.pivot(
        index="area",
        columns="bedrooms",
        values="median",
    ).reindex(
        index=["Melbourne", "Yarra"],
        columns=[1, 2],
    )

    table.columns = [
        "1-bedroom apartment",
        "2-bedroom apartment",
    ]

    fig = grouped_bar(
        table,
        "Apartment prices by bedroom count",
        ylabel="Median nightly listed price (AUD)",
        colors=[TEAL, GOLD],
    )

    done(fig, "07_size_price")


# ==================== Plot listed price per guest capacity ====================

def plot_price_per_person():

    data = require_rows(
        sc.loc[
            sc["area"].eq("Melbourne")
            & sc["property_group"].eq("Apartment")
            & sc["bedrooms"].isin([1, 2, 3])
            & sc["capacity"].gt(0)
        ].sort_values("bedrooms"),
        "price per guest capacity",
    ).copy()

    data["Price_per_capacity"] = (
        data["median"] / data["capacity"]
    )

    labels = [
        f"{int(row['bedrooms'])} bedrooms | "
        f"median capacity {row['capacity']:g}"
        for _, row in data.iterrows()
    ]

    fig = horizontal(
        labels,
        data["Price_per_capacity"].values,
        "Listed price relative to guest capacity",
        "Median listed price / median capacity (AUD per person per night)",
        fmt=prep.format_aud,
    )

    done(fig, "08_per_person")

    export_table(
        data,
        "08_price_per_capacity",
    )


# ==================== Plot transport and nature review themes ====================

def plot_review_themes():

    table = select_areas(
        theme_rates,
        ["Melbourne", "Yarra Ranges"],
    )[
        ["Walking_transport", "Quiet_nature"]
    ].T

    table.index = [
        THEME_LABELS[column]
        for column in table.index
    ]

    fig = grouped_bar(
        table,
        "Transport and nature mentions in reviews",
        ylabel="Share of non-missing comments (%)",
        colors=[TEAL, GOLD],
        value_format="{:.1f}%",
    )

    done(fig, "09_review_themes")


# ==================== Plot family-related review mentions ====================

def plot_family_mentions():

    data = select_areas(
        theme_rates,
        AREAS,
    )["Family_children"]

    fig = horizontal(
        data.index,
        data.values,
        "Family-related mentions by area",
        "Share of non-missing comments mentioning family keywords (%)",
        colors=[
            GOLD if area == "Yarra Ranges" else GRAY
            for area in data.index
        ],
        fmt=prep.format_percent,
    )

    done(fig, "10_family_mentions")


# ==================== Plot pool listing rates ====================

def plot_pool_rates():

    data = (
        select_areas(amenity_rates, MIX_AREAS)["Pool"]
        * 100
    )

    fig = horizontal(
        data.index,
        data.values,
        "Pool listing rates by area",
        "Share of entire-home listings explicitly listing a pool (%)",
        colors=[
            TEAL if area == "Melbourne" else GRAY
            for area in data.index
        ],
        fmt=prep.format_percent,
    )

    done(fig, "11_pool")


# ==================== Plot retreat-related amenities ====================

def plot_retreat_amenities():

    table = (
        select_areas(
            amenity_rates,
            ["Melbourne", "Yarra Ranges"],
        )[
            ["Fireplace", "Free_parking", "Garden"]
        ].T
        * 100
    )

    table.index = [
        AMENITY_LABELS[column]
        for column in table.index
    ]

    fig = grouped_bar(
        table,
        "Fireplace, parking, and outdoor-space listing rates",
        ylabel="Share of entire-home listings (%)",
        colors=[TEAL, GOLD],
        value_format="{:.0f}%",
    )

    done(fig, "12_retreat_amenities")


# ==================== Plot two-night calendar-rule compatibility ====================

def plot_two_night_rules():

    data = load_output(
        ["calendar_summary.csv"],
        required_columns=[
            "area",
            "days",
            "available",
            "accept_2",
        ],
    )

    data["accept_2_share"] = (
        data["accept_2"]
        / data["available"].replace(0, np.nan)
    )

    values = (
        select_areas(
            data.set_index("area"),
            AREAS,
        )["accept_2_share"]
        * 100
    )

    fig = horizontal(
        values.index,
        values.values,
        "Two-night stays permitted by daily calendar rules",
        "Share of available listing-dates permitting two nights (%)",
        colors=[
            GOLD if area == "Yarra Ranges" else GRAY
            for area in values.index
        ],
        fmt=prep.format_percent,
    )

    done(fig, "13_two_nights")


# ==================== Plot monthly review activity ====================

def plot_monthly_reviews():

    cohort = q.loc[
        q["mature"].fillna(False)
        & q["area"].isin(REVIEW_TREND_AREAS)
    ]

    require_rows(cohort, "monthly review activity")

    data = rvm.rename("reviews").reset_index()

    data = data.merge(
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

    denominators = cohort.groupby("area").size()

    areas = [
        area
        for area in REVIEW_TREND_AREAS
        if area in denominators.index
    ]

    table = (
        data.groupby(["month", "area"])["reviews"]
        .sum()
        .unstack("area")
        .reindex(index=months, columns=areas)
        .fillna(0)
        .div(denominators.reindex(areas), axis=1)
        * 100
    )

    export_table(
        table.rename_axis("Month").reset_index(),
        "06_monthly_reviews_per100",
    )

    fig, ax = plt.subplots(figsize=(11, 5))

    for area in areas:
        ax.plot(
            np.arange(len(table)),
            table[area],
            marker="o",
            markersize=4,
            linewidth=2,
            label=area,
            color=AREA_COLORS[area],
        )

    ax.set_xticks(
        np.arange(len(table)),
        [month[2:].replace("-", "/") for month in months],
    )

    ax.set_ylabel("New reviews per 100 cohort listings")

    ax.set_title(
        "Monthly review activity in a fixed historical cohort",
        loc="left",
        pad=15,
    )

    ax.legend(
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
    )

    style_axis(ax, grid_axis="y")

    fig.tight_layout()
    done(fig, "14_monthly_reviews")


# ==================== Load model test results ====================

def model_test_results():
    """
    Expected row order:
    global median, area-bedroom median, selected model.
    The original analysis exports test.csv in this order.
    """

    table = load_output(
        ["test.csv"],
        required_columns=[
            "within25",
            "MedAE",
        ],
    )

    if len(table) != 3:
        raise ValueError(
            "test.csv must contain the three original evaluation rows "
            "in global-median, area-bedroom-median, selected-model order."
        )

    table = table.copy()

    table["Method"] = [
        "Global median",
        "Area-bedroom median",
        "Selected model",
    ]

    return table.set_index("Method")


# ==================== Plot model price-match rates ====================

def plot_model_match():

    data = model_test_results()

    fig = horizontal(
        data.index,
        data["within25"].values * 100,
        "Predictions within 25% of recorded listed prices",
        "Listings per 100 test listings",
        colors=[GRAY, BLUE, TEAL],
        fmt=lambda value: f"{value:.1f}",
    )

    done(fig, "15_model_match")


# ==================== Plot median absolute prediction errors ====================

def plot_model_error():

    data = model_test_results()

    fig = horizontal(
        data.index,
        data["MedAE"].values,
        "Typical nightly listed-price prediction error",
        "Median absolute error (AUD per night; lower is better)",
        colors=[GRAY, BLUE, TEAL],
        fmt=lambda value: f"A${value:.1f}",
    )

    done(fig, "16_model_error")


# ==================== Plot permutation feature importance ====================

def plot_model_drivers():

    data = load_output(
        ["importance.csv"],
        required_columns=[
            "feature",
            "value",
        ],
    )

    data = require_rows(
        data.sort_values(
            "value",
            ascending=False,
        ).head(6),
        "permutation importance",
    )

    labels = [
        FEATURE_LABELS.get(feature, feature)
        for feature in data["feature"]
    ]

    fig = horizontal(
        labels,
        data["value"].values,
        "Features contributing to listed-price prediction",
        "Increase in validation MAE after permutation (AUD)",
        fmt=lambda value: f"{value:.2f}",
    )

    done(fig, "17_model_drivers")


# ==================== Load selected product candidates ====================

def selected_candidates():

    return require_rows(
        load_output(
            ["prescriptive_selected_plans.csv"],
            required_columns=[
                "area",
                "property_group",
                "bedrooms",
                "matched_median",
                "launch",
                "n",
                "reviews",
            ],
        ),
        "selected candidates",
    )


# ==================== Plot candidate price benchmarks ====================

def plot_recommended_prices():

    data = selected_candidates()

    table = data[
        ["matched_median", "launch"]
    ].copy()

    table.index = [
        f"{row['area']}\n"
        f"{int(row['bedrooms'])}-bedroom "
        f"{row['property_group']}"
        for _, row in data.iterrows()
    ]

    table.columns = [
        "Matched two-night peer median",
        "Historical trial-price benchmark",
    ]

    fig = grouped_bar(
        table,
        "Price benchmarks for selected product candidates",
        ylabel="AUD per night",
        colors=[GRAY, TEAL],
        figsize=(12, 6),
    )

    done(fig, "18_recommended_prices")


# ==================== Plot selected product areas ====================

def plot_decision_map():

    geo = load_boundaries()
    data = selected_candidates()

    unique_areas = data["area"].drop_duplicates().tolist()

    colors = {
        area: [TEAL, BLUE, GOLD, RED][i % 4]
        for i, area in enumerate(unique_areas)
    }

    points = e.loc[
        e["area"].isin(unique_areas)
    ].dropna(subset=["longitude", "latitude"])

    require_rows(points, "candidate-area map")

    longitude_min = points["longitude"].min()
    longitude_max = points["longitude"].max()
    latitude_min = points["latitude"].min()
    latitude_max = points["latitude"].max()

    longitude_padding = max(
        (longitude_max - longitude_min) * 0.15,
        0.03,
    )

    latitude_padding = max(
        (latitude_max - latitude_min) * 0.15,
        0.03,
    )

    extent = [
        longitude_min - longitude_padding,
        longitude_max + longitude_padding,
        latitude_min - latitude_padding,
        latitude_max + latitude_padding,
    ]

    fig, (ax, notes) = plt.subplots(
        1,
        2,
        figsize=(13, max(6, len(data) * 1.7)),
        gridspec_kw={
            "width_ratios": [1, 1.15],
        },
    )

    draw_base_map(
        ax,
        geo,
        highlights=colors,
        extent=extent,
    )

    for area in unique_areas:
        local_points = points.loc[
            points["area"].eq(area)
        ]

        if local_points.empty:
            continue

        ax.text(
            local_points["longitude"].median(),
            local_points["latitude"].median(),
            area,
            ha="center",
            fontsize=10,
            zorder=3,
            bbox={
                "facecolor": "white",
                "edgecolor": colors[area],
                "pad": 4,
            },
        )

    notes.axis("off")

    step = 0.85 / max(len(data), 1)

    for i, (_, row) in enumerate(data.iterrows()):
        text = (
            f"Candidate {i + 1}: {row['area']}\n"
            f"{int(row['bedrooms'])}-bedroom "
            f"{row['property_group']}\n"
            f"Trial-price benchmark: A${row['launch']:.0f}/night\n"
            f"Comparable listings: {int(row['n'])}\n"
            f"Historical annual review median: {row['reviews']:g}"
        )

        notes.text(
            0.03,
            0.95 - i * step,
            text,
            transform=notes.transAxes,
            fontsize=10,
            va="top",
            linespacing=1.6,
            bbox={
                "facecolor": "#F0F6F5",
                "edgecolor": colors[row["area"]],
                "boxstyle": "round,pad=0.6",
            },
        )

    ax.set_title(
        "Areas containing selected candidates",
        loc="left",
    )

    notes.set_title(
        "Product candidates and reference prices",
        loc="left",
    )

    map_note(
        fig,
        "Boundaries: Inside Airbnb. Historical price benchmarks; "
        "candidate selection is not a profit ranking.",
    )

    fig.tight_layout(rect=[0, 0.06, 1, 1])
    done(fig, "19_decision_map")


# ==================== Plot rating groups and estimated revenue ====================

def plot_rating_revenue():

    data = rating_sample()

    prep.check_columns(
        data,
        ["estimated_revenue_l365d"],
        "Rating sample",
    )

    data["Rating_group"] = pd.cut(
        data["review_scores_rating"],
        bins=[0, 4.5, 4.8, 5],
        labels=prep.RATING_ORDER,
    )

    summary = data.groupby(
        "Rating_group",
        observed=True,
    ).agg(
        Listings=("id", "size"),
        Valid_revenue_observations=(
            "estimated_revenue_l365d",
            "count",
        ),
        Median_listed_price_AUD=("price_aud", "median"),
        Median_estimated_annual_revenue_AUD=(
            "estimated_revenue_l365d",
            "median",
        ),
        Median_annual_reviews=("recent_reviews", "median"),
    )

    summary = summary.reindex(prep.RATING_ORDER)

    export_table(
        summary.reset_index(),
        "rating_summary",
    )

    labels = [
        f"{group} | valid revenue n="
        f"{int(row['Valid_revenue_observations'])}"
        for group, row in summary.iterrows()
    ]

    fig = horizontal(
        labels,
        summary["Median_estimated_annual_revenue_AUD"].values,
        "Estimated annual revenue across rating groups",
        "Median estimated annual revenue (AUD; not actual revenue or profit)",
        colors=[GRAY, TEAL, BLUE],
        fmt=prep.format_aud,
        figsize=(12, 5),
    )

    done(fig, "20_rating_estimated_revenue")


# ==================== Plot service-score priorities ====================

def plot_service_priorities():

    data = rating_sample()
    rows = []

    for column, label in SCORE_LABELS.items():
        if column not in data.columns:
            continue

        values = data.loc[
            data[column].between(1, 5),
            column,
        ].dropna()

        if values.empty:
            continue

        rows.append(
            {
                "Service": label,
                "Valid_listings": len(values),
                "Median_score": values.median(),
                "Below_4_5_pct": values.lt(4.5).mean() * 100,
            }
        )

    summary = require_rows(
        pd.DataFrame(rows),
        "service-score priorities",
    ).sort_values(
        "Below_4_5_pct",
        ascending=False,
    )

    export_table(
        summary,
        "service_priority",
    )

    fig = horizontal(
        summary["Service"],
        summary["Below_4_5_pct"].values,
        "Service dimensions with ratings below 4.5",
        "Share of valid scores below 4.5 (%)",
        fmt=prep.format_percent,
    )

    done(fig, "21_service_priorities")


# ==================== Plot facility listing evidence ====================

def plot_facility_evidence():

    labels = {
        "Air_conditioning": "Air conditioning",
        "Wifi": "Wi-Fi",
        "Self_check_in": "Self check-in",
        "Air_purifier_listed": "Air purifier",
    }

    prep.check_columns(
        q,
        list(labels),
        "Price-model sample",
    )

    summary = pd.DataFrame(
        [
            {
                "Facility": label,
                "Listed_count": int(q[column].eq(1).sum()),
                "Sample_size": len(q),
                "Listed_pct": q[column].eq(1).mean() * 100,
            }
            for column, label in labels.items()
        ]
    )

    export_table(
        summary,
        "facility_evidence",
    )

    fig = horizontal(
        summary["Facility"],
        summary["Listed_pct"].values,
        "Facilities explicitly listed in the model sample",
        "Share of listings explicitly listing the facility (%)",
        fmt=prep.format_percent,
    )

    done(fig, "22_facility_evidence")


# ==================== Run all chart functions ====================

CHARTS = [
    ("00_analysis_framework", plot_analysis_framework),
    ("eda_host_scope", plot_host_scope),
    ("eda_missingness", plot_missingness),
    ("eda_price_distribution", plot_price_distribution),
    ("01_market_map", plot_market_map),
    ("02_supply", plot_area_supply),
    ("03_property_mix", plot_property_mix),
    ("04_comparable_price_map", plot_comparable_price_map),
    ("05_onebed_price", plot_onebed_prices),
    ("06_onebed_reviews", plot_onebed_reviews),
    ("07_size_price", plot_size_prices),
    ("08_per_person", plot_price_per_person),
    ("09_review_themes", plot_review_themes),
    ("10_family_mentions", plot_family_mentions),
    ("11_pool", plot_pool_rates),
    ("12_retreat_amenities", plot_retreat_amenities),
    ("13_two_nights", plot_two_night_rules),
    ("14_monthly_reviews", plot_monthly_reviews),
    ("15_model_match", plot_model_match),
    ("16_model_error", plot_model_error),
    ("17_model_drivers", plot_model_drivers),
    ("18_recommended_prices", plot_recommended_prices),
    ("19_decision_map", plot_decision_map),
    ("20_rating_estimated_revenue", plot_rating_revenue),
    ("21_service_priorities", plot_service_priorities),
    ("22_facility_evidence", plot_facility_evidence),
]


# ==================== Save chart-generation report ====================

def main():

    chart_results.clear()

    for name, function in CHARTS:
        run_chart(name, function)

    report = pd.DataFrame(chart_results)

    export_table(
        report,
        "chart_generation_report",
    )

    saved = report["Status"].eq("Saved").sum()
    skipped = report["Status"].eq("Skipped").sum()

    print()
    print("Chart generation completed.")
    print(f"Saved charts: {saved}")
    print(f"Skipped charts: {skipped}")
    print(f"Figure directory: {F}")
    print(f"Table directory: {T}")


# ==================== Run script ====================

if __name__ == "__main__":
    main()
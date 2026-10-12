#This part will be used to define how we will draw our graphs and install drawing tools
"""Shared chart preparation and plotting utilities."""

from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt

from matplotlib.patches import Polygon, Patch
from matplotlib.colors import Normalize

import ssl
import sys
import subprocess
import importlib.util

# Install the certificate package if missing.
if importlib.util.find_spec("certifi") is None:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "certifi"
    ])

import certifi


# ==================== Local folders ====================

# Place this script in the project's data folder.
PROJECT_FOLDER = Path(__file__).resolve().parent.parent

OUT = PROJECT_FOLDER / "analysis_outputs"
T = OUT / "tables"
F = OUT / "figures"

MODEL_FOLDER = OUT / "models"
ASSET = PROJECT_FOLDER / "map"

for folder in [T, F, ASSET]:
    folder.mkdir(parents=True, exist_ok=True)

# ==================== Colors and labels ====================

NAVY = "#183C4A"
TEAL = "#168A85"
GOLD = "#D58A39"
BLUE = "#5386AF"
RED = "#BA5E4B"

MUTED = "#617580"
PALE = "#EAF1F2"
GRAY = "#C9D2D5"

# Match the property groups created by Data_overview.py.
COLORS = {
    "Apartment": TEAL,
    "House/Townhouse": BLUE,
    "Cottage/Guesthouse": GOLD,
    "Other": GRAY
}

AREAS = [
    "Melbourne",
    "Yarra",
    "Port Phillip",
    "Stonnington",
    "Yarra Ranges"
]

AMENITIES = [
    "Wifi",
    "Kitchen",
    "Free parking",
    "Self check-in",
    "Pool",
    "Fireplace",
    "Hot tub",
    "Pets allowed",
    "Workspace",
    "BBQ",
    "Garden",
    "Air conditioning"
]

REVIEW_THEMES = [
    "Walking/Transport",
    "Quiet/Nature",
    "Family/Children",
    "Couples/Celebrations",
    "Work/Business"
]

FEATURE_LABELS = {
    "bedrooms": "Bedrooms",
    "accommodates": "Guest capacity",
    "bath_num": "Bathrooms",
    "area": "Area",
    "property_group": "Property type",
    "minimum_nights": "Minimum stay",
    "quote_nights": "Quoted stay length",
    "quote_lead": "Booking lead time",
    "quote_weekend": "Weekend check-in",
    "quote_month": "Check-in month"
}


# ==================== Read saved results ====================

def read_saved_table(filename, **kwargs):
    """Read an existing CSV result from the local tables folder."""
    path = T / filename

    if not path.is_file():
        raise FileNotFoundError(
            f"Required table not found: {path}. "
            "Run the corresponding preparation or modeling script first."
        )

    return pd.read_csv(path, **kwargs)


def load_chart_data():
    """Load persisted results without relying on another script's variables."""
    entire_listings = read_saved_table(
        "entire_home_listings.csv",
        dtype={
            "id": "string",
            "host_id": "string",
            "mature": "boolean",
            "has_review": "boolean"
        },
        low_memory=False
    )

    modeling_sample = read_saved_table(
        "modeling_sample.csv",
        dtype={
            "id": "string",
            "host_id": "string",
            "mature": "boolean",
            "has_review": "boolean"
        },
        low_memory=False
    )

    monthly_reviews = read_saved_table(
        "monthly_reviews.csv",
        dtype={"listing_id": "string", "month": "string"}
    )

    metadata_path = MODEL_FOLDER / "model_meta.json"

    if not metadata_path.is_file():
        raise FileNotFoundError(
            f"Model metadata not found: {metadata_path}. "
            "Run Price_model.py first."
        )

    return {
        "entire_listings": entire_listings,
        "modeling_sample": modeling_sample,
        "monthly_reviews": monthly_reviews,
        "calendar_summary": read_saved_table(
            "calendar_summary.csv",
            index_col="area"
        ),
        "scenarios": read_saved_table("scenarios.csv"),
        "selected_plans": read_saved_table("09_selected_plans.csv"),
        "importance": read_saved_table("importance.csv"),
        "validation": read_saved_table("validation.csv", index_col=0),
        "test": read_saved_table("test.csv", index_col=0),
        "model_meta": json.loads(
            metadata_path.read_text(encoding="utf-8")
        )
    }


# ==================== Plot styling ====================

def style_charts():
    """Apply a consistent English-language chart style."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.unicode_minus": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.edgecolor": "#C5D1D4",
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": NAVY,
        "text.color": NAVY,
        "text.parse_math": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white"
    })


def done(fig, name, show=False):
    """Save a figure to disk and optionally display it."""
    path = F / f"{name}.png"

    fig.savefig(
        path,
        dpi=165,
        bbox_inches="tight"
    )

    if show:
        plt.show()

    plt.close(fig)
    return path


def horizontal(
    labels,
    values,
    title,
    unit="",
    colors=None,
    fmt=None,
    figsize=(9.2, 4.3)
):
    """Create a horizontal bar chart without saving or displaying it."""
    labels = list(labels)
    values = np.asarray(values, dtype=float)

    if len(labels) != len(values) or len(values) == 0:
        raise ValueError(
            "Labels and values must have the same nonzero length."
        )

    if not np.isfinite(values).all():
        raise ValueError("Chart values must be finite numbers.")

    fig, ax = plt.subplots(figsize=figsize)

    bars = ax.barh(
        labels,
        values,
        color=TEAL if colors is None else colors,
        height=0.58
    )

    ax.invert_yaxis()
    ax.set_title(title, loc="left", fontweight="bold", pad=18)
    ax.set_xlabel(unit)
    ax.grid(axis="x", alpha=0.14)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, pad=10)

    lower = min(0.0, float(values.min()))
    upper = max(0.0, float(values.max()))
    span = upper - lower if upper > lower else 1.0
    padding = span * 0.025

    ax.set_xlim(
        lower - span * 0.15 if lower < 0 else 0,
        upper + span * 0.24
    )

    for bar, value in zip(bars, values):
        label = fmt(value) if fmt else f"{value:,.0f}"

        ax.text(
            value + padding if value >= 0 else value - padding,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            ha="left" if value >= 0 else "right",
            fontweight="bold",
            fontsize=11
        )

    fig.tight_layout()
    return fig


def export_table(dataframe, name):
    """Save a chart's supporting table to disk."""
    path = T / f"{name}.csv"

    dataframe.to_csv(
        path,
        index=False,
        encoding="utf-8-sig"
    )

    return path


# ==================== Optional map preparation ====================

def load_map_boundaries():
    """Read locally saved Inside Airbnb neighborhood boundaries."""
    path = ASSET / "neighbourhoods.geojson"

    if not path.is_file():
        raise FileNotFoundError(
            f"Map boundaries not found: {path}. "
            "Save neighbourhoods.geojson in the project's assets folder "
            "before creating maps."
        )

    return json.loads(path.read_text(encoding="utf-8"))


def polygon_rings(feature):
    """Return exterior rings for Polygon or MultiPolygon geometry."""
    geometry = feature.get("geometry")

    if geometry is None:
        return []

    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        return []

    return [polygon[0] for polygon in polygons if polygon]


def base_map(
    ax,
    geo,
    values=None,
    cmap=None,
    norm=None,
    highlights=None,
    extent=None
):
    """Draw neighborhood boundaries using explicitly supplied map data."""
    if values is not None and (cmap is None or norm is None):
        raise ValueError(
            "A color map and normalization are required for mapped values."
        )

    for feature in geo["features"]:
        name = feature["properties"]["neighbourhood"]
        color = "#EFF2F0"

        if values is not None:
            value = values.get(name)

            color = (
                cmap(norm(value))
                if value is not None and pd.notna(value)
                else "#E0E5E6"
            )

        if highlights is not None:
            color = highlights.get(name, color)

        for ring in polygon_rings(feature):
            ax.add_patch(Polygon(
                ring,
                closed=True,
                facecolor=color,
                edgecolor="white",
                linewidth=0.8,
                zorder=1
            ))

    bounds = (
        extent if extent is not None
        else [144.38, 146.23, -38.13, -37.39]
    )

    ax.set_xlim(bounds[0], bounds[1])
    ax.set_ylim(bounds[2], bounds[3])
    ax.set_aspect(1 / np.cos(np.deg2rad(37.8)))

    ax.set_facecolor("#F7FAFB")
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
        fontsize=10,
        arrowprops={"arrowstyle": "->", "color": NAVY},
        color=NAVY
    )


def map_source(
    fig,
    text=(
        "Boundaries: Inside Airbnb, 2026-06-16. "
        "Listing coordinates are approximate."
    )
):
    """Add a source note to a map."""
    fig.text(0.03, 0.015, text, fontsize=8, color=MUTED)


# Apply styling only; no data loading or chart generation occurs here.
style_charts()

#Below is downloading the map of Melbourne for our analysis later
"""Download and validate Melbourne neighborhood map boundaries."""

from pathlib import Path
import json
import urllib.request

# Place this script in the project's data folder.
PROJECT_FOLDER = Path(__file__).resolve().parent.parent
ASSET_FOLDER = PROJECT_FOLDER / "map"
ASSET_FOLDER.mkdir(parents=True, exist_ok=True)

MAP_FILE = ASSET_FOLDER / "neighbourhoods.geojson"

# Match the June 2026 snapshot used in the analysis.
MAP_URL = (
    "https://data.insideairbnb.com/"
    "australia/vic/melbourne/2026-06-16/"
    "visualisations/neighbourhoods.geojson"
)


def validate_boundaries(content):
    """Check that the file contains usable neighborhood boundaries."""
    geo = json.loads(content)

    if geo.get("type") != "FeatureCollection":
        raise ValueError("The downloaded file is not a GeoJSON FeatureCollection.")

    features = geo.get("features", [])

    if not features:
        raise ValueError("The map contains no boundary features.")

    for feature in features:
        if not feature.get("properties", {}).get("neighbourhood"):
            raise ValueError("A boundary is missing its neighborhood name.")

        geometry = feature.get("geometry") or {}

        if geometry.get("type") not in ["Polygon", "MultiPolygon"]:
            raise ValueError("A boundary contains unsupported geometry.")

        if not geometry.get("coordinates"):
            raise ValueError("A boundary contains no coordinates.")

    return geo


def main():
    if MAP_FILE.is_file():
        geo = validate_boundaries(
            MAP_FILE.read_text(encoding="utf-8")
        )
        print(f"Existing map validated: {MAP_FILE}")
    else:
        print(f"Downloading map boundaries from: {MAP_URL}")

        request = urllib.request.Request(
            MAP_URL,
            headers={"User-Agent": "Melbourne-Airbnb-Analysis/1.0"}
        )

        # Use a trusted CA certificate bundle for HTTPS verification.
        ssl_context = ssl.create_default_context(
            cafile=certifi.where()
        )

        with urllib.request.urlopen(
            request,
            timeout=60,
            context=ssl_context
        ) as response:
            content = response.read().decode("utf-8-sig")

        geo = validate_boundaries(content)

        MAP_FILE.write_text(
            json.dumps(geo, ensure_ascii=False),
            encoding="utf-8"
        )

        print(f"Map boundaries saved to: {MAP_FILE}")

    names = sorted({
        feature["properties"]["neighbourhood"]
        for feature in geo["features"]
    })

    print(f"Neighborhood boundaries: {len(geo['features'])}")
    print("Available areas:")
    print(", ".join(names))
    print("Map preparation completed. Run Business_charts.py next.")


if __name__ == "__main__":
    main()




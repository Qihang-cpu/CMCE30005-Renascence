#This will be the process that using the method that defined in the Graph_preparation part and make data visualization 
#of our project 
"""Generate business charts from saved local analysis results."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

from matplotlib.patches import Patch
from matplotlib.colors import Normalize

from Graph_preparation import (
    NAVY, TEAL, GOLD, BLUE, MUTED, GRAY,
    COLORS, AREAS, AMENITIES, REVIEW_THEMES, FEATURE_LABELS,
    ASSET, F,
    load_chart_data, load_map_boundaries,
    horizontal, done, export_table, base_map, map_source
)


# ==================== Supporting summaries ====================

def profile_tables(listings):
    """Summarize supply, property types, amenities, and review themes."""
    counts = (
        listings.groupby("area")
        .size()
        .sort_values(ascending=False)
    )

    mix = pd.crosstab(
        listings["area"],
        listings["property_group"],
        normalize="index"
    ).reindex(columns=list(COLORS), fill_value=0)

    amenities = listings.groupby("area")[AMENITIES].mean()

    denominators = listings.groupby("area")["text_n"].sum()

    themes = (
        listings.groupby("area")[REVIEW_THEMES]
        .sum()
        .div(denominators.replace(0, np.nan), axis=0)
        * 100
    )

    export_table(
        counts.rename("entire_home_listings")
        .rename_axis("area")
        .reset_index(),
        "01_supply"
    )

    export_table(
        (mix * 100).round(2).reset_index(),
        "02_property_mix_pct"
    )

    export_table(
        (amenities * 100).round(2).reset_index(),
        "03_amenities_pct"
    )

    export_table(
        themes.round(2).reset_index(),
        "04_review_themes_pct"
    )

    export_table(
        denominators.rename("nonempty_reviews").reset_index(),
        "04_review_theme_denominators"
    )

    return counts, mix, amenities, themes


def finish_axes(ax, title, ylabel):
    """Apply shared formatting to vertical charts."""
    ax.set_title(title, loc="left", fontweight="bold", pad=16)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.14)
    ax.set_axisbelow(True)


# ==================== Market supply ====================

def market_charts(counts, mix):
    top = counts.head(8)

    done(
        horizontal(
            top.index,
            top.values,
            "Where are entire-home listings concentrated?",
            "Entire-home listings in the current city scrape"
        ),
        "02_supply"
    )

    chosen = [
        area for area in
        ["Melbourne", "Yarra", "Port Phillip", "Yarra Ranges"]
        if area in mix.index
    ]

    if not chosen:
        return

    composition = mix.loc[chosen] * 100

    fig, ax = plt.subplots(figsize=(10, 4.8))
    left = np.zeros(len(composition))

    for group in composition.columns:
        values = composition[group].to_numpy()

        bars = ax.barh(
            composition.index,
            values,
            left=left,
            label=group,
            color=COLORS[group],
            height=0.54
        )

        for bar, value, offset in zip(bars, values, left):
            if value >= 12:
                ax.text(
                    offset + value / 2,
                    bar.get_y() + bar.get_height() / 2,
                    f"{value:.0f}%",
                    ha="center",
                    va="center",
                    color="white",
                    fontweight="bold"
                )

        left += values

    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of local entire-home listings (%)")
    ax.set_title(
        "Property composition differs across areas",
        loc="left",
        fontweight="bold",
        pad=16
    )
    ax.legend(
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.18),
        frameon=False
    )
    ax.tick_params(axis="y", length=0)

    fig.tight_layout()
    done(fig, "03_property_mix")


# ==================== Urban product comparisons ====================

def urban_charts(scenarios):
    urban = scenarios.loc[
        scenarios["bedrooms"].eq(1)
        & scenarios["property_group"].eq("Apartment")
        & scenarios["area"].isin(AREAS[:4])
    ].set_index("area").reindex(AREAS[:4]).dropna(subset=["n"])

    if not urban.empty:
        labels = [
            f"{area} · n={int(row['n'])}"
            for area, row in urban.iterrows()
        ]

        done(
            horizontal(
                labels,
                urban["median"],
                "One-bedroom apartments: comparable listing prices",
                "Median nightly listing price (AUD)",
                colors=[
                    TEAL if area == "Yarra" else GRAY
                    for area in urban.index
                ]
            ),
            "05_onebed_price"
        )

        review_sample = urban.dropna(subset=["reviews"])

        if not review_sample.empty:
            labels = [
                f"{area} · n={int(row['mature_n'])}"
                for area, row in review_sample.iterrows()
            ]

            done(
                horizontal(
                    labels,
                    review_sample["reviews"],
                    "One-bedroom apartments: historical review activity",
                    "Median annual reviews per listing with sufficient history",
                    colors=[
                        TEAL if area == "Yarra" else GRAY
                        for area in review_sample.index
                    ]
                ),
                "06_onebed_reviews"
            )

        export_table(
            urban[
                ["n", "mature_n", "median", "reviews", "active"]
            ].round(3).reset_index(),
            "05_urban_onebed_comparison"
        )

    comparison = scenarios.loc[
        scenarios["area"].isin(["Melbourne", "Yarra"])
        & scenarios["bedrooms"].isin([1, 2])
        & scenarios["property_group"].eq("Apartment")
    ]

    if not comparison.empty:
        prices = comparison.pivot(
            index="area",
            columns="bedrooms",
            values="median"
        ).reindex(["Melbourne", "Yarra"]).dropna(how="all")

        fig, ax = plt.subplots(figsize=(9.2, 4.6))
        positions = np.arange(len(prices))
        width = 0.3

        for index, bedrooms in enumerate([1, 2]):
            if bedrooms not in prices.columns:
                continue

            bars = ax.bar(
                positions + (index - 0.5) * width,
                prices[bedrooms],
                width,
                color=[TEAL, GOLD][index],
                label=f"{bedrooms}-bedroom apartment"
            )
            ax.bar_label(bars, fmt="%.0f", padding=5)

        ax.set_xticks(positions, prices.index)
        finish_axes(
            ax,
            "Apartment size and nightly listing price",
            "Median nightly listing price (AUD)"
        )
        ax.legend(frameon=False)
        ax.margins(y=0.18)

        fig.tight_layout()
        done(fig, "07_size_price")

    capacity = scenarios.loc[
        scenarios["area"].eq("Melbourne")
        & scenarios["property_group"].eq("Apartment")
        & scenarios["bedrooms"].isin([1, 2, 3])
    ].sort_values("bedrooms")

    if not capacity.empty:
        values = capacity["median"] / (capacity["bedrooms"] * 2)

        labels = [
            f"{int(bed)} bedrooms / {int(bed * 2)} guests"
            for bed in capacity["bedrooms"]
        ]

        done(
            horizontal(
                labels,
                values,
                "Illustrative price per guest at design capacity",
                "Median listing price divided by assumed guests (AUD/night)",
                colors=[
                    TEAL if bed == 2 else GRAY
                    for bed in capacity["bedrooms"]
                ]
            ),
            "08_per_person"
        )


# ==================== Review themes and amenities ====================

def experience_charts(amenities, themes):
    areas = [
        area for area in ["Melbourne", "Yarra Ranges"]
        if area in themes.index
    ]

    if areas:
        categories = ["Walking/Transport", "Quiet/Nature"]
        fig, ax = plt.subplots(figsize=(9.2, 4.6))
        positions = np.arange(len(categories))
        width = 0.32

        for index, area in enumerate(areas):
            bars = ax.bar(
                positions + (index - (len(areas) - 1) / 2) * width,
                themes.loc[area, categories],
                width,
                label=area,
                color=[TEAL, GOLD][index]
            )
            ax.bar_label(bars, fmt="%.1f%%", padding=5)

        ax.set_xticks(positions, categories)
        finish_axes(
            ax,
            "Review themes differ between urban and retreat areas",
            "Share of nonempty reviews mentioning a theme (%)"
        )
        ax.legend(frameon=False)
        ax.margins(y=0.2)

        fig.tight_layout()
        done(fig, "09_review_themes")

    family = themes["Family/Children"].reindex(AREAS).dropna()

    if not family.empty:
        done(
            horizontal(
                family.index,
                family.values,
                "Family and children mentions in reviews",
                "Share mentioning related English keywords (%)",
                colors=[
                    GOLD if area == "Yarra Ranges" else GRAY
                    for area in family.index
                ],
                fmt=lambda value: f"{value:.1f}%"
            ),
            "10_family_mentions"
        )

    pools = (
        amenities["Pool"]
        .reindex(["Melbourne", "Yarra", "Port Phillip", "Yarra Ranges"])
        .dropna() * 100
    )

    if not pools.empty:
        done(
            horizontal(
                pools.index,
                pools.values,
                "Pool availability among entire-home listings",
                "Listings reporting a pool (%)",
                colors=[
                    TEAL if area == "Melbourne" else GRAY
                    for area in pools.index
                ],
                fmt=lambda value: f"{value:.0f}%"
            ),
            "11_pool"
        )

    areas = [
        area for area in ["Melbourne", "Yarra Ranges"]
        if area in amenities.index
    ]

    if areas:
        categories = ["Fireplace", "Free parking", "Garden"]
        fig, ax = plt.subplots(figsize=(9.2, 4.6))
        positions = np.arange(len(categories))
        width = 0.32

        for index, area in enumerate(areas):
            bars = ax.bar(
                positions + (index - (len(areas) - 1) / 2) * width,
                amenities.loc[area, categories] * 100,
                width,
                label=area,
                color=[TEAL, GOLD][index]
            )
            ax.bar_label(bars, fmt="%.0f%%", padding=5)

        ax.set_xticks(positions, categories)
        ax.set_ylim(0, 110)

        finish_axes(
            ax,
            "Amenities supporting a retreat product",
            "Share of local entire-home listings (%)"
        )
        ax.legend(frameon=False)

        fig.tight_layout()
        done(fig, "12_retreat_amenities")


# ==================== Calendar and monthly activity ====================

def operations_charts(calendar_summary, sample, monthly_reviews):
    two_nights = (
        calendar_summary["accept_2_share"]
        .reindex(AREAS)
        .dropna() * 100
    )

    if not two_nights.empty:
        done(
            horizontal(
                two_nights.index,
                two_nights.values,
                "Two-night stays: calendar rule compatibility",
                "Available dates whose individual rules allow two nights (%)",
                colors=[
                    GOLD if area == "Yarra Ranges" else GRAY
                    for area in two_nights.index
                ],
                fmt=lambda value: f"{value:.0f}%"
            ),
            "13_two_nights"
        )

    cohort = sample.loc[
        sample["mature"].fillna(False)
        & sample["area"].isin(["Melbourne", "Yarra", "Yarra Ranges"]),
        ["id", "area"]
    ].copy()

    if cohort.empty:
        return

    # Align saved listing identifiers before joining.
    # Earlier CSV exports may represent numeric IDs with a trailing ".0".
    cohort["id"] = (
        cohort["id"].astype("string")
        .str.replace(r"\.0$", "", regex=True)
    )

    activity = monthly_reviews.rename(
        columns={"listing_id": "id"}
    ).copy()

    activity["id"] = (
        activity["id"].astype("string")
        .str.replace(r"\.0$", "", regex=True)
    )

    activity = activity.merge(
        cohort,
        on="id",
        how="inner",
        validate="many_to_one"
    )

    if activity.empty:
        raise ValueError(
            "Monthly reviews do not match the saved modeling sample IDs."
        )

    months = pd.period_range(
        "2025-07", "2026-05", freq="M"
    ).astype(str)

    table = (
        activity.groupby(["month", "area"])["reviews"]
        .sum()
        .unstack()
        .reindex(months)
        .fillna(0)
    )

    table = table.div(cohort.groupby("area").size(), axis=1) * 100

    export_table(
        table.round(2).rename_axis("month").reset_index(),
        "06_monthly_reviews_per100"
    )

    fig, ax = plt.subplots(figsize=(10, 4.6))

    for area, color in [
        ("Melbourne", TEAL),
        ("Yarra", BLUE),
        ("Yarra Ranges", GOLD)
    ]:
        if area in table.columns:
            ax.plot(
                np.arange(len(table)),
                table[area],
                label=area,
                color=color,
                marker="o",
                markersize=4,
                linewidth=2
            )

    ax.set_xticks(
        np.arange(len(table)),
        [f"{month[2:4]}/{month[5:]}" for month in table.index]
    )

    finish_axes(
        ax,
        "Monthly review activity within a fixed cohort",
        "New reviews per 100 listings"
    )
    ax.legend(frameon=False)

    fig.tight_layout()
    done(fig, "14_monthly_reviews")


# ==================== Model performance ====================

def model_charts(test_results, importance):
    order = [
        "Global Median",
        "Area and Bedroom Median",
        "Selected Model"
    ]

    results = test_results.reindex(order)

    if results[["within25", "MedAE"]].isna().any().any():
        raise ValueError("The saved test results are incomplete.")

    labels = [
        "Global median price",
        "Area and bedroom median",
        "Selected feature-based model"
    ]

    done(
        horizontal(
            labels,
            results["within25"] * 100,
            "Predictions within 25% of observed listing prices",
            "Listings per 100 test listings",
            colors=[GRAY, BLUE, TEAL],
            fmt=lambda value: f"{value:.1f}"
        ),
        "15_model_match"
    )

    done(
        horizontal(
            labels,
            results["MedAE"],
            "Typical prediction error by pricing method",
            "Median absolute error (AUD/night; lower is better)",
            colors=[GRAY, BLUE, TEAL],
            fmt=lambda value: f"A${value:.0f}"
        ),
        "16_model_error"
    )

    # Plot positive importance values to show measurable model reliance.
    drivers = (
        importance.loc[importance["value"].gt(0)]
        .sort_values("value", ascending=False)
        .head(6)
    )

    if not drivers.empty:
        done(
            horizontal(
                [
                    FEATURE_LABELS.get(feature, feature)
                    for feature in drivers["feature"]
                ],
                drivers["value"],
                "Features used most by the pricing model",
                "Increase in validation MAE after shuffling (AUD)",
                fmt=lambda value: f"{value:.1f}"
            ),
            "17_model_drivers"
        )


# ==================== Recommended product plans ====================

def decisions_charts(selected):
    if selected.empty:
        return

    selected = selected.copy()
    positions = np.arange(len(selected))
    width = 0.31

    fig, ax = plt.subplots(figsize=(10, 4.8))

    for index, (column, label, color) in enumerate([
        ("matched_median", "Comparable median price", GRAY),
        ("launch", "Reference launch price", TEAL)
    ]):
        bars = ax.bar(
            positions + (index - 0.5) * width,
            selected[column],
            width,
            label=label,
            color=color
        )
        ax.bar_label(bars, fmt="%.0f", padding=5)

    ax.set_xticks(
        positions,
        [
            f"{row['area']}\n{int(row['bedrooms'])}-bedroom\n"
            f"{row['property_group']}"
            for _, row in selected.iterrows()
        ]
    )

    finish_axes(
        ax,
        "Reference launch prices and comparable listings",
        "Nightly listing price (AUD)"
    )
    ax.legend(frameon=False)
    ax.margins(y=0.2)

    fig.tight_layout()
    done(fig, "18_recommended_prices")

    rows = []

    for _, row in selected.iterrows():
        rows.append({
            "plan": f"{row['area']} / {int(row['bedrooms'])} bedrooms",
            "launch_price_AUD": row["launch"],
            "10_nights_illustrative_amount_AUD": row["launch"] * 10,
            "15_nights_illustrative_amount_AUD": row["launch"] * 15,
            "20_nights_illustrative_amount_AUD": row["launch"] * 20
        })

    export_table(
        pd.DataFrame(rows),
        "10_revenue_scenarios_not_forecast"
    )


# ==================== Geographic charts ====================

def geography_charts(listings, sample, selected, geo):
    fig, ax = plt.subplots(figsize=(10, 5.9))
    base_map(ax, geo)

    for group, color in COLORS.items():
        points = listings.loc[listings["property_group"].eq(group)]

        ax.scatter(
            points["longitude"],
            points["latitude"],
            s=3,
            alpha=0.5,
            color=color,
            linewidths=0,
            zorder=2
        )

    ax.legend(
        handles=[
            Patch(color=color, label=group)
            for group, color in COLORS.items()
        ],
        loc="upper left",
        fontsize=9
    )
    ax.set_title(
        "Entire-home listings by property type",
        loc="left",
        fontweight="bold",
        pad=12
    )

    map_source(fig)
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    done(fig, "01_market_map")

    comparable = sample.loc[
        sample["property_group"].eq("Apartment")
        & sample["bedrooms"].eq(2)
        & sample["accommodates"].between(4, 5)
    ]

    stats = (
        comparable.groupby("area")["price_aud"]
        .agg(["size", "median"])
    )
    stats = stats.loc[stats["size"].ge(30)]

    export_table(
        stats.round(2).reset_index(),
        "07_twobed_map_comparables"
    )

    if not stats.empty:
        minimum = float(stats["median"].min())
        maximum = float(stats["median"].max())

        if minimum == maximum:
            minimum -= 1
            maximum += 1

        norm = Normalize(vmin=minimum, vmax=maximum)
        cmap = mpl.colormaps["YlGnBu"]

        fig, ax = plt.subplots(figsize=(9.7, 6))
        base_map(
            ax,
            geo,
            values=stats["median"].to_dict(),
            cmap=cmap,
            norm=norm,
            extent=[144.77, 145.21, -37.95, -37.67]
        )

        locations = {
            "Melbourne": (144.947, -37.81),
            "Yarra": (145.001, -37.79),
            "Port Phillip": (144.969, -37.858),
            "Stonnington": (145.041, -37.862),
            "Moreland": (144.96, -37.704),
            "Darebin": (145.021, -37.718),
            "Whitehorse": (145.165, -37.824),
            "Maribyrnong": (144.883, -37.776),
            "Moonee Valley": (144.909, -37.721),
            "Glen Eira": (145.045, -37.908),
            "Boroondara": (145.078, -37.802)
        }

        for area, (longitude, latitude) in locations.items():
            if area in stats.index:
                ax.text(
                    longitude,
                    latitude,
                    f"{area}\nA${stats.loc[area, 'median']:.0f}",
                    ha="center",
                    va="center",
                    fontsize=8.5,
                    bbox={
                        "facecolor": "white",
                        "edgecolor": "none",
                        "alpha": 0.86,
                        "pad": 2
                    },
                    zorder=3
                )

        colorbar = fig.colorbar(
            mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
            ax=ax,
            fraction=0.036,
            pad=0.02,
            shrink=0.76
        )
        colorbar.set_label("Median listing price (AUD/night)")

        ax.set_title(
            "Comparable two-bedroom apartment prices by area",
            loc="left",
            fontweight="bold",
            pad=14
        )
        map_source(
            fig,
            "Inside Airbnb boundaries; 4–5 guests; at least 30 listings "
            "per area. Grey: insufficient comparable listings."
        )

        fig.tight_layout(rect=[0, 0.05, 1, 1])
        done(fig, "04_comparable_price_map")

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5))

    highlights = {
        "Melbourne": BLUE,
        "Yarra": TEAL,
        "Yarra Ranges": GOLD
    }

    base_map(
        axes[0], geo,
        highlights=highlights,
        extent=[144.83, 145.08, -37.94, -37.70]
    )
    base_map(
        axes[1], geo,
        highlights=highlights,
        extent=[144.85, 146.23, -38.1, -37.4]
    )

    annotation_positions = {
        "Yarra": (0, (145.005, -37.81), (144.94, -37.73)),
        "Melbourne": (0, (144.94, -37.82), (144.84, -37.90)),
        "Yarra Ranges": (1, (145.58, -37.78), (145.26, -38.04))
    }

    # Use saved prices rather than hard-coded recommendations.
    for _, row in selected.iterrows():
        area = row["area"]

        if area not in annotation_positions:
            continue

        panel, point, text_position = annotation_positions[area]
        color = highlights[area]

        axes[panel].annotate(
            f"{area}\n{int(row['bedrooms'])}-bedroom\n"
            f"A${row['launch']:.0f}/night",
            xy=point,
            xytext=text_position,
            fontsize=10,
            arrowprops={"arrowstyle": "-", "color": color},
            bbox={
                "facecolor": "white",
                "edgecolor": color,
                "boxstyle": "round,pad=.4"
            },
            zorder=3
        )

    axes[0].set_title("Urban product plans", loc="left", fontweight="bold")
    axes[1].set_title("Retreat product plan", loc="left", fontweight="bold")

    map_source(
        fig,
        "Inside Airbnb boundaries. Reference launch prices use the "
        "June 2026 snapshot."
    )

    fig.tight_layout(rect=[0, 0.06, 1, 1])
    done(fig, "19_decision_map")


# ==================== Run chart generation ====================

def main():
    data = load_chart_data()

    counts, mix, amenities, themes = profile_tables(
        data["entire_listings"]
    )

    market_charts(counts, mix)
    urban_charts(data["scenarios"])
    experience_charts(amenities, themes)

    operations_charts(
        data["calendar_summary"],
        data["modeling_sample"],
        data["monthly_reviews"]
    )

    model_charts(data["test"], data["importance"])
    decisions_charts(data["selected_plans"])

    if (ASSET / "neighbourhoods.geojson").is_file():
        geography_charts(
            data["entire_listings"],
            data["modeling_sample"],
            data["selected_plans"],
            load_map_boundaries()
        )
    else:
        print(
            "Maps skipped: assets/neighbourhoods.geojson was not found."
        )

    print(f"Business charts saved to: {F}")


if __name__ == "__main__":
    main()

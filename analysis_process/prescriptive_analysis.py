# ==================== Import packages ====================

from pathlib import Path
import sys

import numpy as np
import pandas as pd


# ==================== Locate the project directory ====================

SCRIPT_DIR = Path(__file__).resolve().parent

PROJECT_DIR = SCRIPT_DIR.parent
MODULE_DIR = PROJECT_DIR / "data"

for filename in [
    "Graph_preparation.py",
    "Data_Visualization.py",
]:
    module_path = MODULE_DIR / filename

    if not module_path.is_file():
        raise FileNotFoundError(
            f"Required Python file not found: {module_path}"
        )

if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


# ==================== Import preparation and visualization modules ====================

import Graph_preparation as prep
import Data_Visualization as viz


# ==================== Set output directories ====================

OUT = PROJECT_DIR / "analysis_outputs"

F = OUT / "figures"
T = OUT / "tables"
MODELS = OUT / "models"

for folder in [OUT, F, T, MODELS]:
    folder.mkdir(parents=True, exist_ok=True)

if Path(prep.OUT).resolve() != OUT.resolve():
    raise ValueError(
        "Graph_preparation.py uses a different output directory. "
        f"Expected: {OUT}"
    )

export_table = prep.export_table
show_table = prep.show_table


# ==================== Load predictive candidate results ====================

candidate_path = T / "predictive_candidate_quotes.csv"

if not candidate_path.is_file():
    raise FileNotFoundError(
        f"Required predictive output not found: {candidate_path}. "
        "Run predictive_analysis.py first."
    )

sc = pd.read_csv(
    candidate_path,
    low_memory=False,
)

required_columns = [
    "area",
    "property_group",
    "bedrooms",
    "n",
    "hosts",
    "mature_n",
    "median",
    "capacity",
    "reviews",
    "model",
    "matched_n",
    "matched_hosts",
    "matched_median",
    "matched_p25",
    "matched_p75",
]

prep.check_columns(
    sc,
    required_columns,
    "Predictive candidate results",
)

for column in required_columns:
    if column not in ["area", "property_group"]:
        sc[column] = pd.to_numeric(
            sc[column],
            errors="coerce",
        )

segment_keys = [
    "area",
    "property_group",
    "bedrooms",
]

if sc.duplicated(segment_keys).any():
    raise ValueError(
        "Candidate results contain duplicate market segments."
    )

if sc.empty:
    raise ValueError(
        "No candidate segments are available."
    )


# ==================== Define candidate-selection rules ====================

MIN_PEERS = 50
MIN_HISTORY = 30
MIN_HOSTS = 30
MIN_TWO_NIGHT_PEERS = 20

NUMBER_OF_CANDIDATES = 3
PRICE_INCREMENT = 10

# Candidates are ranked by historical annual review activity.
# Listing and host counts provide secondary ranking criteria.
# This procedure does not maximize revenue or profit.


# ==================== Define candidate-ranking function ====================

def rank_candidates(
    candidates,
    min_peers=50,
    min_history=30,
    min_hosts=30,
    min_two=20,
):
    """Filter and rank eligible market segments."""

    eligible = candidates.loc[
        candidates["n"].ge(min_peers)
        & candidates["mature_n"].ge(min_history)
        & candidates["hosts"].ge(min_hosts)
        & candidates["matched_n"].ge(min_two)
        & np.isfinite(candidates["model"])
        & candidates["model"].gt(0)
        & np.isfinite(candidates["reviews"])
        & candidates["matched_p25"].notna()
        & candidates["matched_p75"].notna()
        & candidates["matched_p25"].le(
            candidates["matched_p75"]
        )
    ].copy()

    return eligible.sort_values(
        [
            "reviews",
            "n",
            "hosts",
            "area",
            "property_group",
            "bedrooms",
        ],
        ascending=[
            False,
            False,
            False,
            True,
            True,
            True,
        ],
    ).reset_index(drop=True)


# ==================== Record candidate eligibility ====================

eligibility = sc.copy()

eligibility["Pass_peer_count"] = (
    eligibility["n"].ge(MIN_PEERS)
)

eligibility["Pass_history_count"] = (
    eligibility["mature_n"].ge(MIN_HISTORY)
)

eligibility["Pass_host_count"] = (
    eligibility["hosts"].ge(MIN_HOSTS)
)

eligibility["Pass_two_night_count"] = (
    eligibility["matched_n"].ge(
        MIN_TWO_NIGHT_PEERS
    )
)

eligibility["Pass_model_reference"] = (
    np.isfinite(eligibility["model"])
    & eligibility["model"].gt(0)
)

eligibility["Pass_historical_activity"] = (
    np.isfinite(eligibility["reviews"])
)

eligibility["Pass_price_interval"] = (
    eligibility["matched_p25"].notna()
    & eligibility["matched_p75"].notna()
    & eligibility["matched_p25"].le(
        eligibility["matched_p75"]
    )
)

pass_columns = [
    column
    for column in eligibility.columns
    if column.startswith("Pass_")
]

eligibility["Eligible"] = (
    eligibility[pass_columns].all(axis=1)
)

export_table(
    eligibility,
    "prescriptive_candidate_eligibility",
)


# ==================== Rank eligible product candidates ====================

ranked = rank_candidates(
    sc,
    min_peers=MIN_PEERS,
    min_history=MIN_HISTORY,
    min_hosts=MIN_HOSTS,
    min_two=MIN_TWO_NIGHT_PEERS,
)

ranked.insert(
    0,
    "Rank",
    np.arange(1, len(ranked) + 1),
)

export_table(
    ranked,
    "candidate_ranking",
)

show_table(
    ranked[
        [
            "Rank",
            "area",
            "property_group",
            "bedrooms",
            "n",
            "hosts",
            "mature_n",
            "reviews",
            "matched_n",
            "model",
        ]
    ].round(2)
)

if len(ranked) < NUMBER_OF_CANDIDATES:
    raise ValueError(
        f"Only {len(ranked)} segments satisfy the selection rules. "
        f"At least {NUMBER_OF_CANDIDATES} are required. "
        "Review the eligibility table before changing the rules."
    )


# ==================== Select the top three product candidates ====================

selected = (
    ranked.head(NUMBER_OF_CANDIDATES)
    .copy()
    .reset_index(drop=True)
)

selected["plan"] = [
    f"Candidate {index + 1}"
    for index in range(len(selected))
]


# ==================== Define trial-price selection function ====================

def choose_trial_price(row):
    """
    Select the nearest AUD 10 price to the model reference
    within the matched peer interquartile range.
    """

    lower = (
        np.ceil(
            row["matched_p25"] / PRICE_INCREMENT
        )
        * PRICE_INCREMENT
    )

    upper = (
        np.floor(
            row["matched_p75"] / PRICE_INCREMENT
        )
        * PRICE_INCREMENT
    )

    if lower > upper:
        raise ValueError(
            "No AUD 10 price point exists inside the peer interval for "
            f"{row['area']}, "
            f"{int(row['bedrooms'])}-bedroom "
            f"{row['property_group']}. "
            "Manual price review is required."
        )

    price_grid = np.arange(
        lower,
        upper + PRICE_INCREMENT,
        PRICE_INCREMENT,
    )

    nearest_index = np.argmin(
        np.abs(
            price_grid - row["model"]
        )
    )

    return int(
        price_grid[nearest_index]
    )


# ==================== Calculate historical trial-price benchmarks ====================

selected["launch"] = selected.apply(
    choose_trial_price,
    axis=1,
)

selected["quote_nights_reference"] = 2

selected["Difference_from_model_AUD"] = (
    selected["launch"]
    - selected["model"]
)

# These are historical listed-price benchmarks.
# They do not establish an optimal price or guarantee a booking.


# ==================== Validate selected candidates and prices ====================

assert len(selected) == NUMBER_OF_CANDIDATES

assert selected["n"].ge(MIN_PEERS).all()

assert selected["mature_n"].ge(
    MIN_HISTORY
).all()

assert selected["hosts"].ge(
    MIN_HOSTS
).all()

assert selected["matched_n"].ge(
    MIN_TWO_NIGHT_PEERS
).all()

assert selected["launch"].ge(
    selected["matched_p25"]
).all()

assert selected["launch"].le(
    selected["matched_p75"]
).all()

assert selected["launch"].mod(
    PRICE_INCREMENT
).eq(0).all()


# ==================== Save selected product plans ====================

export_table(
    selected,
    "prescriptive_selected_plans",
)

show_table(
    selected[
        [
            "plan",
            "area",
            "property_group",
            "bedrooms",
            "model",
            "matched_n",
            "matched_p25",
            "matched_median",
            "matched_p75",
            "launch",
        ]
    ].round(2)
)


# ==================== Evaluate selection-rule sensitivity ====================

sensitivity_rules = [
    (
        "Relaxed",
        30,
        20,
        20,
        10,
    ),
    (
        "Main",
        50,
        30,
        30,
        20,
    ),
    (
        "Stricter",
        100,
        50,
        50,
        30,
    ),
    (
        "Large samples",
        150,
        80,
        80,
        30,
    ),
]

sensitivity_rows = []

for (
    label,
    min_peers,
    min_history,
    min_hosts,
    min_two,
) in sensitivity_rules:

    sensitivity_ranked = rank_candidates(
        sc,
        min_peers=min_peers,
        min_history=min_history,
        min_hosts=min_hosts,
        min_two=min_two,
    )

    top = sensitivity_ranked.head(
        NUMBER_OF_CANDIDATES
    )

    candidate_labels = [
        (
            f"{row['area']} | "
            f"{int(row['bedrooms'])}-bedroom "
            f"{row['property_group']}"
        )
        for _, row in top.iterrows()
    ]

    sensitivity_rows.append(
        {
            "Rule": label,
            "Minimum_peers": min_peers,
            "Minimum_history": min_history,
            "Minimum_hosts": min_hosts,
            "Minimum_two_night_peers": min_two,
            "Eligible_segments": len(sensitivity_ranked),
            "Top_candidates": "; ".join(
                candidate_labels
            ),
        }
    )

sensitivity = pd.DataFrame(
    sensitivity_rows
)

export_table(
    sensitivity,
    "prescriptive_sensitivity",
)

show_table(sensitivity)


# ==================== Prepare alternative product watchlist ====================

watchlist = sc.loc[
    (
        sc["area"].eq("Melbourne")
        & sc["bedrooms"].eq(2)
        & sc["property_group"].eq("Apartment")
    )
    |
    (
        sc["area"].eq("Yarra Ranges")
        & sc["bedrooms"].eq(1)
        & sc["property_group"].eq("Cottage/Guesthouse")
    )
].copy()

watch_prices = []
watch_notes = []

for _, row in watchlist.iterrows():

    valid_reference = (
        pd.notna(row["model"])
        and np.isfinite(row["model"])
        and pd.notna(row["matched_p25"])
        and pd.notna(row["matched_p75"])
    )

    if not valid_reference:
        watch_prices.append(np.nan)
        watch_notes.append(
            "Insufficient price-reference data"
        )
        continue

    try:
        watch_prices.append(
            choose_trial_price(row)
        )
        watch_notes.append(
            "Historical price reference only"
        )

    except ValueError:
        watch_prices.append(np.nan)
        watch_notes.append(
            "Manual price review required"
        )

watchlist["Reference_price_AUD"] = watch_prices
watchlist["Review_note"] = watch_notes

export_table(
    watchlist,
    "watchlist_products",
)


# ==================== Build the integrated evidence chain ====================

evidence_rows = []

for _, row in selected.iterrows():

    product = (
        f"{row['area']} | "
        f"{int(row['bedrooms'])}-bedroom "
        f"{row['property_group']}"
    )

    descriptive_evidence = (
        f"{int(row['n'])} comparable listings; "
        f"{int(row['hosts'])} hosts; "
        f"{int(row['mature_n'])} historical listings; "
        f"median annual reviews: {row['reviews']:g}"
    )

    predictive_evidence = (
        f"{int(row['matched_n'])} two-night peers; "
        f"median model reference: "
        f"A${row['model']:.0f} per night"
    )

    decision_evidence = (
        f"Peer P25-P75: "
        f"A${row['matched_p25']:.0f}-"
        f"A${row['matched_p75']:.0f}; "
        f"historical trial-price benchmark: "
        f"A${row['launch']:.0f} per night"
    )

    evidence_rows.append(
        {
            "Candidate": row["plan"],
            "Product": product,
            "Descriptive_evidence": descriptive_evidence,
            "Predictive_evidence": predictive_evidence,
            "Prescriptive_decision": decision_evidence,
            "Client_action": (
                "Identify a suitable property, confirm authorization "
                "and actual operating costs, and review live comparable "
                "quotes before launching."
            ),
        }
    )

evidence_chain = pd.DataFrame(
    evidence_rows
)

export_table(
    evidence_chain,
    "integrated_evidence_chain",
)

show_table(evidence_chain)


# ==================== Prepare client-facing recommendations ====================

recommendation_rows = []

for _, row in selected.iterrows():

    recommendation_rows.append(
        {
            "Candidate": row["plan"],
            "Area": row["area"],
            "Property_type": row["property_group"],
            "Bedrooms": int(row["bedrooms"]),
            "Capacity_reference": row["capacity"],
            "Historical_trial_price_AUD": row["launch"],
            "Peer_price_P25_AUD": row["matched_p25"],
            "Peer_price_P75_AUD": row["matched_p75"],
            "First_action": (
                "Find an existing or prospective managed property "
                "matching this product segment."
            ),
            "Before_launch": (
                "Verify property condition, permissions, total costs, "
                "and comparable prices for the actual stay dates."
            ),
            "After_launch": (
                "Track listing views, inquiries, bookings, achieved prices, "
                "and operating costs; review the offer weekly."
            ),
        }
    )

recommendations = pd.DataFrame(
    recommendation_rows
)

export_table(
    recommendations,
    "client_recommendations",
)

show_table(recommendations.round(2))


# ==================== Prepare alternative price benchmarks ====================

price_options = selected[
    [
        "plan",
        "area",
        "property_group",
        "bedrooms",
        "matched_p25",
        "launch",
        "matched_p75",
    ]
].rename(
    columns={
        "plan": "Candidate",
        "area": "Area",
        "property_group": "Property_type",
        "bedrooms": "Bedrooms",
        "matched_p25": "Peer_lower_quartile_AUD",
        "launch": "Historical_trial_price_AUD",
        "matched_p75": "Peer_upper_quartile_AUD",
    }
)

export_table(
    price_options,
    "prescriptive_price_options",
)

# Price options come from observed comparable quotes.
# No occupancy, sold-night, or revenue-growth assumptions are added.


# ==================== Prepare operational improvement actions ====================

operational_actions = pd.DataFrame(
    [
        {
            "Priority": 1,
            "Action": "Review cleaning standards",
            "Implementation": (
                "Use a turnover checklist and inspect recurring issues."
            ),
            "Evidence_limit": (
                "Service ratings identify areas for review; "
                "they do not prove the financial effect of an intervention."
            ),
        },
        {
            "Priority": 2,
            "Action": "Verify listing accuracy",
            "Implementation": (
                "Check photographs, room descriptions, capacity, "
                "amenities, and disclosed limitations."
            ),
            "Evidence_limit": (
                "Accurate descriptions are an operating action, "
                "not a quantified revenue forecast."
            ),
        },
        {
            "Priority": 3,
            "Action": "Improve check-in instructions",
            "Implementation": (
                "Provide clear arrival, access, and support instructions."
            ),
            "Evidence_limit": (
                "The dataset does not estimate the causal return "
                "from changing the check-in process."
            ),
        },
        {
            "Priority": 4,
            "Action": "Inspect existing air conditioning",
            "Implementation": (
                "Check functionality and ensure the listing describes "
                "the available equipment correctly."
            ),
            "Evidence_limit": (
                "Amenity prevalence does not establish installation ROI."
            ),
        },
        {
            "Priority": 5,
            "Action": "Review discretionary equipment purchases",
            "Implementation": (
                "Obtain actual quotations and assess property-specific needs "
                "before purchasing equipment."
            ),
            "Evidence_limit": (
                "Air purifiers are not treated as a required purchase "
                "based on listing prevalence alone."
            ),
        },
    ]
)

export_table(
    operational_actions,
    "prescriptive_operational_actions",
)


# ==================== Save decision-rule documentation ====================

decision_rules = pd.DataFrame(
    [
        {
            "Rule": "Minimum comparable listings",
            "Value": str(MIN_PEERS),
        },
        {
            "Rule": "Minimum historical listings",
            "Value": str(MIN_HISTORY),
        },
        {
            "Rule": "Minimum independent hosts",
            "Value": str(MIN_HOSTS),
        },
        {
            "Rule": "Minimum matched two-night listings",
            "Value": str(MIN_TWO_NIGHT_PEERS),
        },
        {
            "Rule": "Primary ranking criterion",
            "Value": (
                "Median annual reviews among historical listings, descending"
            ),
        },
        {
            "Rule": "Secondary ranking criteria",
            "Value": (
                "Comparable listing count and host count, descending"
            ),
        },
        {
            "Rule": "Deterministic tie-breakers",
            "Value": (
                "Area, property group, and bedroom count, ascending"
            ),
        },
        {
            "Rule": "Trial-price rule",
            "Value": (
                "Nearest AUD 10 price to the model reference "
                "inside the matched peer P25-P75 interval"
            ),
        },
        {
            "Rule": "Decision scope",
            "Value": (
                "Product candidates and historical listing-price benchmarks; "
                "not a property purchase or profit recommendation"
            ),
        },
    ]
)

export_table(
    decision_rules,
    "prescriptive_decision_rules",
)


# ==================== Generate recommendation charts ====================

chart_functions = [
    (
        "18_recommended_prices",
        viz.plot_recommended_prices,
    ),
    (
        "19_decision_map",
        viz.plot_decision_map,
    ),
]

chart_results = []

for name, function in chart_functions:

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

export_table(
    pd.DataFrame(chart_results),
    "prescriptive_chart_generation_report",
)


# ==================== Print completion summary ====================

print()
print("Prescriptive analysis completed.")
print()

print(f"Eligible segments: {len(ranked):,}")
print(f"Selected candidates: {len(selected)}")
print()

for _, row in selected.iterrows():

    print(
        f"{row['plan']}: "
        f"{row['area']} | "
        f"{int(row['bedrooms'])}-bedroom "
        f"{row['property_group']} | "
        f"A${row['launch']:.0f} per night"
    )

print()
print(f"Figure directory: {F}")
print(f"Table directory: {T}")

print()
print(
    "Candidate rankings use historical review activity and sample rules. "
    "They do not establish the highest-profit product or an optimal price."
)
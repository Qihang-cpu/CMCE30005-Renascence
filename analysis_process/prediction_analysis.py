# ==================== Import packages ====================

from pathlib import Path
import sys
import json
import importlib.metadata

import joblib
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.compose import (
    ColumnTransformer,
    TransformedTargetRegressor,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import (
    RandomForestRegressor,
    HistGradientBoostingRegressor,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    mean_absolute_error,
    median_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.inspection import permutation_importance


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

BASE_DIR = PROJECT_DIR

OUT = BASE_DIR / "analysis_outputs"
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


# ==================== Load prepared analysis samples ====================

q = prep.q.copy()
sc = prep.sc.copy()

AMENITY_COLUMNS = prep.AMENITY_COLUMNS.copy()

if q.empty:
    raise ValueError(
        "The price-model sample is empty."
    )


# ==================== Define numeric and categorical predictors ====================

NUMERIC_FEATURES = [
    "bedrooms",
    "accommodates",
    "bath_num",
    "minimum_nights",
    "quote_nights",
    "quote_lead",
    "quote_weekend",
] + AMENITY_COLUMNS

CATEGORICAL_FEATURES = [
    "area",
    "property_group",
    "quote_month",
]

FEATURES = (
    NUMERIC_FEATURES
    + CATEGORICAL_FEATURES
)

TARGET = "price_aud"
GROUP = "host_id"

prep.check_columns(
    q,
    [
        "id",
        GROUP,
        TARGET,
    ] + FEATURES,
    "Price-model sample",
)


# ==================== Validate listing IDs and host groups ====================

if q["id"].isna().any() or not q["id"].is_unique:
    raise ValueError(
        "The model sample must contain one non-missing ID per listing."
    )

host_ids = (
    q[GROUP]
    .astype("string")
    .str.strip()
)

invalid_hosts = (
    host_ids.isna()
    | host_ids.eq("").fillna(False)
)

if invalid_hosts.any():
    raise ValueError(
        f"{int(invalid_hosts.sum())} listings have missing host IDs. "
        "Resolve these records before splitting by host."
    )

q[GROUP] = host_ids

q = q.reset_index(drop=True)


# ==================== Standardize predictor data types ====================

for column in NUMERIC_FEATURES:
    q[column] = pd.to_numeric(
        q[column],
        errors="coerce",
    ).replace(
        [np.inf, -np.inf],
        np.nan,
    )

for column in CATEGORICAL_FEATURES:
    values = (
        q[column]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

    q[column] = (
        values.astype(object)
        .where(values.notna(), np.nan)
    )

q[TARGET] = pd.to_numeric(
    q[TARGET],
    errors="coerce",
)

valid_target = (
    q[TARGET].notna()
    & np.isfinite(q[TARGET])
    & q[TARGET].gt(0)
)

if not valid_target.all():
    raise ValueError(
        "The model target must contain only finite positive prices."
    )


# ==================== Define model inputs ====================

X = q[FEATURES].copy()
y = q[TARGET].copy()
groups = q[GROUP].copy()

print(f"Model listings: {len(q):,}")
print(f"Unique hosts: {groups.nunique():,}")
print(f"Numeric predictors: {len(NUMERIC_FEATURES)}")
print(f"Categorical predictors: {len(CATEGORICAL_FEATURES)}")
print()


# ==================== Split development and final test samples by host ====================

development_index, test_index = next(
    GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42,
    ).split(
        X,
        y,
        groups,
    )
)


# ==================== Split training and validation samples by host ====================

train_relative, validation_relative = next(
    GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=43,
    ).split(
        X.iloc[development_index],
        y.iloc[development_index],
        groups.iloc[development_index],
    )
)

train_index = development_index[train_relative]
validation_index = development_index[validation_relative]


# ==================== Verify separation between host groups ====================

train_hosts = set(groups.iloc[train_index])
validation_hosts = set(groups.iloc[validation_index])
test_hosts = set(groups.iloc[test_index])

if not train_hosts.isdisjoint(validation_hosts):
    raise ValueError(
        "Training and validation samples share host IDs."
    )

if not train_hosts.isdisjoint(test_hosts):
    raise ValueError(
        "Training and test samples share host IDs."
    )

if not validation_hosts.isdisjoint(test_hosts):
    raise ValueError(
        "Validation and test samples share host IDs."
    )

split_summary = pd.DataFrame(
    [
        {
            "Split": "Training",
            "Listings": len(train_index),
            "Hosts": len(train_hosts),
        },
        {
            "Split": "Validation",
            "Listings": len(validation_index),
            "Hosts": len(validation_hosts),
        },
        {
            "Split": "Final test",
            "Listings": len(test_index),
            "Hosts": len(test_hosts),
        },
    ]
)

export_table(
    split_summary,
    "predictive_split_summary",
)

show_table(split_summary)

# Group proportions are determined by host counts.
# Listing proportions may differ from exactly 60%, 20%, and 20%.


# ==================== Save listing-level split assignments ====================

split_assignments = q[
    ["id", GROUP]
].copy()

split_assignments["Split"] = ""

split_assignments.loc[
    train_index,
    "Split",
] = "Training"

split_assignments.loc[
    validation_index,
    "Split",
] = "Validation"

split_assignments.loc[
    test_index,
    "Split",
] = "Final test"

export_table(
    split_assignments,
    "predictive_split_assignments",
)


# ==================== Define numeric preprocessing ====================

numeric_pipeline = Pipeline(
    steps=[
        (
            "impute",
            SimpleImputer(
                strategy="median",
                add_indicator=True,
                keep_empty_features=True,
            ),
        ),
        (
            "scale",
            StandardScaler(),
        ),
    ]
)


# ==================== Define categorical preprocessing ====================

categorical_pipeline = Pipeline(
    steps=[
        (
            "impute",
            SimpleImputer(
                strategy="constant",
                fill_value="Unknown",
                keep_empty_features=True,
            ),
        ),
        (
            "encode",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
            ),
        ),
    ]
)


# ==================== Combine preprocessing pipelines ====================

preprocessor = ColumnTransformer(
    transformers=[
        (
            "numeric",
            numeric_pipeline,
            NUMERIC_FEATURES,
        ),
        (
            "categorical",
            categorical_pipeline,
            CATEGORICAL_FEATURES,
        ),
    ],
    remainder="drop",
)


# ==================== Define model-pipeline constructor ====================

def build_pipeline(estimator, log_target=True):
    """Build a preprocessing and regression pipeline."""

    regression_pipeline = Pipeline(
        steps=[
            (
                "prepare",
                clone(preprocessor),
            ),
            (
                "model",
                estimator,
            ),
        ]
    )

    if log_target:
        return TransformedTargetRegressor(
            regressor=regression_pipeline,
            func=np.log,
            inverse_func=np.exp,
        )

    return regression_pipeline


# ==================== Define candidate regression models ====================

models = {
    "Log Ridge": build_pipeline(
        Ridge(
            alpha=15,
        ),
        log_target=True,
    ),
    "Random Forest": build_pipeline(
        RandomForestRegressor(
            n_estimators=180,
            min_samples_leaf=8,
            max_depth=18,
            max_features=0.8,
            n_jobs=2,
            random_state=42,
        ),
        log_target=True,
    ),
    "Gradient Boosting": build_pipeline(
        HistGradientBoostingRegressor(
            loss="absolute_error",
            max_iter=200,
            max_leaf_nodes=15,
            min_samples_leaf=40,
            l2_regularization=3,
            random_state=42,
        ),
        log_target=False,
    ),
}

# Log Ridge and Random Forest use log-transformed listed prices.
# Gradient Boosting uses listed prices in AUD with absolute-error loss.
# All reported evaluation metrics are calculated in the original AUD scale.


# ==================== Define evaluation metrics ====================

def evaluate_predictions(actual, predicted):
    """Evaluate predictions against recorded nightly listed prices."""

    actual = np.asarray(
        actual,
        dtype=float,
    )

    predicted = np.asarray(
        predicted,
        dtype=float,
    )

    if not np.isfinite(predicted).all():
        raise ValueError(
            "Predictions contain non-finite values."
        )

    absolute_error = np.abs(
        actual - predicted
    )

    return {
        "MAE": float(
            mean_absolute_error(
                actual,
                predicted,
            )
        ),
        "MedAE": float(
            median_absolute_error(
                actual,
                predicted,
            )
        ),
        "within25": float(
            np.mean(
                absolute_error / actual <= 0.25
            )
        ),
        "RMSE": float(
            np.sqrt(
                mean_squared_error(
                    actual,
                    predicted,
                )
            )
        ),
        "R2": float(
            r2_score(
                actual,
                predicted,
            )
        ),
    }


# ==================== Train candidate models and evaluate validation performance ====================

validation_results = {}
fitted_models = {}

for name, model in models.items():

    print(f"Training {name}...")

    model.fit(
        X.iloc[train_index],
        y.iloc[train_index],
    )

    validation_predictions = model.predict(
        X.iloc[validation_index]
    )

    validation_results[name] = evaluate_predictions(
        y.iloc[validation_index],
        validation_predictions,
    )

    fitted_models[name] = model

validation_table = (
    pd.DataFrame.from_dict(
        validation_results,
        orient="index",
    )
    .rename_axis("Model")
    .reset_index()
)

export_table(
    validation_table,
    "validation",
)

show_table(
    validation_table.round(3)
)


# ==================== Select the model using validation MAE ====================

winner = min(
    validation_results,
    key=lambda name: validation_results[name]["MAE"],
)

print(f"Selected model: {winner}")

print(
    "Validation MAE: "
    f"A${validation_results[winner]['MAE']:.2f} per night"
)

print()


# ==================== Refit the selected model on development data ====================

selected_model = clone(
    models[winner]
)

selected_model.fit(
    X.iloc[development_index],
    y.iloc[development_index],
)

test_predictions = selected_model.predict(
    X.iloc[test_index]
)


# ==================== Construct the global-median baseline ====================

development_median = float(
    y.iloc[development_index].median()
)

global_predictions = np.repeat(
    development_median,
    len(test_index),
)


# ==================== Construct the area-bedroom median baseline ====================

peer_medians = (
    q.iloc[development_index]
    .groupby(["area", "bedrooms"])[TARGET]
    .median()
)

peer_predictions = np.array(
    [
        peer_medians.get(
            (area, bedrooms),
            development_median,
        )
        for area, bedrooms in zip(
            X.iloc[test_index]["area"],
            X.iloc[test_index]["bedrooms"],
        )
    ],
    dtype=float,
)

# Baselines use development data only.
# Unseen area-bedroom groups use the development-wide median.


# ==================== Evaluate final test performance ====================

test_results = {
    "Global median": evaluate_predictions(
        y.iloc[test_index],
        global_predictions,
    ),
    "Area-bedroom median": evaluate_predictions(
        y.iloc[test_index],
        peer_predictions,
    ),
    "Selected model": evaluate_predictions(
        y.iloc[test_index],
        test_predictions,
    ),
}

# Preserve this order for the existing visualization functions.
TEST_METHOD_ORDER = [
    "Global median",
    "Area-bedroom median",
    "Selected model",
]

test_table = (
    pd.DataFrame.from_dict(
        test_results,
        orient="index",
    )
    .reindex(TEST_METHOD_ORDER)
    .rename_axis("Method")
    .reset_index()
)

export_table(
    test_table,
    "test",
)

show_table(
    test_table.round(3)
)


# ==================== Save listing-level test predictions ====================

test_prediction_table = (
    q.iloc[test_index][
        [
            "id",
            GROUP,
            "area",
            "property_group",
            "bedrooms",
            TARGET,
        ]
    ]
    .copy()
    .reset_index(drop=True)
)

test_prediction_table["Global_median_prediction"] = (
    global_predictions
)

test_prediction_table["Area_bedroom_prediction"] = (
    peer_predictions
)

test_prediction_table["Model_prediction"] = (
    test_predictions
)

test_prediction_table["Absolute_error_AUD"] = (
    test_prediction_table[TARGET]
    .sub(test_prediction_table["Model_prediction"])
    .abs()
)

test_prediction_table["Absolute_percentage_error"] = (
    test_prediction_table["Absolute_error_AUD"]
    / test_prediction_table[TARGET]
)

export_table(
    test_prediction_table,
    "predictive_test_predictions",
)


# ==================== Calculate improvement over the peer baseline ====================

peer_mae = test_results[
    "Area-bedroom median"
]["MAE"]

model_mae = test_results[
    "Selected model"
]["MAE"]

mae_improvement = (
    (peer_mae - model_mae) / peer_mae
    if peer_mae > 0
    else None
)

improvement_table = pd.DataFrame(
    [
        {
            "Selected_model": winner,
            "Peer_baseline_MAE_AUD": peer_mae,
            "Selected_model_MAE_AUD": model_mae,
            "MAE_improvement_pct": (
                mae_improvement * 100
                if mae_improvement is not None
                else np.nan
            ),
        }
    ]
)

export_table(
    improvement_table,
    "predictive_baseline_improvement",
)


# ==================== Calculate validation permutation importance ====================

# Use the training-fitted model and validation observations.
# Do not use the final test set to calculate feature importance.

permutation = permutation_importance(
    fitted_models[winner],
    X.iloc[validation_index],
    y.iloc[validation_index],
    scoring="neg_mean_absolute_error",
    n_repeats=3,
    random_state=42,
    n_jobs=1,
)

importance = pd.DataFrame(
    {
        "feature": FEATURES,
        "value": permutation.importances_mean,
        "std": permutation.importances_std,
    }
).sort_values(
    "value",
    ascending=False,
).reset_index(drop=True)

export_table(
    importance,
    "importance",
)

show_table(
    importance.round(3)
)


# ==================== Generate two-night segment price references ====================

prediction_rows = []

for _, segment in sc.iterrows():

    peers = q.loc[
        q["area"].eq(segment["area"])
        & q["property_group"].eq(segment["property_group"])
        & q["bedrooms"].eq(segment["bedrooms"])
    ]

    matched = peers.loc[
        peers["quote_nights"].eq(2)
        & peers["minimum_nights"].le(2)
    ]

    if matched.empty:
        reference_price = np.nan

    else:
        reference_price = float(
            np.median(
                selected_model.predict(
                    matched[FEATURES]
                )
            )
        )

    prediction_rows.append(
        {
            "area": segment["area"],
            "property_group": segment["property_group"],
            "bedrooms": int(segment["bedrooms"]),
            "model": reference_price,
            "matched_n": len(matched),
            "matched_hosts": matched[GROUP].nunique(),
            "matched_median": matched[TARGET].median(),
            "matched_p25": matched[TARGET].quantile(0.25),
            "matched_p75": matched[TARGET].quantile(0.75),
            "quote_lead_p25": matched["quote_lead"].quantile(0.25),
            "quote_lead_p75": matched["quote_lead"].quantile(0.75),
        }
    )

segment_predictions = pd.DataFrame(
    prediction_rows
)

candidate_quotes = sc.merge(
    segment_predictions,
    on=[
        "area",
        "property_group",
        "bedrooms",
    ],
    how="left",
    validate="one_to_one",
)

export_table(
    candidate_quotes,
    "predictive_candidate_quotes",
)

show_table(
    candidate_quotes.loc[
        candidate_quotes["n"].ge(50),
        [
            "area",
            "property_group",
            "bedrooms",
            "n",
            "model",
            "matched_n",
            "matched_median",
        ],
    ].round(2)
)

# Segment references summarize model predictions for observed listings.
# They are not independent test results, optimal prices, or future prices.
# Two-night matching uses actual quoted stay duration and minimum-stay rules.


# ==================== Save the selected model ====================

model_path = (
    MODELS / "selected_price_model.joblib"
)

joblib.dump(
    selected_model,
    model_path,
)


# ==================== Save feature schema ====================

feature_schema = {
    "target": TARGET,
    "target_unit": "AUD per night",
    "grouping_variable": GROUP,
    "numeric_features": NUMERIC_FEATURES,
    "categorical_features": CATEGORICAL_FEATURES,
    "selected_model": winner,
    "training_scope": (
        "Confirmed non-Superhost entire-home listings "
        "meeting the price-analysis scope"
    ),
}

(MODELS / "price_model_features.json").write_text(
    json.dumps(
        feature_schema,
        indent=2,
    ),
    encoding="utf-8",
)


# ==================== Save model metadata ====================

package_versions = {
    package: importlib.metadata.version(package)
    for package in [
        "numpy",
        "pandas",
        "scikit-learn",
        "joblib",
    ]
}

model_metadata = {
    "selected_model": winner,
    "selection_metric": "Validation MAE",
    "validation": validation_results,
    "test": test_results,
    "split_listings": {
        "training": len(train_index),
        "validation": len(validation_index),
        "test": len(test_index),
    },
    "split_hosts": {
        "training": len(train_hosts),
        "validation": len(validation_hosts),
        "test": len(test_hosts),
    },
    "peer_baseline_mae_improvement": mae_improvement,
    "saved_model": model_path.name,
    "model_fit_sample": "Development sample",
    "package_versions": package_versions,
}

(MODELS / "price_model_metadata.json").write_text(
    json.dumps(
        model_metadata,
        indent=2,
        allow_nan=False,
    ),
    encoding="utf-8",
)


# ==================== Generate predictive-analysis charts ====================

# These functions read test.csv and importance.csv from the tables folder.

viz.plot_model_match()
viz.plot_model_error()
viz.plot_model_drivers()


# ==================== Print completion summary ====================

print()
print("Predictive analysis completed.")
print()

print(f"Selected model: {winner}")

print(
    "Final test MAE: "
    f"A${test_results['Selected model']['MAE']:.2f} per night"
)

print(
    "Final test median absolute error: "
    f"A${test_results['Selected model']['MedAE']:.2f} per night"
)

print(
    "Predictions within 25% of recorded listed prices: "
    f"{test_results['Selected model']['within25']:.1%}"
)

if mae_improvement is not None:
    print(
        "MAE improvement over the area-bedroom baseline: "
        f"{mae_improvement:.1%}"
    )

print()
print(f"Segment price references: {len(candidate_quotes):,}")
print(f"Figure directory: {F}")
print(f"Table directory: {T}")
print(f"Model directory: {MODELS}")

print()
print(
    "Predictions represent reference nightly listed prices, "
    "not actual transaction prices or profit-maximizing prices."
)
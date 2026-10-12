#This part will be used to quotation model training and rental plan generation
#And it will prepare for the later modeling analysing and EDA process
from pathlib import Path
import json
import pickle

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    RandomForestRegressor
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    mean_absolute_error,
    median_absolute_error,
    mean_squared_error,
    r2_score
)
from sklearn.base import clone
from sklearn.inspection import permutation_importance


# ==================== Local file paths ====================

# Save this script in the project's data folder.
PROJECT_FOLDER = Path(__file__).resolve().parent.parent

OUTPUT_FOLDER = PROJECT_FOLDER / "analysis_outputs"
TABLE_FOLDER = OUTPUT_FOLDER / "tables"
MODEL_FOLDER = OUTPUT_FOLDER / "models"

for folder in [TABLE_FOLDER, MODEL_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

INPUT_FILE = TABLE_FOLDER / "listings_prepared.csv"

AMENITIES = [
    "Wifi", "Kitchen", "Free parking", "Self check-in",
    "Pool", "Fireplace", "Hot tub", "Pets allowed",
    "Workspace", "BBQ", "Garden", "Air conditioning"
]

NUMERIC_FEATURES = [
    "bedrooms", "accommodates", "bath_num",
    "minimum_nights", "quote_nights", "quote_lead",
    "quote_weekend"
] + AMENITIES

CATEGORICAL_FEATURES = [
    "area", "property_group", "quote_month"
]

FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def evaluate(actual, predicted):
    """Evaluate nightly listing-price predictions."""
    actual = np.asarray(actual)
    predicted = np.asarray(predicted)

    return {
        "MAE": float(mean_absolute_error(actual, predicted)),
        "MedAE": float(median_absolute_error(actual, predicted)),
        "within25": float(
            np.mean(np.abs(actual - predicted) / actual <= 0.25)
        ),
        "RMSE": float(np.sqrt(mean_squared_error(actual, predicted))),
        "R2": float(r2_score(actual, predicted))
    }


def save_json(path, content):
    """Save metadata to a local JSON file."""
    path.write_text(
        json.dumps(content, indent=2),
        encoding="utf-8"
    )


def load_modeling_data():
    """Read prepared listings from disk and select the modeling sample."""
    if not INPUT_FILE.is_file():
        raise FileNotFoundError(
            f"Prepared listings file not found: {INPUT_FILE}. "
            "Run Data_overview.py first."
        )

    required_columns = [
        "id", "host_id", "source", "room_type", "price_aud",
        "bedrooms", "accommodates", "bath_num", "minimum_nights",
        "quote_nights", "quote_lead", "price_quote_checkin_date",
        "area", "property_group", "recent_reviews",
        "mature", "has_review"
    ] + AMENITIES

    data = pd.read_csv(
        INPUT_FILE,
        usecols=required_columns,
        dtype={
            "id": "string",
            "host_id": "string",
            "mature": "boolean",
            "has_review": "boolean"
        },
        low_memory=False
    )

    sample = data.loc[
        data["source"].eq("city scrape")
        & data["room_type"].eq("Entire home/apt")
        & data["price_aud"].between(20, 2000)
        & data["bedrooms"].between(1, 3)
        & data["accommodates"].between(1, 8)
        & data["minimum_nights"].between(1, 7)
        & data["quote_nights"].between(1, 7)
        & data["quote_lead"].between(0, 30)
    ].copy()

    if sample.empty:
        raise ValueError("No listings meet the modeling criteria.")

    if sample["host_id"].isna().any():
        raise ValueError("The modeling sample contains missing host IDs.")

    if sample[["mature", "has_review"]].isna().any().any():
        raise ValueError("The modeling sample contains missing review flags.")

    sample["mature"] = sample["mature"].astype(bool)
    sample["has_review"] = sample["has_review"].astype(bool)

    dates = pd.to_datetime(sample["price_quote_checkin_date"])
    sample["quote_weekend"] = dates.dt.dayofweek.ge(5).astype(int)
    sample["quote_month"] = dates.dt.month.astype(str)

    sample.reset_index(drop=True, inplace=True)

    sample.to_csv(
        TABLE_FOLDER / "modeling_sample.csv",
        index=False
    )

    return sample


def build_models():
    """Create regression pipelines with preprocessing."""
    preprocessing = ColumnTransformer([
        (
            "num",
            Pipeline([
                (
                    "impute",
                    SimpleImputer(strategy="median", add_indicator=True)
                ),
                ("scale", StandardScaler())
            ]),
            NUMERIC_FEATURES
        ),
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            CATEGORICAL_FEATURES
        )
    ])

    def make_pipeline(estimator, log_target=True):
        pipeline = Pipeline([
            ("prepare", clone(preprocessing)),
            ("model", estimator)
        ])

        if log_target:
            return TransformedTargetRegressor(
                regressor=pipeline,
                func=np.log,
                inverse_func=np.exp
            )

        return pipeline

    return {
        "Log Ridge Regression": make_pipeline(Ridge(alpha=15)),
        "Log Random Forest": make_pipeline(
            RandomForestRegressor(
                n_estimators=180,
                min_samples_leaf=8,
                max_depth=18,
                max_features=0.8,
                n_jobs=2,
                random_state=42
            )
        ),
        "Histogram Gradient Boosting": make_pipeline(
            HistGradientBoostingRegressor(
                loss="absolute_error",
                max_iter=200,
                max_leaf_nodes=15,
                min_samples_leaf=40,
                l2_regularization=3,
                random_state=42
            ),
            log_target=False
        )
    }


def generate_scenarios(sample, model):
    """Generate reference launch prices using local comparable listings."""
    scenarios = []

    for area in [
        "Melbourne", "Yarra", "Port Phillip",
        "Stonnington", "Moreland", "Yarra Ranges"
    ]:
        for bedrooms in [1, 2, 3]:
            property_group = (
                "Cottage/Guesthouse"
                if area == "Yarra Ranges"
                else "Apartment"
            )

            peers = sample.loc[
                sample["area"].eq(area)
                & sample["bedrooms"].eq(bedrooms)
                & sample["accommodates"].between(
                    bedrooms * 2, bedrooms * 2 + 1
                )
                & sample["property_group"].eq(property_group)
            ]

            if len(peers) < 20:
                continue

            mature_peers = peers.loc[peers["mature"]]

            template = peers[NUMERIC_FEATURES].median().to_dict()
            template.update({
                "area": area,
                "property_group": property_group,
                "quote_month": "6",
                "quote_weekend": 0,
                "bedrooms": bedrooms,
                "accommodates": bedrooms * 2,
                "bath_num": 1 if bedrooms < 3 else 2,
                "minimum_nights": 2,
                "quote_nights": 2,
                "quote_lead": 3
            })

            for amenity in AMENITIES:
                template[amenity] = int(peers[amenity].mean() >= 0.5)

            template.update({
                "Wifi": 1,
                "Kitchen": 1,
                "Air conditioning": 1,
                "Self check-in": 1
            })

            if area == "Yarra Ranges":
                template.update({
                    "Free parking": 1,
                    "Garden": 1,
                    "Fireplace": 1
                })
            else:
                template.update({
                    "Pool": 0,
                    "Hot tub": 0,
                    "Fireplace": 0
                })

            model_price = float(
                model.predict(pd.DataFrame([template])[FEATURES])[0]
            )

            matched = peers.loc[
                peers["quote_nights"].eq(2)
                & peers["minimum_nights"].le(2)
            ]

            used_fallback = len(matched) < 30
            if used_fallback:
                matched = peers

            # Bound the reference price by peer P25–P75.
            # This rule does not estimate the most profitable price.
            anchor = float(np.clip(
                model_price,
                matched["price_aud"].quantile(0.25),
                matched["price_aud"].quantile(0.75)
            ))

            launch_price = int(np.floor(anchor / 10 + 0.5) * 10)

            scenarios.append({
                "area": area,
                "bedrooms": bedrooms,
                "property_group": property_group,
                "n": len(peers),
                "mature_n": len(mature_peers),
                "median": peers["price_aud"].median(),
                "p25": peers["price_aud"].quantile(0.25),
                "p75": peers["price_aud"].quantile(0.75),
                "reviews": mature_peers["recent_reviews"].median(),
                "active": mature_peers["has_review"].mean(),
                "model": model_price,
                "matched_n": len(matched),
                "matched_median": matched["price_aud"].median(),
                "matched_p25": matched["price_aud"].quantile(0.25),
                "matched_p75": matched["price_aud"].quantile(0.75),
                "used_fallback": used_fallback,
                "launch": launch_price,
                "template": json.dumps(template)
            })

    if not scenarios:
        raise ValueError(
            "No product scenarios meet the minimum sample requirement."
        )

    results = pd.DataFrame(scenarios)
    results.to_csv(TABLE_FOLDER / "scenarios.csv", index=False)

    results.drop(columns="template").round(2).to_csv(
        TABLE_FOLDER / "08_all_product_comparisons.csv",
        index=False,
        encoding="utf-8-sig"
    )

    selected = pd.concat([
        results.loc[
            results["area"].eq(area)
            & results["bedrooms"].eq(bedrooms)
        ]
        for area, bedrooms in [
            ("Yarra", 1),
            ("Melbourne", 2),
            ("Yarra Ranges", 1)
        ]
    ], ignore_index=True)

    selected.drop(columns="template").round(2).to_csv(
        TABLE_FOLDER / "09_selected_plans.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nSelected product plans:")
    print(
        selected[
            ["area", "bedrooms", "model", "matched_n", "launch"]
        ].round(2).to_string(index=False)
    )


def main():
    sample = load_modeling_data()

    X = sample[FEATURES]
    y = sample["price_aud"]
    groups = sample["host_id"]

    # Split by host to prevent overlap between sets.
    development, test_indices = next(
        GroupShuffleSplit(
            n_splits=1,
            test_size=0.2,
            random_state=42
        ).split(X, y, groups)
    )

    train_local, validation_local = next(
        GroupShuffleSplit(
            n_splits=1,
            test_size=0.25,
            random_state=43
        ).split(
            X.iloc[development],
            y.iloc[development],
            groups.iloc[development]
        )
    )

    train_indices = development[train_local]
    validation_indices = development[validation_local]

    # Save split membership for reproducibility.
    split_table = sample[["id", "host_id"]].copy()
    split_table["split"] = ""

    split_table.loc[train_indices, "split"] = "train"
    split_table.loc[validation_indices, "split"] = "validation"
    split_table.loc[test_indices, "split"] = "test"

    split_table.to_csv(
        TABLE_FOLDER / "model_split.csv",
        index=False
    )

    models = build_models()
    validation_results = {}
    fitted_models = {}

    for name, model in models.items():
        print(f"Training: {name}")

        model.fit(X.iloc[train_indices], y.iloc[train_indices])
        predictions = model.predict(X.iloc[validation_indices])

        validation_results[name] = evaluate(
            y.iloc[validation_indices], predictions
        )
        fitted_models[name] = model

    pd.DataFrame(validation_results).T.to_csv(
        TABLE_FOLDER / "validation.csv"
    )

    # Select using validation MAE only.
    winner = min(
        validation_results,
        key=lambda name: validation_results[name]["MAE"]
    )

    selected_model = clone(models[winner]).fit(
        X.iloc[development],
        y.iloc[development]
    )

    model_path = MODEL_FOLDER / "price_model.pkl"
    with model_path.open("wb") as file:
        pickle.dump(selected_model, file)

    test_predictions = selected_model.predict(X.iloc[test_indices])
    global_median = float(y.iloc[development].median())

    global_predictions = np.repeat(global_median, len(test_indices))

    peer_medians = (
        sample.iloc[development]
        .groupby(["area", "bedrooms"])["price_aud"]
        .median()
    )

    peer_predictions = np.array([
        peer_medians.get((area, bedrooms), global_median)
        for area, bedrooms in zip(
            X.iloc[test_indices]["area"],
            X.iloc[test_indices]["bedrooms"]
        )
    ])

    test_results = {
        "Global Median": evaluate(
            y.iloc[test_indices], global_predictions
        ),
        "Area and Bedroom Median": evaluate(
            y.iloc[test_indices], peer_predictions
        ),
        "Selected Model": evaluate(
            y.iloc[test_indices], test_predictions
        )
    }

    pd.DataFrame(test_results).T.to_csv(TABLE_FOLDER / "test.csv")

    # Save individual test predictions.
    prediction_table = sample.iloc[test_indices][
        ["id", "host_id", "area", "bedrooms", "price_aud"]
    ].copy()

    prediction_table["predicted_price_aud"] = test_predictions
    prediction_table["global_median_prediction"] = global_predictions
    prediction_table["peer_median_prediction"] = peer_predictions

    prediction_table.to_csv(
        TABLE_FOLDER / "test_predictions.csv",
        index=False
    )

    importance_result = permutation_importance(
        fitted_models[winner],
        X.iloc[validation_indices],
        y.iloc[validation_indices],
        scoring="neg_mean_absolute_error",
        n_repeats=3,
        random_state=42,
        n_jobs=1
    )

    importance_table = pd.DataFrame({
        "feature": FEATURES,
        "value": importance_result.importances_mean
    }).sort_values("value", ascending=False)

    importance_table.to_csv(
        TABLE_FOLDER / "importance.csv",
        index=False
    )

    save_json(MODEL_FOLDER / "model_meta.json", {
        "winner": winner,
        "validation": validation_results,
        "test": test_results,
        "split": [
            len(train_indices),
            len(validation_indices),
            len(test_indices)
        ],
        "features": FEATURES,
        "nums": NUMERIC_FEATURES,
        "cats": CATEGORICAL_FEATURES,
        "input_file": str(INPUT_FILE)
    })

    # Reload the saved model before generating scenarios.
    with model_path.open("rb") as file:
        saved_model = pickle.load(file)

    generate_scenarios(sample, saved_model)

    print(f"\nModeling sample: {len(sample):,} listings")
    print(f"Selected model: {winner}")
    print(f"Model saved to: {model_path}")
    print(f"Tables saved to: {TABLE_FOLDER}")

    print("\nTest results:")
    print(pd.DataFrame(test_results).T.round(3).to_string())


if __name__ == "__main__":
    main()
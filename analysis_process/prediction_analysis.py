# ==================== Install missing packages ====================

import importlib.util
import subprocess
import sys

packages = {
    'pandas': 'pandas',
    'numpy': 'numpy',
    'matplotlib': 'matplotlib',
    'sklearn': 'scikit-learn',
    'joblib': 'joblib'
}

missing_packages = [
    package_name
    for module_name, package_name in packages.items()
    if importlib.util.find_spec(module_name) is None
]

if missing_packages:
    subprocess.check_call([
        sys.executable,
        '-m',
        'pip',
        'install',
        *missing_packages
    ])


# ==================== Import packages ====================

import json
from pathlib import Path
from importlib.metadata import version

import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.base import clone
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import (
    RandomForestRegressor,
    HistGradientBoostingRegressor
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    mean_absolute_error,
    median_absolute_error,
    mean_squared_error,
    r2_score
)
from sklearn.inspection import permutation_importance


# ==================== Set output folders ====================

OUT = Path('analysis_output')

FIGURES = OUT / 'figures'
CHARTS = OUT / 'charts'
MODELS = OUT / 'models'

for folder in [FIGURES, CHARTS, MODELS]:
    folder.mkdir(parents=True, exist_ok=True)

pd.set_option('display.max_columns', 25)
pd.set_option('display.width', 180)


# ==================== Set chart colors and styles ====================

NAVY = '#183C4A'
TEAL = '#168A85'
GOLD = '#D58A39'
BLUE = '#5386AF'
GRAY = '#C9D2D5'

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.unicode_minus': False,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'text.color': NAVY,
    'axes.labelcolor': NAVY
})


# ==================== Define helper functions ====================

def locate_listings():
    folders = [
        Path('.'),
        Path('data'),
        Path('upload'),
        Path('../upload'),
        Path('/content')
    ]

    filenames = [
        'listings (1).csv.gz',
        'listings.csv.gz',
        'listings.csv'
    ]

    for folder in folders:
        for filename in filenames:
            path = folder / filename

            if path.is_file():
                return path

    raise FileNotFoundError(
        'Place listings (1).csv.gz, listings.csv.gz, or '
        'listings.csv in the project folder or data folder.'
    )


def parse_amenities(value):
    if not isinstance(value, str):
        return ''

    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value.lower()

    if isinstance(parsed, list):
        return ' | '.join(str(item) for item in parsed).lower()

    return str(parsed).lower()


def save_table(frame, name):
    frame.to_csv(
        CHARTS / f'{name}.csv',
        index=False,
        encoding='utf-8-sig'
    )

    print(f'\n{name}')
    print(frame.to_string(index=False))


def save_figure(fig, name):
    fig.tight_layout()

    fig.savefig(
        FIGURES / f'{name}.png',
        dpi=165,
        bbox_inches='tight'
    )

    plt.show()
    plt.close(fig)


def evaluate(actual, predicted):
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    return {
        'MAE': float(mean_absolute_error(actual, predicted)),
        'MedAE': float(median_absolute_error(actual, predicted)),
        'Within_25_Percent': float(
            np.mean(np.abs(actual - predicted) / actual <= 0.25)
        ),
        'RMSE': float(np.sqrt(mean_squared_error(actual, predicted))),
        'R2': float(r2_score(actual, predicted))
    }


# ==================== Load the listings dataset ====================

listing_path = locate_listings()
raw = pd.read_csv(listing_path, low_memory=False)

required_columns = [
    'id',
    'host_id',
    'last_scraped',
    'price',
    'bedrooms',
    'accommodates',
    'minimum_nights',
    'neighbourhood_cleansed',
    'bathrooms_text',
    'price_quote_checkin_date',
    'price_quote_checkout_date',
    'source',
    'room_type',
    'property_type',
    'amenities'
]

missing_columns = [
    column
    for column in required_columns
    if column not in raw.columns
]

if missing_columns:
    raise ValueError(
        f'The listings file is missing required columns: {missing_columns}'
    )

print(f'Loaded file: {listing_path}')


# ==================== Prepare listing variables ====================

l = raw.dropna(subset=['id']).copy()

l['_scraped_order'] = pd.to_datetime(
    l['last_scraped'],
    errors='coerce'
)

l = (
    l.sort_values('_scraped_order', kind='stable')
    .drop_duplicates('id', keep='last')
    .sort_index()
    .drop(columns='_scraped_order')
)

l['price_aud'] = pd.to_numeric(
    l['price']
    .astype('string')
    .str.replace(r'[$,]', '', regex=True),
    errors='coerce'
)

for column in ['bedrooms', 'accommodates', 'minimum_nights']:
    l[column] = pd.to_numeric(l[column], errors='coerce')

l['area'] = l['neighbourhood_cleansed']

bathroom_text = l['bathrooms_text'].astype('string')

l['bath_num'] = pd.to_numeric(
    bathroom_text.str.extract(r'(\d+(?:\.\d+)?)')[0],
    errors='coerce'
)

l.loc[
    bathroom_text.str.contains(
        'half-bath',
        case=False,
        na=False
    ),
    'bath_num'
] = 0.5

checkin = pd.to_datetime(
    l['price_quote_checkin_date'],
    errors='coerce'
)

checkout = pd.to_datetime(
    l['price_quote_checkout_date'],
    errors='coerce'
)

scraped = pd.to_datetime(
    l['last_scraped'],
    errors='coerce'
)

l['quote_nights'] = (checkout - checkin).dt.days
l['quote_lead'] = (checkin - scraped).dt.days
l['quote_weekend'] = checkin.dt.dayofweek.ge(5).astype(int)
l['quote_month'] = checkin.dt.month.astype('Int64').astype('string')

l['property_group'] = np.select(
    [
        l['property_type'].isin([
            'Entire rental unit',
            'Entire condo',
            'Entire serviced apartment',
            'Entire loft'
        ]),
        l['property_type'].isin([
            'Entire home',
            'Entire townhouse'
        ]),
        l['property_type'].isin([
            'Entire cottage',
            'Entire cabin',
            'Entire guesthouse',
            'Entire guest suite',
            'Tiny home',
            'Farm stay'
        ])
    ],
    [
        'Apartment',
        'House / townhouse',
        'Cottage / guesthouse'
    ],
    default='Other'
)


# ==================== Extract amenity indicators ====================

amenity_patterns = {
    'WiFi': r'\bwifi\b',
    'Kitchen': r'\bkitchen\b',
    'Free parking': (
        r'\bfree parking on premises\b|'
        r'\bfree driveway parking\b'
    ),
    'Self check-in': r'\bself check-in\b',
    'Pool': r'\bpool\b',
    'Fireplace': r'\b(?:indoor fireplace|fireplace)\b',
    'Hot tub': r'\bhot tub\b',
    'Pets allowed': r'\bpets allowed\b',
    'Workspace': r'\bdedicated workspace\b',
    'BBQ': r'\bbbq\b',
    'Garden': r'\bbackyard\b|\bgarden\b',
    'Air conditioning': r'air conditioning'
}

amen = list(amenity_patterns)
amenity_text = l['amenities'].map(parse_amenities)

for feature, pattern in amenity_patterns.items():
    l[feature] = (
        amenity_text.str.contains(
            pattern,
            regex=True,
            na=False
        )
        .astype(int)
    )


# ==================== Define the modeling sample ====================

e = l.loc[
    l['source'].eq('city scrape')
    & l['room_type'].eq('Entire home/apt')
].copy()

q = e.loc[
    e['price_aud'].between(20, 2000)
    & e['bedrooms'].between(1, 3)
    & e['accommodates'].between(1, 8)
    & e['minimum_nights'].between(1, 7)
    & e['quote_nights'].between(1, 7)
    & e['quote_lead'].between(0, 30)
].copy()

# Host IDs are required to prevent host overlap across data splits.
missing_host_count = int(q['host_id'].isna().sum())
q = q.dropna(subset=['host_id']).reset_index(drop=True)

if q.empty or q['host_id'].nunique() < 5:
    raise ValueError(
        'Insufficient listings or distinct hosts for grouped splitting.'
    )

print(f'Modeling listings: {len(q):,}')
print(f'Excluded listings with missing host IDs: {missing_host_count:,}')


# ==================== Define predictors and target ====================

nums = [
    'bedrooms',
    'accommodates',
    'bath_num',
    'minimum_nights',
    'quote_nights',
    'quote_lead',
    'quote_weekend'
] + amen

cats = [
    'area',
    'property_group',
    'quote_month'
]

# Replace missing categorical values with an explicit label.
for column in cats:
    q[column] = (
        q[column]
        .astype('string')
        .fillna('Unknown')
        .astype(str)
    )

X = q[nums + cats].copy()
y = q['price_aud'].copy()
groups = q['host_id'].copy()

save_table(
    pd.DataFrame({
        'Feature': nums + cats,
        'Type': ['Numeric'] * len(nums) + ['Categorical'] * len(cats)
    }),
    'predictive_features'
)


# ==================== Split data by host ====================

# Reserve approximately 20% of host groups for the final test.
development_index, test_index = next(
    GroupShuffleSplit(
        n_splits=1,
        test_size=0.20,
        random_state=42
    ).split(X, y, groups)
)

# Use approximately 25% of development host groups for validation.
train_relative, validation_relative = next(
    GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=43
    ).split(
        X.iloc[development_index],
        y.iloc[development_index],
        groups.iloc[development_index]
    )
)

train_index = development_index[train_relative]
validation_index = development_index[validation_relative]

assert set(groups.iloc[train_index]).isdisjoint(
    set(groups.iloc[validation_index])
)

assert set(groups.iloc[development_index]).isdisjoint(
    set(groups.iloc[test_index])
)

split_labels = np.full(len(q), '', dtype=object)
split_labels[train_index] = 'Train'
split_labels[validation_index] = 'Validation'
split_labels[test_index] = 'Test'

save_table(
    pd.DataFrame({
        'Split': ['Train', 'Validation', 'Test'],
        'Listings': [
            len(train_index),
            len(validation_index),
            len(test_index)
        ],
        'Hosts': [
            groups.iloc[train_index].nunique(),
            groups.iloc[validation_index].nunique(),
            groups.iloc[test_index].nunique()
        ]
    }),
    'predictive_data_split'
)

# Save listing-to-split assignments for reproducibility.
q[['id', 'host_id']].assign(Split=split_labels).to_csv(
    CHARTS / 'predictive_split_assignments.csv',
    index=False,
    encoding='utf-8-sig'
)


# ==================== Define preprocessing ====================

numeric_pipeline = Pipeline([
    (
        'impute',
        SimpleImputer(
            strategy='median',
            add_indicator=True
        )
    ),
    ('scale', StandardScaler())
])

# Support both older and newer scikit-learn versions.
try:
    encoder = OneHotEncoder(
        handle_unknown='ignore',
        sparse_output=False
    )
except TypeError:
    encoder = OneHotEncoder(
        handle_unknown='ignore',
        sparse=False
    )

preprocessor = ColumnTransformer([
    ('num', numeric_pipeline, nums),
    ('cat', encoder, cats)
])


# ==================== Define candidate models ====================

def build_model(estimator, log_target=True):
    pipeline = Pipeline([
        ('prepare', clone(preprocessor)),
        ('model', estimator)
    ])

    if log_target:
        return TransformedTargetRegressor(
            regressor=pipeline,
            func=np.log,
            inverse_func=np.exp
        )

    return pipeline


models = {
    'Log-Target Ridge Regression': build_model(
        Ridge(alpha=15)
    ),

    'Log-Target Random Forest': build_model(
        RandomForestRegressor(
            n_estimators=180,
            min_samples_leaf=8,
            max_depth=18,
            max_features=0.8,
            n_jobs=2,
            random_state=42
        )
    ),

    'Gradient Boosting': build_model(
        HistGradientBoostingRegressor(
            loss='absolute_error',
            max_iter=200,
            max_leaf_nodes=15,
            min_samples_leaf=40,
            l2_regularization=3,
            random_state=42
        ),
        log_target=False
    )
}


# ==================== P1: Train and validate candidate models ====================

validation_results = {}
fitted_validation_models = {}

for name, model in models.items():
    print(f'\nTraining: {name}')

    model.fit(
        X.iloc[train_index],
        y.iloc[train_index]
    )

    validation_predictions = model.predict(
        X.iloc[validation_index]
    )

    validation_results[name] = evaluate(
        y.iloc[validation_index],
        validation_predictions
    )

    fitted_validation_models[name] = model

validation_table = (
    pd.DataFrame(validation_results)
    .T
    .rename_axis('Model')
    .reset_index()
)

save_table(
    validation_table.round(4),
    'predictive_validation_metrics'
)

winner = min(
    validation_results,
    key=lambda name: validation_results[name]['MAE']
)

print(f'\nSelected model based on validation MAE: {winner}')


# ==================== P1: Refit the selected model ====================

# Fit on train + validation data.
# The final test hosts remain excluded.
fit = clone(models[winner])

fit.fit(
    X.iloc[development_index],
    y.iloc[development_index]
)

test_predictions = fit.predict(X.iloc[test_index])


# ==================== P1: Evaluate baseline methods ====================

development_median = float(
    y.iloc[development_index].median()
)

global_predictions = np.repeat(
    development_median,
    len(test_index)
)

group_medians = (
    q.iloc[development_index]
    .groupby(['area', 'bedrooms'])['price_aud']
    .median()
)

peer_predictions = np.array([
    group_medians.get(
        (area, bedrooms),
        development_median
    )
    for area, bedrooms in zip(
        X.iloc[test_index]['area'],
        X.iloc[test_index]['bedrooms']
    )
])

test_results = {
    'Global Median': evaluate(
        y.iloc[test_index],
        global_predictions
    ),

    'Area-Bedroom Median': evaluate(
        y.iloc[test_index],
        peer_predictions
    ),

    'Selected Model': evaluate(
        y.iloc[test_index],
        test_predictions
    )
}

test_table = (
    pd.DataFrame(test_results)
    .T
    .rename_axis('Method')
    .reset_index()
)

save_table(
    test_table.round(4),
    'predictive_test_metrics'
)

test_output = q.iloc[test_index][
    ['id', 'area', 'bedrooms', 'price_aud']
].copy()

test_output = test_output.rename(columns={
    'price_aud': 'Actual_Advertised_Price_AUD'
})

test_output['Model_Prediction_AUD'] = test_predictions
test_output['Global_Median_Prediction_AUD'] = global_predictions
test_output['Peer_Median_Prediction_AUD'] = peer_predictions

test_output['Absolute_Error_AUD'] = np.abs(
    test_output['Actual_Advertised_Price_AUD']
    - test_predictions
)

test_output.to_csv(
    CHARTS / 'predictive_test_predictions.csv',
    index=False,
    encoding='utf-8-sig'
)


# ==================== P1: Plot model performance ====================

fig, axes = plt.subplots(1, 2, figsize=(13, 5))

colors = [GRAY, BLUE, TEAL]

match_bars = axes[0].barh(
    test_table['Method'],
    test_table['Within_25_Percent'] * 100,
    color=colors
)

axes[0].invert_yaxis()
axes[0].set_xlim(0, 110)
axes[0].set_xlabel('Predictions within 25% of Advertised Price (%)')
axes[0].set_title('Price Matching Performance', fontweight='bold')

axes[0].bar_label(
    match_bars,
    fmt='%.1f%%',
    padding=4
)

error_bars = axes[1].barh(
    test_table['Method'],
    test_table['MedAE'],
    color=colors
)

axes[1].invert_yaxis()
axes[1].set_xlabel('Median Absolute Error (AUD per Night)')
axes[1].set_title('Typical Pricing Error', fontweight='bold')
axes[1].margins(x=0.2)

axes[1].bar_label(
    error_bars,
    fmt='%.1f',
    padding=4
)

save_figure(fig, 'predictive_model_performance')


# ==================== P1: Plot actual versus predicted prices ====================

actual = y.iloc[test_index].to_numpy()

fig, ax = plt.subplots(figsize=(7, 6))

ax.scatter(
    actual,
    test_predictions,
    s=12,
    alpha=0.25,
    color=TEAL,
    linewidths=0
)

lower = min(actual.min(), test_predictions.min())
upper = max(actual.max(), test_predictions.max())

ax.plot(
    [lower, upper],
    [lower, upper],
    linestyle='--',
    color=GOLD,
    label='Perfect Agreement'
)

ax.set_xlabel('Actual Advertised Nightly Price (AUD)')
ax.set_ylabel('Predicted Nightly Price (AUD)')

ax.set_title(
    'Held-Out Hosts: Actual versus Predicted Prices',
    loc='left',
    fontweight='bold'
)

ax.legend(frameon=False)

save_figure(fig, 'predictive_actual_vs_predicted')


# ==================== P2: Calculate permutation importance ====================

# Use the model fitted only on the training split.
# Calculate importance on validation data, not the final test.
permutation = permutation_importance(
    fitted_validation_models[winner],
    X.iloc[validation_index],
    y.iloc[validation_index],
    scoring='neg_mean_absolute_error',
    n_repeats=3,
    random_state=42,
    n_jobs=1
)

imp = pd.DataFrame({
    'Feature': X.columns,
    'MAE_Increase_AUD': permutation.importances_mean,
    'Importance_SD': permutation.importances_std
}).sort_values(
    'MAE_Increase_AUD',
    ascending=False
)

save_table(
    imp.round(4),
    'predictive_feature_importance'
)

top_importance = imp.head(10)

fig, ax = plt.subplots(figsize=(10, 6))

ax.barh(
    top_importance['Feature'],
    top_importance['MAE_Increase_AUD'],
    xerr=top_importance['Importance_SD'],
    color=TEAL,
    capsize=3
)

ax.invert_yaxis()
ax.axvline(0, color=GRAY, linewidth=1)

ax.set_xlabel('Increase in MAE after Shuffling the Feature (AUD)')

ax.set_title(
    'Permutation Importance on Validation Data',
    loc='left',
    fontweight='bold'
)

save_figure(fig, 'predictive_feature_importance')


# ==================== P3: Define candidate property groups ====================

urban_supply = (
    e.loc[e['property_group'].eq('Apartment')]
    .groupby('area')
    .size()
    .nlargest(4)
)

urban_areas = list(urban_supply.index)

comparison_areas = [
    'Melbourne',
    'Yarra',
    'Port Phillip',
    'Stonnington',
    'Moreland',
    'Yarra Ranges'
]

prediction_rows = []
template_rows = []

for area in comparison_areas:
    for bedrooms in [1, 2, 3]:
        property_group = (
            'Cottage / guesthouse'
            if area == 'Yarra Ranges'
            else 'Apartment'
        )

        peers = q.loc[
            q['area'].eq(area)
            & q['bedrooms'].eq(bedrooms)
            & q['accommodates'].between(
                2 * bedrooms,
                2 * bedrooms + 1
            )
            & q['property_group'].eq(property_group)
        ]

        if len(peers) < 20:
            continue

        template = peers[nums].median().to_dict()

        # Use the same quotation scenario as the original notebook:
        # June, weekday check-in, three days ahead, two-night stay.
        template.update({
            'area': area,
            'property_group': property_group,
            'quote_month': '6',
            'quote_weekend': 0,
            'bedrooms': bedrooms,
            'accommodates': 2 * bedrooms,
            'bath_num': 1 if bedrooms < 3 else 2,
            'minimum_nights': 2,
            'quote_nights': 2,
            'quote_lead': 3
        })

        for feature in amen:
            template[feature] = int(
                peers[feature].mean() >= 0.5
            )

        template.update({
            'WiFi': 1,
            'Kitchen': 1,
            'Air conditioning': 1,
            'Self check-in': 1
        })

        if area == 'Yarra Ranges':
            template.update({
                'Free parking': 1,
                'Garden': 1,
                'Fireplace': 1
            })
        else:
            template.update({
                'Pool': 0,
                'Hot tub': 0,
                'Fireplace': 0
            })

        model_input = pd.DataFrame([template])[X.columns]

        predicted_price = float(
            fit.predict(model_input)[0]
        )

        matched = peers.loc[
            peers['quote_nights'].eq(2)
            & peers['minimum_nights'].le(2)
        ]

        prediction_rows.append({
            'area': area,
            'bedrooms': bedrooms,
            'property_group': property_group,
            'n': len(peers),
            'model': predicted_price,
            'matched_n': len(matched),
            'matched_median': matched['price_aud'].median(),
            'matched_p25': matched['price_aud'].quantile(0.25),
            'matched_p75': matched['price_aud'].quantile(0.75),
            'template': json.dumps(template, ensure_ascii=False)
        })

        template_rows.append(template)

predictions = pd.DataFrame(prediction_rows)

if predictions.empty:
    raise ValueError(
        'No candidate property groups contain at least 20 listings.'
    )

save_table(
    predictions.drop(columns='template').round(2),
    'predictive_candidate_quotes'
)

# Save the exact product definitions used to generate the quotes.
predictions.to_csv(
    CHARTS / 'predictive_candidate_quotes_with_templates.csv',
    index=False,
    encoding='utf-8-sig'
)

pd.DataFrame(template_rows)[X.columns].to_csv(
    CHARTS / 'predictive_candidate_templates.csv',
    index=False,
    encoding='utf-8-sig'
)


# ==================== P3: Plot candidate product quotes ====================

prediction_view = predictions.loc[
    (
        predictions['area'].isin(urban_areas)
        & predictions['bedrooms'].isin([1, 2])
    )
    | (
        predictions['area'].eq('Yarra Ranges')
        & predictions['bedrooms'].eq(1)
    )
].copy()

if not prediction_view.empty:
    labels = [
        f'{row.area}: {int(row.bedrooms)}BR'
        for row in prediction_view.itertuples()
    ]

    positions = np.arange(len(prediction_view))
    height = 0.35

    fig, ax = plt.subplots(
        figsize=(11, max(5, len(prediction_view) * 0.65))
    )

    ax.barh(
        positions - height / 2,
        prediction_view['model'],
        height,
        color=TEAL,
        label='Model Reference Price'
    )

    ax.barh(
        positions + height / 2,
        prediction_view['matched_median'],
        height,
        color=GRAY,
        label='Two-Night Peer Median'
    )

    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.set_xlabel('Advertised Nightly Price (AUD)')

    ax.set_title(
        'Candidate Products under a Standard Quote Scenario',
        loc='left',
        fontweight='bold'
    )

    ax.legend(frameon=False)

    save_figure(fig, 'predictive_candidate_quotes')


# ==================== Save the selected model and baselines ====================

# The saved model contains preprocessing and the fitted estimator.
joblib.dump(
    fit,
    MODELS / 'selected_price_model.joblib'
)

joblib.dump(
    {
        'global_median': development_median,
        'area_bedroom_medians': group_medians
    },
    MODELS / 'price_baselines.joblib'
)

model_metadata = {
    'selected_model': winner,
    'target': 'Advertised nightly price in AUD',
    'features': list(X.columns),
    'numeric_features': nums,
    'categorical_features': cats,
    'validation_metrics': validation_results,
    'test_metrics': test_results,
    'split_listings': {
        'train': len(train_index),
        'validation': len(validation_index),
        'test': len(test_index)
    },
    'missing_host_ids_excluded': missing_host_count,
    'fitted_on': 'Development data: training plus validation',
    'test_hosts_excluded_from_fitting': True,
    'candidate_quote_scenario': {
        'month': 'June',
        'weekend_checkin': False,
        'lead_days': 3,
        'stay_nights': 2
    },
    'versions': {
        package: version(package)
        for package in [
            'pandas',
            'numpy',
            'matplotlib',
            'scikit-learn',
            'joblib'
        ]
    }
}

with open(
    MODELS / 'price_model_metadata.json',
    'w',
    encoding='utf-8'
) as file:
    json.dump(model_metadata, file, indent=2, ensure_ascii=False)


# ==================== Verify the saved model ====================

loaded_model = joblib.load(
    MODELS / 'selected_price_model.joblib'
)

verification_input = X.iloc[test_index[:5]]

np.testing.assert_allclose(
    loaded_model.predict(verification_input),
    fit.predict(verification_input)
)

print('\nSaved model verification passed.')


# ==================== Report output locations ====================

print('\nPredictive analysis completed.')
print(f'Selected model: {winner}')
print(f'Figures: {FIGURES.resolve()}')
print(f'Tables: {CHARTS.resolve()}')
print(f'Models: {MODELS.resolve()}')

print(
    '\nInterpretation: the model predicts reference advertised prices, '
    'not booking prices, occupancy, revenue, or profit. '
    'Feature importance does not establish causal price premiums.'
)
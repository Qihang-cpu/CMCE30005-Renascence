# ==================== Install missing packages ====================

import importlib.util
import subprocess
import sys

packages = {
    'pandas': 'pandas',
    'numpy': 'numpy',
    'matplotlib': 'matplotlib'
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

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


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

TEAL = '#168A85'
GOLD = '#D58A39'
BLUE = '#5386AF'
GRAY = '#C9D2D5'
NAVY = '#183C4A'

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


def load_table(filename, required_columns):
    path = CHARTS / filename

    if not path.is_file():
        raise FileNotFoundError(
            f'Missing file: {path}. '
            'Run the previous Descriptive and Predictive code first.'
        )

    frame = pd.read_csv(path)

    missing = [
        column
        for column in required_columns
        if column not in frame.columns
    ]

    if missing:
        raise ValueError(
            f'{filename} is missing required columns: {missing}'
        )

    return frame


# ==================== Load descriptive and predictive results ====================

keys = ['area', 'bedrooms', 'property_group']

descriptive = load_table(
    '04_comparable_property_groups.csv',
    keys + ['n', 'mature_n', 'median', 'reviews']
)

predictions = load_table(
    'predictive_candidate_quotes_with_templates.csv',
    keys + [
        'model',
        'matched_n',
        'matched_median',
        'matched_p25',
        'matched_p75',
        'template'
    ]
)

urban_supply = load_table(
    '03_urban_candidate_supply.csv',
    ['Area', 'Apartment_Listings']
)

urban_areas = urban_supply['Area'].tolist()

prediction_columns = keys + [
    'model',
    'matched_n',
    'matched_median',
    'matched_p25',
    'matched_p75',
    'template'
]

sc = descriptive.merge(
    predictions[prediction_columns],
    on=keys,
    how='inner',
    validate='one_to_one'
)

if sc.empty:
    raise ValueError(
        'No matching candidate groups were found between '
        'the descriptive and predictive results.'
    )

save_table(
    sc.drop(columns='template').round(3),
    'prescriptive_candidate_evidence'
)


# ==================== Define decision rules ====================

# These are project-defined business thresholds.
# They are not statistical significance criteria.
MIN_PEERS = 100
MIN_HISTORY = 80
MIN_TWO_NIGHT_PEERS = 30
ACTIVITY_FLOOR = 0.90
PRICE_STEP = 10

save_table(
    pd.DataFrame({
        'Rule': [
            'Minimum comparable listings',
            'Minimum listings with one year of review history',
            'Minimum two-night comparable listings',
            'Minimum review activity relative to Melbourne',
            'Trial price increment in AUD'
        ],
        'Value': [
            MIN_PEERS,
            MIN_HISTORY,
            MIN_TWO_NIGHT_PEERS,
            ACTIVITY_FLOOR,
            PRICE_STEP
        ]
    }),
    'prescriptive_decision_rules'
)


# ==================== S1: Define eligible city candidates ====================

def city_candidates(bedrooms):
    candidates = sc.loc[
        sc['area'].isin(urban_areas)
        & sc['bedrooms'].eq(bedrooms)
        & sc['property_group'].eq('Apartment')
    ].copy()

    candidates['sample_ok'] = (
        candidates['n'].ge(MIN_PEERS)
        & candidates['mature_n'].ge(MIN_HISTORY)
        & candidates['matched_n'].ge(MIN_TWO_NIGHT_PEERS)
    )

    return candidates


# ==================== S1: Select the one-bedroom city pilot ====================

reference_rows = sc.loc[
    sc['area'].eq('Melbourne')
    & sc['bedrooms'].eq(1)
    & sc['property_group'].eq('Apartment'),
    'reviews'
]

if len(reference_rows) != 1 or reference_rows.isna().any():
    raise ValueError(
        'A valid Melbourne one-bedroom review benchmark is required.'
    )

reference = float(reference_rows.iloc[0])
activity_threshold = reference * ACTIVITY_FLOOR

city_one = city_candidates(1)

city_one['activity_ok'] = (
    city_one['reviews'].ge(activity_threshold)
)

city_one['eligible'] = (
    city_one['sample_ok']
    & city_one['activity_ok']
)

qualified_a = (
    city_one.loc[city_one['eligible']]
    .sort_values(
        ['median', 'reviews'],
        ascending=False
    )
)

save_table(
    city_one.drop(columns='template').round(3),
    'prescriptive_one_bedroom_candidates'
)

if qualified_a.empty:
    raise ValueError(
        'No one-bedroom city candidate meets the stated rules. '
        'Review the candidate scope or business thresholds.'
    )

choice_a = qualified_a.iloc[0].copy()

print(
    f'\nAnnual review threshold: '
    f'{reference:.1f} × {ACTIVITY_FLOOR:.0%} '
    f'= {activity_threshold:.1f}'
)

print(f'Selected one-bedroom city pilot: {choice_a["area"]}')


# ==================== S1: Select the existing four-person product ====================

city_two = city_candidates(2)

qualified_b = (
    city_two.loc[city_two['sample_ok']]
    .sort_values(
        ['reviews', 'median'],
        ascending=False,
        na_position='last'
    )
)

save_table(
    city_two.drop(columns='template').round(3),
    'prescriptive_two_bedroom_candidates'
)

if qualified_b.empty:
    raise ValueError(
        'No two-bedroom city candidate meets the sample requirements.'
    )

choice_b = qualified_b.iloc[0].copy()

if pd.isna(choice_b['reviews']):
    raise ValueError(
        'The selected two-bedroom candidate has no valid review metric.'
    )

print(f'Selected four-person product: {choice_b["area"]}')


# ==================== S1: Check the existing retreat property scenario ====================

retreat_rows = sc.loc[
    sc['area'].eq('Yarra Ranges')
    & sc['bedrooms'].eq(1)
    & sc['property_group'].eq('Cottage / guesthouse')
]

if len(retreat_rows) != 1:
    raise ValueError(
        'A unique Yarra Ranges one-bedroom retreat candidate is required.'
    )

choice_c = retreat_rows.iloc[0].copy()

if choice_c['matched_n'] < MIN_TWO_NIGHT_PEERS:
    raise ValueError(
        'The retreat scenario has too few two-night comparable listings.'
    )

retreat_template = json.loads(choice_c['template'])

required_retreat_amenities = [
    'Fireplace',
    'Free parking',
    'Garden'
]

if not all(
    retreat_template.get(feature) == 1
    for feature in required_retreat_amenities
):
    raise ValueError(
        'The retreat prediction template does not include '
        'the required amenities.'
    )

print(
    'Retreat quote applies only if the actual property matches '
    'the specified configuration.'
)


# ==================== S2: Combine selected products ====================

selected = pd.DataFrame([
    choice_a.to_dict(),
    choice_b.to_dict(),
    choice_c.to_dict()
]).reset_index(drop=True)

selected['plan'] = [
    'A: City Pilot',
    'B: Existing Four-Person Property',
    'C: Existing Retreat Property'
]


# ==================== S2: Choose trial prices within peer constraints ====================

def choose_trial_price(row):
    required = [
        row['model'],
        row['matched_p25'],
        row['matched_p75']
    ]

    if not np.isfinite(required).all():
        raise ValueError(
            f'Missing or invalid pricing evidence for {row["area"]}.'
        )

    lower = (
        np.ceil(row['matched_p25'] / PRICE_STEP)
        * PRICE_STEP
    )

    upper = (
        np.floor(row['matched_p75'] / PRICE_STEP)
        * PRICE_STEP
    )

    grid = np.arange(
        lower,
        upper + 1,
        PRICE_STEP
    )

    if len(grid) == 0:
        raise ValueError(
            f'No A${PRICE_STEP} price increment falls within '
            f'the peer interquartile range for {row["area"]}.'
        )

    # Select the allowed price closest to the model reference.
    return int(
        grid[np.argmin(np.abs(grid - row['model']))]
    )


selected['launch'] = selected.apply(
    choose_trial_price,
    axis=1
)

selected['minimum_stay'] = 2

selection_view = selected[
    [
        'plan',
        'area',
        'bedrooms',
        'model',
        'matched_n',
        'matched_p25',
        'matched_median',
        'matched_p75',
        'launch',
        'minimum_stay'
    ]
].rename(columns={
    'plan': 'Plan',
    'area': 'Area',
    'bedrooms': 'Bedrooms',
    'model': 'Model_Reference_Price_AUD',
    'matched_n': 'Two_Night_Comparable_Listings',
    'matched_p25': 'Peer_P25_AUD',
    'matched_median': 'Peer_Median_AUD',
    'matched_p75': 'Peer_P75_AUD',
    'launch': 'Trial_Nightly_Price_AUD',
    'minimum_stay': 'Minimum_Stay_Nights'
})

save_table(
    selection_view.round(2),
    'prescriptive_selected_plans'
)

# Preserve exact templates and unrounded values for later use.
selected.to_csv(
    CHARTS / 'prescriptive_selected_plans_full.csv',
    index=False,
    encoding='utf-8-sig'
)


# ==================== S2: Plot trial prices and peer medians ====================

positions = np.arange(len(selected))
width = 0.34

fig, ax = plt.subplots(figsize=(11, 6))

for offset, column, label, color in [
    (-width / 2, 'matched_median', 'Two-Night Peer Median', GRAY),
    (width / 2, 'launch', 'Selected Trial Price', TEAL)
]:
    bars = ax.bar(
        positions + offset,
        selected[column],
        width,
        label=label,
        color=color
    )

    ax.bar_label(
        bars,
        fmt='%.0f',
        padding=4,
        fontweight='bold'
    )

labels = [
    f'{row.area}\n{int(row.bedrooms)}BR'
    for row in selected.itertuples()
]

ax.set_xticks(positions, labels)
ax.set_ylabel('Advertised Nightly Price (AUD)')

ax.set_title(
    'Selected Trial Prices and Comparable Market Medians',
    loc='left',
    fontweight='bold'
)

ax.margins(y=0.2)
ax.legend(frameon=False)
ax.grid(axis='y', alpha=0.14)
ax.set_axisbelow(True)

save_figure(fig, 'prescriptive_trial_prices')


# ==================== S2: Plot price constraints ====================

fig, ax = plt.subplots(figsize=(11, 5))

for i, row in selected.iterrows():
    ax.plot(
        [row['matched_p25'], row['matched_p75']],
        [i, i],
        color=GRAY,
        linewidth=8,
        solid_capstyle='round'
    )

ax.scatter(
    selected['model'],
    positions,
    color=GOLD,
    marker='D',
    s=65,
    label='Model Reference Price',
    zorder=3
)

ax.scatter(
    selected['launch'],
    positions,
    color=TEAL,
    s=70,
    label='Selected Trial Price',
    zorder=4
)

# Add an empty line to identify the peer range in the legend.
ax.plot(
    [],
    [],
    color=GRAY,
    linewidth=8,
    label='Peer Interquartile Range'
)

ax.set_yticks(positions, labels)
ax.invert_yaxis()
ax.set_xlabel('Advertised Nightly Price (AUD)')

ax.set_title(
    'Trial Prices within Comparable Price Constraints',
    loc='left',
    fontweight='bold'
)

ax.legend(
    frameon=False,
    loc='upper center',
    bbox_to_anchor=(0.5, -0.2),
    ncol=3
)

save_figure(fig, 'prescriptive_price_constraints')


# ==================== S3: Test sensitivity to the activity threshold ====================

sensitivity_rows = []

for ratio in [0.75, 0.90, 1.00, 1.10]:
    candidates = city_one.loc[
        city_one['sample_ok']
        & city_one['reviews'].ge(reference * ratio)
    ].sort_values(
        ['median', 'reviews'],
        ascending=False
    )

    sensitivity_rows.append({
        'Activity_Requirement_Ratio': ratio,
        'Annual_Review_Threshold': reference * ratio,
        'Eligible_Areas': len(candidates),
        'Selected_Area': (
            candidates.iloc[0]['area']
            if not candidates.empty
            else 'No Eligible Candidate'
        )
    })

sensitivity = pd.DataFrame(sensitivity_rows)

save_table(
    sensitivity.round(3),
    'prescriptive_sensitivity'
)


# ==================== S3: Plot sensitivity results ====================

fig, ax = plt.subplots(figsize=(10, 5))

bars = ax.bar(
    sensitivity['Activity_Requirement_Ratio'].map(
        lambda value: f'{value:.0%}'
    ),
    sensitivity['Eligible_Areas'],
    color=TEAL
)

ax.set_xlabel('Required Activity Relative to Melbourne')
ax.set_ylabel('Number of Eligible Areas')
ax.set_title(
    'Candidate Eligibility under Different Activity Requirements',
    loc='left',
    fontweight='bold'
)

ax.set_ylim(
    0,
    max(1, sensitivity['Eligible_Areas'].max()) + 1.5
)

for bar, row in zip(
    bars,
    sensitivity.itertuples(index=False)
):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.08,
        row.Selected_Area,
        ha='center',
        va='bottom',
        fontsize=9
    )

ax.yaxis.set_major_locator(
    plt.MaxNLocator(integer=True)
)

save_figure(fig, 'prescriptive_activity_sensitivity')


# ==================== Define lower and higher price tests ====================

def round_to_price_step(value):
    return int(
        np.floor(value / PRICE_STEP + 0.5)
        * PRICE_STEP
    )


price_tests = pd.DataFrame({
    'Plan': selected['plan'],
    'Area': selected['area'],
    'Lower_Test_Price_AUD': selected['launch'].map(
        lambda value: round_to_price_step(value * 0.90)
    ),
    'Starting_Price_AUD': selected['launch'],
    'Higher_Test_Price_AUD': selected['launch'].map(
        lambda value: round_to_price_step(value * 1.10)
    )
})

save_table(
    price_tests,
    'prescriptive_price_test_scenarios'
)


# ==================== Save decision settings ====================

decision_settings = {
    'minimum_comparable_listings': MIN_PEERS,
    'minimum_history_listings': MIN_HISTORY,
    'minimum_two_night_comparables': MIN_TWO_NIGHT_PEERS,
    'activity_floor_ratio': ACTIVITY_FLOOR,
    'price_step_aud': PRICE_STEP,
    'minimum_stay_nights': 2,
    'price_objective': (
        'Choose the allowed price closest to the model reference '
        'within the two-night peer interquartile range.'
    ),
    'selection_rules': {
        'A': (
            'Highest median advertised price among eligible '
            'one-bedroom city candidates.'
        ),
        'B': (
            'Highest median annual review activity among '
            'sample-qualified two-bedroom city candidates.'
        ),
        'C': (
            'Conditional quote for an existing Yarra Ranges '
            'one-bedroom retreat property.'
        )
    }
}

with open(
    CHARTS / 'prescriptive_decision_settings.json',
    'w',
    encoding='utf-8'
) as file:
    json.dump(
        decision_settings,
        file,
        indent=2,
        ensure_ascii=False
    )


# ==================== Verify decision constraints ====================

assert selected['matched_n'].ge(
    MIN_TWO_NIGHT_PEERS
).all()

assert selected['launch'].ge(
    selected['matched_p25']
).all()

assert selected['launch'].le(
    selected['matched_p75']
).all()

assert selected['launch'].mod(
    PRICE_STEP
).eq(0).all()

assert selected['minimum_stay'].eq(2).all()

print('\nDecision constraint checks passed.')


# ==================== Report output locations ====================

print('\nPrescriptive analysis completed.')
print(f'Figures: {FIGURES.resolve()}')
print(f'Tables: {CHARTS.resolve()}')
print(f'Model folder: {MODELS.resolve()}')
print('No new predictive model was trained.')

print(
    '\nInterpretation: trial prices are constrained starting points, '
    'not profit-maximizing prices. The peer interquartile range '
    'is not a prediction confidence interval. Lower and higher '
    'price tests are proposed experimental settings.'
)
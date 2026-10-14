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

pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 160)


# ==================== Set chart colors and styles ====================

NAVY = '#183C4A'
TEAL = '#168A85'
GOLD = '#D58A39'
BLUE = '#5386AF'
GRAY = '#C9D2D5'
MUTED = '#617580'

AREAS = [
    'Melbourne',
    'Yarra',
    'Port Phillip',
    'Stonnington',
    'Yarra Ranges'
]

PROPERTY_COLORS = {
    'Apartment': TEAL,
    'House / townhouse': BLUE,
    'Cottage / guesthouse': GOLD,
    'Other': GRAY
}

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.unicode_minus': False,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.edgecolor': '#C5D1D4',
    'axes.labelcolor': MUTED,
    'xtick.color': MUTED,
    'ytick.color': NAVY,
    'text.color': NAVY,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'savefig.facecolor': 'white'
})


# ==================== Define helper functions ====================

def locate(stem):
    """Find an input file in common project folders."""
    folders = [
        Path('.'),
        Path('data'),
        Path('upload'),
        Path('../upload'),
        Path('/content')
    ]

    names = [
        f'{stem} (1).csv.gz',
        f'{stem}.csv.gz',
        f'{stem}.csv'
    ]

    for folder in folders:
        for name in names:
            candidate = folder / name

            if candidate.is_file():
                return candidate

    raise FileNotFoundError(
        f'Cannot find {stem}. Place {stem} (1).csv.gz '
        f'or {stem}.csv in the project folder or data folder.'
    )


def require_columns(frame, columns, dataset_name):
    """Check that an input dataset has the required columns."""
    missing = [
        column
        for column in columns
        if column not in frame.columns
    ]

    if missing:
        raise ValueError(
            f'{dataset_name} is missing required columns: {missing}'
        )


def save_figure(fig, name):
    """Save and display a figure."""
    fig.tight_layout()

    fig.savefig(
        FIGURES / f'{name}.png',
        dpi=165,
        bbox_inches='tight'
    )

    plt.show()
    plt.close(fig)


def save_table(frame, name):
    """Save and print a table."""
    frame.to_csv(
        CHARTS / f'{name}.csv',
        index=False,
        encoding='utf-8-sig'
    )

    print(f'\n{name}')
    print(frame.to_string(index=False))

    return frame


def horizontal_chart(labels, values, title, xlabel, name,
                     colors=None, percent=False):
    """Create a horizontal bar chart."""
    labels = list(labels)
    values = np.asarray(values, dtype=float)

    if len(values) == 0:
        print(f'Skipped empty chart: {name}')
        return

    fig, ax = plt.subplots(figsize=(10, 4.8))

    bars = ax.barh(
        labels,
        values,
        color=colors if colors is not None else TEAL,
        height=0.58
    )

    ax.invert_yaxis()
    ax.set_title(title, loc='left', fontweight='bold', pad=16)
    ax.set_xlabel(xlabel)
    ax.grid(axis='x', alpha=0.14)
    ax.set_axisbelow(True)
    ax.tick_params(axis='y', length=0)

    finite_values = values[np.isfinite(values)]
    maximum = finite_values.max() if len(finite_values) else 0
    scale = maximum if maximum > 0 else 1

    ax.set_xlim(0, scale * 1.25)

    for bar, value in zip(bars, values):
        if not np.isfinite(value):
            continue

        label = f'{value:.1f}%' if percent else f'{value:,.1f}'

        ax.text(
            value + scale * 0.025,
            bar.get_y() + bar.get_height() / 2,
            label,
            va='center',
            fontweight='bold'
        )

    save_figure(fig, name)


def parse_amenities(value):
    """Convert an amenities JSON list into searchable text."""
    if not isinstance(value, str):
        return ''

    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value.lower()

    if isinstance(parsed, list):
        return ' | '.join(str(item) for item in parsed).lower()

    return str(parsed).lower()


# ==================== Load input files ====================

listing_path = locate('listings')
review_path = locate('reviews')
calendar_path = locate('calendar')

raw = pd.read_csv(listing_path, low_memory=False)

require_columns(
    raw,
    [
        'id',
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
        'amenities',
        'first_review',
        'latitude',
        'longitude'
    ],
    'Listings'
)

review_header = pd.read_csv(review_path, nrows=0)
calendar_header = pd.read_csv(calendar_path, nrows=0)

require_columns(
    review_header,
    ['listing_id', 'date', 'comments'],
    'Reviews'
)

require_columns(
    calendar_header,
    [
        'listing_id',
        'date',
        'available',
        'minimum_nights',
        'maximum_nights'
    ],
    'Calendar'
)

print(f'Listings file: {listing_path}')
print(f'Reviews file: {review_path}')
print(f'Calendar file: {calendar_path}')


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

for column in [
    'bedrooms',
    'accommodates',
    'minimum_nights',
    'latitude',
    'longitude'
]:
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

amenity_text = l['amenities'].map(parse_amenities)

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

amenity_columns = list(amenity_patterns)

for feature, pattern in amenity_patterns.items():
    l[feature] = (
        amenity_text.str.contains(
            pattern,
            regex=True,
            na=False
        )
        .astype(int)
    )


# ==================== Process reviews in a fixed annual window ====================

REVIEW_END = pd.Timestamp('2026-06-16')
REVIEW_START = REVIEW_END - pd.Timedelta(days=364)

theme_patterns = {
    'Walking / transport': (
        r'\b(?:walk(?:ing|able)?|tram|train|transport|'
        r'station|central|cbd)\b'
    ),
    'Quiet / nature': (
        r'\b(?:peaceful|relax(?:ing|ation)?|quiet|tranquil|'
        r'nature|forest|retreat|wildlife|birds?|garden)\b'
    ),
    'Family / children': (
        r'\b(?:family|families|kids|children|child|toddler)\b'
    ),
    'Couples / celebrations': (
        r'\b(?:couple|partner|husband|wife|romantic|anniversary)\b'
    ),
    'Work / business': (
        r'\b(?:work|business|conference|office)\b'
    )
}

theme_columns = list(theme_patterns)

review_parts = []
monthly_parts = []

for chunk in pd.read_csv(
    review_path,
    usecols=['listing_id', 'date', 'comments'],
    chunksize=100000
):
    dates = pd.to_datetime(chunk['date'], errors='coerce')

    mask = dates.between(REVIEW_START, REVIEW_END)
    r = chunk.loc[mask].copy()

    if r.empty:
        continue

    r['month'] = (
        dates.loc[mask]
        .dt.to_period('M')
        .astype(str)
    )

    r['text_n'] = r['comments'].notna().astype(int)
    comments = r['comments'].astype('string')

    for theme, pattern in theme_patterns.items():
        r[theme] = (
            comments.str.contains(
                pattern,
                case=False,
                regex=True,
                na=False
            )
            .astype(int)
        )

    aggregation = {
        'recent_reviews': ('date', 'size'),
        'text_n': ('text_n', 'sum')
    }

    aggregation.update({
        theme: (theme, 'sum')
        for theme in theme_columns
    })

    review_parts.append(
        r.groupby('listing_id').agg(**aggregation)
    )

    monthly_parts.append(
        r.groupby(['listing_id', 'month'])
        .size()
        .rename('reviews')
    )

if not review_parts:
    raise ValueError(
        'No reviews were found in the original annual review window.'
    )

rv = (
    pd.concat(review_parts)
    .groupby(level=0)
    .sum()
)

rvm = (
    pd.concat(monthly_parts)
    .groupby(level=[0, 1])
    .sum()
)

l = l.merge(
    rv,
    left_on='id',
    right_index=True,
    how='left',
    validate='one_to_one'
)

for column in ['recent_reviews', 'text_n'] + theme_columns:
    l[column] = l[column].fillna(0)

l['mature'] = pd.to_datetime(
    l['first_review'],
    errors='coerce'
).le(REVIEW_START)

l['has_review'] = l['recent_reviews'].gt(0)

print(
    f'Review window: {REVIEW_START.date()} '
    f'to {REVIEW_END.date()}'
)


# ==================== Define market and comparison samples ====================

c = l.loc[l['source'].eq('city scrape')].copy()

if c.empty:
    raise ValueError(
        'No city-scrape records were found. '
        'Check that the input file matches the original notebook.'
    )

e = c.loc[c['room_type'].eq('Entire home/apt')].copy()

q = e.loc[
    e['price_aud'].between(20, 2000)
    & e['bedrooms'].between(1, 3)
    & e['accommodates'].between(1, 8)
    & e['minimum_nights'].between(1, 7)
    & e['quote_nights'].between(1, 7)
    & e['quote_lead'].between(0, 30)
].copy()

if e.empty or q.empty:
    raise ValueError(
        'The entire-home or short-stay comparison sample is empty.'
    )

save_table(
    pd.DataFrame({
        'Sample': [
            'Unique listings',
            'Current city scrape',
            'Entire-home market',
            'Short-stay comparison sample'
        ],
        'Listing Count': [len(l), len(c), len(e), len(q)]
    }),
    '00_sample_overview'
)


# ==================== D1: Compare listing supply by area ====================

supply = (
    e.groupby('area')
    .size()
    .sort_values(ascending=False)
    .rename('Entire_Home_Listings')
)

save_table(
    supply.rename_axis('Area').reset_index(),
    '01_listing_supply'
)

horizontal_chart(
    supply.head(8).index,
    supply.head(8).values,
    'Where Are Entire-Home Listings Concentrated?',
    'Number of Entire-Home Listings',
    '01_listing_supply'
)


# ==================== D1: Plot the geographic distribution ====================

fig, ax = plt.subplots(figsize=(10, 7))

for property_group, color in PROPERTY_COLORS.items():
    points = e.loc[
        e['property_group'].eq(property_group)
    ].dropna(subset=['latitude', 'longitude'])

    ax.scatter(
        points['longitude'],
        points['latitude'],
        s=5,
        alpha=0.35,
        color=color,
        label=property_group,
        linewidths=0
    )

ax.set_title(
    'Geographic Distribution of Entire-Home Listings',
    loc='left',
    fontweight='bold'
)

ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')

mean_latitude = e['latitude'].mean()

if pd.notna(mean_latitude):
    ax.set_aspect(
        1 / np.cos(np.deg2rad(mean_latitude))
    )

ax.legend(frameon=False, markerscale=3)

save_figure(fig, '02_listing_distribution')


# ==================== D1: Compare property types by area ====================

property_mix = pd.crosstab(
    e['area'],
    e['property_group'],
    normalize='index'
).reindex(
    columns=list(PROPERTY_COLORS),
    fill_value=0
).mul(100)

save_table(
    property_mix.round(2).rename_axis('Area').reset_index(),
    '02_property_mix_percent'
)

mix_areas = [
    area
    for area in ['Melbourne', 'Yarra', 'Port Phillip', 'Yarra Ranges']
    if area in property_mix.index
]

mix_view = property_mix.loc[mix_areas]

fig, ax = plt.subplots(figsize=(10, 5))
left = np.zeros(len(mix_view))

for property_group, color in PROPERTY_COLORS.items():
    values = mix_view[property_group].to_numpy()

    bars = ax.barh(
        mix_view.index,
        values,
        left=left,
        label=property_group,
        color=color,
        height=0.55
    )

    for bar, value, offset in zip(bars, values, left):
        if value >= 12:
            ax.text(
                offset + value / 2,
                bar.get_y() + bar.get_height() / 2,
                f'{value:.0f}%',
                ha='center',
                va='center',
                color='white',
                fontweight='bold'
            )

    left += values

ax.invert_yaxis()
ax.set_xlim(0, 100)
ax.set_xlabel('Share of Local Entire-Home Listings (%)')

ax.set_title(
    'Property Types Differ Across Areas',
    loc='left',
    fontweight='bold'
)

ax.legend(
    frameon=False,
    ncol=2,
    loc='upper center',
    bbox_to_anchor=(0.5, -0.18)
)

save_figure(fig, '03_property_mix')


# ==================== D2: Define comparable property groups ====================

urban_supply = (
    e.loc[e['property_group'].eq('Apartment')]
    .groupby('area')
    .size()
    .nlargest(4)
)

urban_areas = list(urban_supply.index)

save_table(
    urban_supply
    .rename('Apartment_Listings')
    .rename_axis('Area')
    .reset_index(),
    '03_urban_candidate_supply'
)

peer_rows = []

comparison_areas = [
    'Melbourne',
    'Yarra',
    'Port Phillip',
    'Stonnington',
    'Moreland',
    'Yarra Ranges'
]

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

        historical = peers.loc[peers['mature']]

        peer_rows.append({
            'area': area,
            'bedrooms': bedrooms,
            'property_group': property_group,
            'n': len(peers),
            'mature_n': len(historical),
            'median': peers['price_aud'].median(),
            'p25': peers['price_aud'].quantile(0.25),
            'p75': peers['price_aud'].quantile(0.75),
            'reviews': historical['recent_reviews'].median(),
            'active': historical['has_review'].mean()
        })

sc = pd.DataFrame(peer_rows)

if sc.empty:
    raise ValueError(
        'No comparable property groups contain at least 20 listings.'
    )

save_table(
    sc.round(3),
    '04_comparable_property_groups'
)


# ==================== D2: Compare one-bedroom apartment prices ====================

onebed = (
    sc.loc[
        sc['area'].isin(urban_areas)
        & sc['bedrooms'].eq(1)
        & sc['property_group'].eq('Apartment')
    ]
    .sort_values('median', ascending=False)
    .copy()
)

save_table(
    onebed[
        ['area', 'n', 'mature_n', 'median', 'reviews']
    ].rename(columns={
        'area': 'Area',
        'n': 'Comparable_Listings',
        'mature_n': 'Listings_With_One_Year_Review_History',
        'median': 'Median_Nightly_Price_AUD',
        'reviews': 'Median_Annual_Reviews'
    }).round(1),
    '05_one_bedroom_comparison'
)

horizontal_chart(
    onebed['area'],
    onebed['median'],
    'One-Bedroom Apartments: Median Advertised Prices',
    'Median Advertised Nightly Price (AUD)',
    '04_one_bedroom_prices'
)


# ==================== D2: Compare one-bedroom review activity ====================

horizontal_chart(
    onebed['area'],
    onebed['reviews'],
    'One-Bedroom Apartments: Annual Review Activity',
    'Median Annual Reviews per Listing with One Year of Review History',
    '05_one_bedroom_reviews'
)


# ==================== D3: Compare prices and reviews by bedroom count ====================

size_view = sc.loc[
    sc['area'].isin(['Melbourne', 'Yarra'])
    & sc['bedrooms'].isin([1, 2])
    & sc['property_group'].eq('Apartment')
].copy()

save_table(
    size_view[
        ['area', 'bedrooms', 'n', 'mature_n', 'median', 'reviews']
    ].round(1),
    '06_bedroom_price_and_review_comparison'
)

price_pivot = size_view.pivot(
    index='area',
    columns='bedrooms',
    values='median'
).reindex(columns=[1, 2])

if not price_pivot.empty:
    fig, ax = plt.subplots(figsize=(10, 5))
    positions = np.arange(len(price_pivot))
    width = 0.32

    for i, bedrooms in enumerate([1, 2]):
        bars = ax.bar(
            positions + (i - 0.5) * width,
            price_pivot[bedrooms],
            width,
            color=[TEAL, GOLD][i],
            label=f'{bedrooms}-Bedroom Apartment'
        )

        ax.bar_label(
            bars,
            fmt='%.0f',
            padding=4,
            fontweight='bold'
        )

    ax.set_xticks(positions, price_pivot.index)
    ax.set_ylabel('Median Advertised Nightly Price (AUD)')

    ax.set_title(
        'Apartment Prices by Bedroom Count',
        loc='left',
        fontweight='bold'
    )

    ax.margins(y=0.18)
    ax.legend(frameon=False)
    ax.grid(axis='y', alpha=0.14)
    ax.set_axisbelow(True)

    save_figure(fig, '06_prices_by_bedroom_count')


# ==================== D3: Calculate illustrative prices per person ====================

per_person = sc.loc[
    sc['area'].eq('Melbourne')
    & sc['property_group'].eq('Apartment')
    & sc['bedrooms'].isin([1, 2, 3])
].sort_values('bedrooms').copy()

# Assume two guests per bedroom for this illustrative comparison.
# This is not observed occupancy or actual revenue per guest.
per_person['Assumed_Guests'] = (
    per_person['bedrooms'] * 2
).astype(int)

per_person['Price_Per_Person_AUD'] = (
    per_person['median'] / per_person['Assumed_Guests']
)

save_table(
    per_person[
        [
            'area',
            'bedrooms',
            'median',
            'Assumed_Guests',
            'Price_Per_Person_AUD'
        ]
    ].round(2),
    '07_illustrative_price_per_person'
)

labels = [
    f'{int(row.bedrooms)} bedrooms / {row.Assumed_Guests} guests'
    for row in per_person.itertuples()
]

horizontal_chart(
    labels,
    per_person['Price_Per_Person_AUD'],
    'Melbourne Apartments: Illustrative Price per Person',
    'Median Advertised Price / Assumed Guests (AUD per Person per Night)',
    '07_price_per_person'
)


# ==================== D4: Summarize review themes ====================

theme_denominators = e.groupby('area')['text_n'].sum()

theme_percent = (
    e.groupby('area')[theme_columns]
    .sum()
    .div(theme_denominators.replace(0, np.nan), axis=0)
    .mul(100)
)

save_table(
    theme_percent.round(2).rename_axis('Area').reset_index(),
    '08_review_theme_percent'
)

save_table(
    theme_denominators
    .rename('Non_Missing_Review_Texts')
    .rename_axis('Area')
    .reset_index(),
    '09_review_theme_denominators'
)

theme_areas = [
    area
    for area in ['Melbourne', 'Yarra Ranges']
    if area in theme_percent.index
]

selected_themes = ['Walking / transport', 'Quiet / nature']

if theme_areas:
    fig, ax = plt.subplots(figsize=(10, 5))
    positions = np.arange(len(selected_themes))
    width = 0.32

    for i, area in enumerate(theme_areas):
        values = theme_percent.loc[area, selected_themes]

        bars = ax.bar(
            positions + (i - (len(theme_areas) - 1) / 2) * width,
            values,
            width,
            color=[TEAL, GOLD][i],
            label=area
        )

        ax.bar_label(bars, fmt='%.1f%%', padding=4)

    ax.set_xticks(positions, selected_themes)
    ax.set_ylabel('Share of Local Non-Missing Review Texts (%)')

    ax.set_title(
        'Review Themes Differ Across Areas',
        loc='left',
        fontweight='bold'
    )

    ax.margins(y=0.2)
    ax.legend(frameon=False)
    ax.grid(axis='y', alpha=0.14)
    ax.set_axisbelow(True)

    save_figure(fig, '08_review_themes')

family_areas = [
    area for area in AREAS
    if area in theme_percent.index
]

horizontal_chart(
    family_areas,
    theme_percent.loc[family_areas, 'Family / children'],
    'Mentions of Family and Children in Reviews',
    'Share of Local Non-Missing Review Texts (%)',
    '09_family_mentions',
    percent=True
)


# ==================== D4: Compare amenities across areas ====================

amenity_percent = (
    e.groupby('area')[amenity_columns]
    .mean()
    .mul(100)
)

save_table(
    amenity_percent.round(2).rename_axis('Area').reset_index(),
    '10_amenity_percent'
)

pool_areas = [
    area
    for area in ['Melbourne', 'Yarra', 'Port Phillip', 'Yarra Ranges']
    if area in amenity_percent.index
]

horizontal_chart(
    pool_areas,
    amenity_percent.loc[pool_areas, 'Pool'],
    'Pool Availability Across Areas',
    'Share of Entire-Home Listings Mentioning a Pool (%)',
    '10_pool_availability',
    percent=True
)

retreat_amenities = ['Fireplace', 'Free parking', 'Garden']

retreat_areas = [
    area
    for area in ['Melbourne', 'Yarra Ranges']
    if area in amenity_percent.index
]

if retreat_areas:
    fig, ax = plt.subplots(figsize=(10, 5))
    positions = np.arange(len(retreat_amenities))
    width = 0.32

    for i, area in enumerate(retreat_areas):
        values = amenity_percent.loc[area, retreat_amenities]

        bars = ax.bar(
            positions + (i - (len(retreat_areas) - 1) / 2) * width,
            values,
            width,
            color=[TEAL, GOLD][i],
            label=area
        )

        ax.bar_label(bars, fmt='%.0f%%', padding=4)

    ax.set_xticks(positions, retreat_amenities)
    ax.set_ylim(0, 115)
    ax.set_ylabel('Share of Local Entire-Home Listings (%)')

    ax.set_title(
        'Amenities Associated with Retreat-Style Properties',
        loc='left',
        fontweight='bold'
    )

    ax.legend(frameon=False)
    ax.grid(axis='y', alpha=0.14)
    ax.set_axisbelow(True)

    save_figure(fig, '11_retreat_amenities')


# ==================== D5: Process calendar rules ====================

CALENDAR_START = pd.Timestamp('2026-06-17')
CALENDAR_END = CALENDAR_START + pd.Timedelta(days=89)

region = l.set_index('id')['area'].to_dict()
valid_ids = set(e['id'])

calendar_parts = []

for chunk in pd.read_csv(
    calendar_path,
    usecols=[
        'listing_id',
        'date',
        'available',
        'minimum_nights',
        'maximum_nights'
    ],
    chunksize=250000
):
    dates = pd.to_datetime(chunk['date'], errors='coerce')

    mask = (
        chunk['listing_id'].isin(valid_ids)
        & dates.between(CALENDAR_START, CALENDAR_END)
    )

    z = chunk.loc[mask].copy()

    if z.empty:
        continue

    minimum_nights = pd.to_numeric(
        z['minimum_nights'],
        errors='coerce'
    )

    maximum_nights = pd.to_numeric(
        z['maximum_nights'],
        errors='coerce'
    )

    available = (
        z['available']
        .astype('string')
        .str.lower()
        .isin(['t', 'true', '1'])
    )

    z['is_available'] = available.astype(int)

    # Check the rule for a single available listing-date.
    # This does not establish that two consecutive nights are available.
    z['accept_2'] = (
        available
        & minimum_nights.le(2)
        & maximum_nights.ge(2)
    ).astype(int)

    z['area'] = z['listing_id'].map(region)

    calendar_parts.append(
        z.groupby('area').agg(
            days=('date', 'size'),
            available=('is_available', 'sum'),
            accept_2=('accept_2', 'sum')
        )
    )

if not calendar_parts:
    raise ValueError(
        'No calendar records match the original calendar window.'
    )

cal = (
    pd.concat(calendar_parts)
    .groupby(level=0)
    .sum()
)

cal['accept_2_share'] = (
    cal['accept_2']
    / cal['available'].replace(0, np.nan)
)

cal['open_share'] = (
    cal['available']
    / cal['days'].replace(0, np.nan)
)

save_table(
    cal.round(4).rename_axis('Area').reset_index(),
    '11_calendar_summary'
)

calendar_areas = [
    area for area in AREAS
    if area in cal.index
]

horizontal_chart(
    calendar_areas,
    cal.loc[calendar_areas, 'accept_2_share'] * 100,
    'Available Dates with Rules Allowing a Two-Night Stay',
    'Share of Available Listing-Dates (%)',
    '12_two_night_rules',
    percent=True
)

print(
    f'Calendar window: {CALENDAR_START.date()} '
    f'to {CALENDAR_END.date()}'
)


# ==================== D5: Compare monthly review activity ====================

# Use a fixed cohort with at least one year of review history.
cohort = q.loc[
    q['mature']
    & q['area'].isin(['Melbourne', 'Yarra', 'Yarra Ranges'])
].copy()

if not cohort.empty:
    monthly_data = rvm.reset_index()
    monthly_data.columns = ['id', 'month', 'reviews']

    monthly_data = monthly_data.merge(
        cohort[['id', 'area']],
        on='id',
        how='inner',
        validate='many_to_one'
    )

    # Exclude the partial months at the review-window boundaries.
    months = pd.period_range(
        '2025-07',
        '2026-05',
        freq='M'
    ).astype(str)

    cohort_counts = cohort.groupby('area').size()

    monthly_table = (
        monthly_data.groupby(['month', 'area'])['reviews']
        .sum()
        .unstack()
        .reindex(
            index=months,
            columns=cohort_counts.index
        )
        .fillna(0)
    )

    monthly_table = (
        monthly_table
        .div(cohort_counts, axis=1)
        .mul(100)
    )

    save_table(
        monthly_table.round(2)
        .rename_axis('Month')
        .reset_index(),
        '12_monthly_reviews_per_100_listings'
    )

    save_table(
        cohort_counts
        .rename('Fixed_Cohort_Listings')
        .rename_axis('Area')
        .reset_index(),
        '13_monthly_review_cohort'
    )

    fig, ax = plt.subplots(figsize=(10, 5))

    area_colors = {
        'Melbourne': TEAL,
        'Yarra': BLUE,
        'Yarra Ranges': GOLD
    }

    for area in monthly_table.columns:
        ax.plot(
            np.arange(len(monthly_table)),
            monthly_table[area],
            color=area_colors.get(area, GRAY),
            label=area,
            marker='o',
            markersize=4,
            linewidth=2
        )

    ax.set_xticks(
        np.arange(len(monthly_table)),
        monthly_table.index,
        rotation=45,
        ha='right'
    )

    ax.set_ylabel('New Reviews per 100 Fixed-Cohort Listings')

    ax.set_title(
        'Monthly Review Activity',
        loc='left',
        fontweight='bold'
    )

    ax.legend(frameon=False)
    ax.grid(axis='y', alpha=0.14)
    ax.set_axisbelow(True)

    save_figure(fig, '13_monthly_review_activity')

else:
    print(
        'Monthly review chart skipped: '
        'no listings meet the fixed-cohort criteria.'
    )


# ==================== Report output locations ====================

print('\nDescriptive analysis completed.')
print(f'Figures: {FIGURES.resolve()}')
print(f'Tables: {CHARTS.resolve()}')
print(f'Model folder: {MODELS.resolve()}')
print('No predictive model was trained in this section.')

print(
    '\nInterpretation notes: '
    'review counts are activity indicators, not booking counts; '
    'keyword mentions do not measure sentiment; '
    'unavailable calendar dates do not necessarily mean booked dates.'
)
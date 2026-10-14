# ==================== Install missing packages ====================

import importlib.util
import subprocess
import sys

packages = {
    'pandas': 'pandas',
    'numpy': 'numpy',
    'matplotlib': 'matplotlib',
    'IPython': 'ipython'
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

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from IPython.display import display


# ==================== Set output folders ====================

OUT = Path('analysis_outputs_v3')
F = OUT / 'figures'
T = OUT / 'tables'

for folder in [OUT, F, T]:
    folder.mkdir(parents=True, exist_ok=True)

pd.set_option('display.max_columns', 18)
pd.set_option('display.max_rows', 30)


# ==================== Define chart colors and styles ====================

NAVY = '#183C4A'
TEAL = '#168A85'
GOLD = '#D58A39'
MUTED = '#617580'

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 11,
    'axes.unicode_minus': False,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.spines.left': False,
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

def locate_listings():
    """Find the listings file in common project folders."""
    folders = [
        Path('.'),
        Path('data'),
        Path('../upload'),
        Path('upload'),
        Path('/content')
    ]

    filenames = [
        'listings (1).csv.gz',
        'listings.csv.gz',
        'listings.csv'
    ]

    for folder in folders:
        for filename in filenames:
            candidate = folder / filename

            if candidate.is_file():
                return candidate

    raise FileNotFoundError(
        'Listings file not found. Place listings (1).csv.gz, '
        'listings.csv.gz, or listings.csv in the notebook folder '
        'or the data folder.'
    )


def done(fig, name):
    """Save and display a chart."""
    fig.savefig(
        F / f'{name}.png',
        dpi=165,
        bbox_inches='tight'
    )
    plt.show()
    plt.close(fig)


def horizontal(labels, values, title, unit='', fmt=None):
    """Create a horizontal bar chart with value labels."""
    values = np.asarray(values, dtype=float)

    fig, ax = plt.subplots(figsize=(9.2, 4.3))

    bars = ax.barh(
        list(labels),
        values,
        color=TEAL,
        height=0.58
    )

    ax.invert_yaxis()
    ax.set_title(
        title,
        loc='left',
        fontweight='bold',
        pad=18
    )
    ax.set_xlabel(unit)
    ax.grid(axis='x', alpha=0.14)
    ax.set_axisbelow(True)
    ax.tick_params(axis='y', length=0, pad=10)

    maximum = float(values.max()) if len(values) else 0
    scale = maximum if maximum > 0 else 1

    ax.set_xlim(0, scale * 1.24)

    for bar, value in zip(bars, values):
        label = fmt(value) if fmt else f'{value:,.0f}'

        ax.text(
            value + scale * 0.025,
            bar.get_y() + bar.get_height() / 2,
            label,
            va='center',
            fontweight='bold',
            fontsize=11
        )

    fig.tight_layout()
    return fig


# ==================== Load the listings dataset ====================

listing_path = locate_listings()
raw = pd.read_csv(listing_path, low_memory=False)

required_columns = [
    'id',
    'last_scraped',
    'price',
    'bedrooms',
    'accommodates',
    'minimum_nights',
    'latitude',
    'longitude',
    'neighbourhood_cleansed',
    'bathrooms_text',
    'price_quote_checkin_date',
    'price_quote_checkout_date',
    'source',
    'room_type'
]

missing_columns = [
    column
    for column in required_columns
    if column not in raw.columns
]

if missing_columns:
    raise ValueError(
        'The listings file is missing columns required by the '
        f'original notebook: {missing_columns}'
    )

print(f'Loaded file: {listing_path}')
print(f'Original listings: {len(raw):,}')
print(f'Original variables: {raw.shape[1]:,}')


# ==================== Prepare variables for EDA ====================

# Remove missing listing IDs.
l = raw.dropna(subset=['id']).copy()

# Keep the latest record if a listing ID appears more than once.
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

# Convert price strings to numeric AUD values.
l['price_aud'] = pd.to_numeric(
    l['price']
    .astype('string')
    .str.replace(r'[$,]', '', regex=True),
    errors='coerce'
)

numeric_columns = [
    'bedrooms',
    'accommodates',
    'minimum_nights',
    'latitude',
    'longitude'
]

for column in numeric_columns:
    l[column] = pd.to_numeric(l[column], errors='coerce')

l['area'] = l['neighbourhood_cleansed']

# Extract the number of bathrooms from the bathroom description.
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

# Calculate the stay length and booking lead time of each price quote.
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

if l.empty:
    raise ValueError('No listings remain after checking listing IDs.')


# ==================== Define the analysis samples ====================

# Use listings collected in the current city scrape.
c = l.loc[l['source'].eq('city scrape')].copy()

if c.empty:
    raise ValueError(
        'No records have source = "city scrape". '
        'Check whether you are using the same dataset as the notebook.'
    )

# Use entire-home listings for the price distribution.
e = c.loc[c['room_type'].eq('Entire home/apt')].copy()

if e.empty:
    raise ValueError('No entire-home listings were found.')

# Apply the original notebook's mainstream short-stay criteria.
q = e.loc[
    e['price_aud'].between(20, 2000)
    & e['bedrooms'].between(1, 3)
    & e['accommodates'].between(1, 8)
    & e['minimum_nights'].between(1, 7)
    & e['quote_nights'].between(1, 7)
    & e['quote_lead'].between(0, 30)
].copy()

if q.empty:
    raise ValueError(
        'No listings meet the short-stay comparison criteria. '
        'Check the price, quote dates, and stay-length variables.'
    )

sample_overview = pd.DataFrame({
    'Sample': [
        'Unique listings',
        'Current city scrape',
        'Entire-home listings',
        'Mainstream short-stay comparison sample'
    ],
    'Listing Count': [
        len(l),
        len(c),
        len(e),
        len(q)
    ]
})

display(sample_overview)


# ==================== Check missing values ====================

missing_cols = {
    'price_aud': 'Nightly price',
    'bedrooms': 'Number of bedrooms',
    'bath_num': 'Number of bathrooms',
    'area': 'Area',
    'latitude': 'Latitude',
    'longitude': 'Longitude'
}

missing = (
    l[list(missing_cols)]
    .isna()
    .mean()
    .mul(100)
    .rename(index=missing_cols)
    .sort_values(ascending=False)
)

missing_table = pd.DataFrame({
    'Variable': missing.index,
    'Missing Percentage (%)': missing.values.round(2)
})

display(missing_table)

fig = horizontal(
    missing.index,
    missing.values,
    'Missing Values in Key Variables',
    'Percentage of All Listings (%)',
    fmt=lambda value: f'{value:.1f}%'
)

done(fig, 'eda_missingness')


# ==================== Summarize nightly prices ====================

prices = e.loc[e['price_aud'].gt(0), 'price_aud']

if prices.empty:
    raise ValueError(
        'No positive nightly prices are available for analysis.'
    )

summary_stats = (
    prices
    .describe(percentiles=[.25, .5, .75, .95, .99])
    .rename('Advertised Nightly Price (AUD)')
    .round(2)
)

display(summary_stats.to_frame())


# ==================== Visualize the price distribution ====================

# Restrict the histogram to the 99th percentile for readability.
# Summary statistics and the median still use all positive prices.
cap = prices.quantile(.99)

fig, ax = plt.subplots(figsize=(9.2, 4.2))

ax.hist(
    prices[prices.le(cap)],
    bins=42,
    color=TEAL,
    edgecolor='white'
)

ax.axvline(
    prices.median(),
    color=GOLD,
    linewidth=2,
    label=f'Median of All Positive Prices: A${prices.median():.0f}'
)

ax.set_title(
    'Nightly Price Distribution',
    loc='left',
    fontweight='bold'
)

ax.set_xlabel('Advertised Nightly Price (AUD)')
ax.set_ylabel('Number of Listings')
ax.legend(frameon=False)

fig.tight_layout()
done(fig, 'eda_price_distribution')

print(
    f'For readability, the histogram only shows prices up to '
    f'the 99th percentile (A${cap:,.0f}). '
    f'Higher-price records remain in the dataset.'
)


# ==================== Compare listings by bedroom count ====================

bedroom_summary = (
    q.groupby('bedrooms')
    .agg(
        Listing_Count=('id', 'size'),
        Median_Nightly_Price_AUD=('price_aud', 'median'),
        Median_Guest_Capacity=('accommodates', 'median')
    )
    .rename_axis('Bedrooms')
    .round(1)
)

display(bedroom_summary)


# ==================== Save EDA summary tables ====================

sample_overview.to_csv(
    T / 'eda_sample_overview.csv',
    index=False,
    encoding='utf-8-sig'
)

missing_table.to_csv(
    T / 'eda_missingness.csv',
    index=False,
    encoding='utf-8-sig'
)

summary_stats.to_frame().to_csv(
    T / 'eda_price_summary.csv',
    index_label='Statistic',
    encoding='utf-8-sig'
)

bedroom_summary.to_csv(
    T / 'eda_bedroom_summary.csv',
    encoding='utf-8-sig'
)

print(f'Charts saved to: {F.resolve()}')
print(f'Tables saved to: {T.resolve()}')
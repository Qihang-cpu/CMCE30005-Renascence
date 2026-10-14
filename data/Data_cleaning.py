from pathlib import Path
import os, json
os.environ.setdefault('MPLCONFIGDIR', '/tmp/airbnb_mpl_cache')
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display

OUT = Path('analysis_output')
F, T = OUT / 'chart', OUT / 'tables'
for folder in (F, T):
    folder.mkdir(parents=True, exist_ok=True)

def locate(stem):
    for folder in (Path('.'), Path('data'), Path.home() / 'Downloads'):
        for name in (f'{stem} (1).csv.gz', f'{stem}.csv.gz', f'{stem}.csv', f'{stem}_airbnb.csv'):
            path = folder / name
            if path.exists():
                return path
    raise FileNotFoundError(f'Cannot find the {stem} dataset.')

listing_path, review_path = locate('listings'), locate('reviews')
raw = pd.read_csv(listing_path, low_memory=False)
TEAL, GOLD = '#168A85', '#D58A39'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})

def export_table(df, name):
    df.to_csv(T / f'{name}.csv', index=False, encoding='utf-8-sig')

def done(fig, name):
    fig.savefig(F / f'{name}.png', dpi=165, bbox_inches='tight')
    plt.show()
    plt.close(fig)

def horizontal(labels, values, title, unit='', fmt=None):
    fig, ax = plt.subplots(figsize=(10, 4.5))
    bars = ax.barh(labels, values, color=TEAL)
    ax.invert_yaxis()
    ax.set_title(title, loc='left', fontweight='bold')
    ax.set_xlabel(unit)
    maximum = max(values) if max(values) > 0 else 1
    ax.set_xlim(0, maximum * 1.25)
    for bar, value in zip(bars, values):
        ax.text(value + maximum * .02, bar.get_y() + bar.get_height()/2,
                fmt(value) if fmt else str(value), va='center')
    fig.tight_layout()
    return fig


# Preserve raw data; apply transformations to copy l.
missing_id = int(raw.id.isna().sum())
duplicate_id = int(raw.loc[raw.id.notna(),'id'].duplicated().sum())
l = raw.dropna(subset=['id']).copy()
l['_scraped_order'] = pd.to_datetime(l.last_scraped, errors='coerce')
# For duplicate IDs, retain the latest scraped record. This dataset has no duplicates.
l = (l.sort_values('_scraped_order', kind='stable')
      .drop_duplicates('id', keep='last').sort_index().drop(columns='_scraped_order'))

l['price_aud'] = pd.to_numeric(l.price.astype('string').str.replace(r'[$,]','',regex=True), errors='coerce')
for col in ['bedrooms','beds','accommodates','minimum_nights','maximum_nights','latitude','longitude']:
    l[col] = pd.to_numeric(l[col], errors='coerce')
l['area'] = l.neighbourhood_cleansed
checkin = pd.to_datetime(l.price_quote_checkin_date, errors='coerce')
checkout = pd.to_datetime(l.price_quote_checkout_date, errors='coerce')
l['quote_nights'] = (checkout-checkin).dt.days
l['quote_lead'] = (checkin-pd.to_datetime(l.last_scraped, errors='coerce')).dt.days
l['bath_num'] = pd.to_numeric(l.bathrooms_text.str.extract(r'(\d+(?:\.\d+)?)')[0], errors='coerce')
l.loc[l.bathrooms_text.str.contains('half-bath',case=False,na=False),'bath_num'] = .5
l['property_group'] = np.select([
    l.property_type.isin(['Entire rental unit','Entire condo','Entire serviced apartment','Entire loft']),
    l.property_type.isin(['Entire home','Entire townhouse']),
    l.property_type.isin(['Entire cottage','Entire cabin','Entire guesthouse','Entire guest suite','Tiny home','Farm stay'])
], ['Apartment','House/Townhouse','Cottage/Guest accommodation'], default='Other')

amenity_text = l.amenities.map(lambda x:' | '.join(json.loads(x)).lower() if isinstance(x,str) else '')
patterns = {
    'Wifi':r'\bwifi\b', 'Kitchen':r'\bkitchen\b',
    'Free parking':r'\bfree parking on premises\b|\bfree driveway parking\b',
    'Self check-in':r'\bself check-in\b', 'Pool':r'\bpool\b', 'Fireplace':r'\b(?:indoor fireplace|fireplace)\b',
    'Hot tub':r'\bhot tub\b', 'Pets allowed':r'\bpets allowed\b', 'Workspace':r'\bdedicated workspace\b',
    'BBQ':r'\bbbq\b', 'Garden':r'\bbackyard\b|\bgarden\b', 'Air conditioning':r'air conditioning'
}
amen = list(patterns)
for feature,pattern in patterns.items():
    l[feature] = amenity_text.str.contains(pattern,regex=True,na=False).astype(int)

cleaning_log = pd.DataFrame([
    ['Original listings',len(raw),'Preserve original data'],
    ['Missing IDs',missing_id,'Exclude records without a usable ID'],
    ['Duplicate IDs',duplicate_id,'Retain latest record'],
    ['Missing or unparseable prices',int(l.price_aud.isna().sum()),'Retain for supply analysis; exclude from price modelling'],
    ['Non-positive prices',int(l.price_aud.le(0).sum()),'Exclude from valid quotations'],
    ['Unique listings after cleaning',len(l),'One row per listing'],
], columns=['Check','Count','Treatment'])
display(cleaning_log)
export_table(cleaning_log,'cleaning_log')

cutoff=pd.Timestamp('2026-06-16');start=cutoff-pd.Timedelta(days=364)
ids=set(l.id)
parts=[];monthly=[];themes=[];n=0;lo=None;hi=None

theme_patterns={
'Walking/Transport':r'\b(?:walk(?:ing|able)?|tram|train|transport|station|central|cbd)\b',
'Peacefulness/Nature':r'\b(?:peaceful|relax(?:ing|ation)?|quiet|tranquil|nature|forest|retreat|wildlife|birds?|garden)\b',
'Families/Children':r'\b(?:family|families|kids|children|child|toddler)\b',
'Couples/Celebrations':r'\b(?:couple|partner|husband|wife|romantic|anniversary)\b',
'Work/Business':r'\b(?:work|business|conference|office)\b'}

for c in pd.read_csv(review_path,usecols=['listing_id','date','comments'],chunksize=100000):
 n+=len(c);d=pd.to_datetime(c.date)
 lo=d.min() if lo is None else min(lo,d.min());hi=d.max() if hi is None else max(hi,d.max())
 keep=d.between(start,cutoff)
 r=c.loc[keep].copy()
 r['month']=d.loc[keep].dt.to_period('M').astype(str)
 r['text_n']=r.comments.notna().astype(int)
 for k,pat in theme_patterns.items():r[k]=r.comments.str.contains(pat,case=False,regex=True,na=False).astype(int)
 g=r.groupby('listing_id').agg(recent_reviews=('date','size'),text_n=('text_n','sum'),**{k:(k,'sum') for k in theme_patterns})
 parts.append(g)
 monthly.append(r.groupby(['listing_id','month']).size().rename('reviews'))

rv=pd.concat(parts).groupby(level=0).sum()
rvm=pd.concat(monthly).groupby(level=[0,1]).sum()
l=l.merge(rv,left_on='id',right_index=True,how='left',validate='one_to_one')

for k in ['recent_reviews','text_n']+list(theme_patterns):l[k]=l[k].fillna(0)
l['mature']=pd.to_datetime(l.first_review).le(start)
l['has_review']=l.recent_reviews.gt(0)
(OUT/'review_meta.json').write_text(json.dumps({'rows':n,'min':str(lo.date()),'max':str(hi.date()),'start':str(start.date()),'cutoff':str(cutoff.date()),'window_reviews':int(l.recent_reviews.sum())}))


review_meta=json.loads((OUT/'review_meta.json').read_text())
print(f"Total reviews: {review_meta['rows']:,}; common window: {review_meta['start']} to {review_meta['cutoff']}.")
print('Review counts and theme mentions linked by listing; review text is not displayed.')

c = l[l.source.eq('city scrape')].copy()
assert len(c)>0, 'Source coding changed; verify the listing scope.'
assert pd.to_datetime(c.last_scraped).dt.to_period('M').astype(str).eq('2026-06').mean()>.95, 'Check whether an older dataset was loaded.'

e = c[c.room_type.eq('Entire home/apt')].copy()
scope_rows = [['Unique listings after cleaning',len(l)],['Current city scrape',len(c)],['Entire properties',len(e)]]
q = e.copy()

conditions = [
    ('Valid nightly price AUD 20-2,000', lambda x:x.price_aud.between(20,2000)),
    ('1-3 bedrooms, 1-8 guests', lambda x:x.bedrooms.between(1,3)&x.accommodates.between(1,8)),
    ('Minimum stay 1-7 nights', lambda x:x.minimum_nights.between(1,7)),
    ('Quoted stay 1-7 nights', lambda x:x.quote_nights.between(1,7)),
    ('Check-in lead time 0-30 days', lambda x:x.quote_lead.between(0,30)),
]

for label,condition in conditions:
    q = q[condition(q)].copy()
    scope_rows.append([label,len(q)])
quote_date = pd.to_datetime(q.price_quote_checkin_date)
q['quote_weekend'] = quote_date.dt.dayofweek.ge(5).astype(int)
q['quote_month'] = quote_date.dt.month.astype(str)
scope_table = pd.DataFrame(scope_rows,columns=['Sequential filter','Listings retained'])
display(scope_table)
export_table(scope_table,'scope_flow')
print(f'Prepared: supply sample {len(e):,} listings; comparable short-stay/model sample {len(q):,} listings.')

missing_cols = {'price_aud':'Nightly price','bedrooms':'Bedrooms','bath_num':'Parsed bathrooms',
                'area':'Area','latitude':'Latitude','longitude':'Longitude'}
missing = (l[list(missing_cols)].isna().mean()*100).rename(index=missing_cols).sort_values(ascending=False)
fig=horizontal(missing.index,missing.values,'Missing values in key fields','Share of all listings (%)',fmt=lambda v:f'{v:.1f}%')
done(fig,'eda_missingness')
display(pd.DataFrame({'Field':missing.index,'Missing (%)':missing.values.round(2)}))

prices = e.loc[e.price_aud.gt(0),'price_aud']
summary_stats = prices.describe(percentiles=[.25,.5,.75,.95,.99]).rename('Nightly listing price (AUD)').round(2)
display(summary_stats.to_frame())
cap = prices.quantile(.99)
fig,ax=plt.subplots(figsize=(9.2,4.2))
ax.hist(prices[prices.le(cap)],bins=42,color=TEAL,edgecolor='white')
ax.axvline(prices.median(),color=GOLD,linewidth=2,label=f'Median of all positive prices: AUD {prices.median():.0f}')
ax.set_title('Listing prices are right-skewed: compare medians',loc='left',fontweight='bold')
ax.set_xlabel('Nightly listing price (AUD)');ax.set_ylabel('Listing_count');ax.legend(frameon=False)
fig.tight_layout();done(fig,'eda_price_distribution')
print(f'For display only, the histogram ends at the 99th percentile: AUD {cap:,.0f}; higher-price records remain in the original data.')
display(q.groupby('bedrooms').agg(Listing_count=('id','size'),Median_price=('price_aud','median'),Median_capacity=('accommodates','median')).round(1))
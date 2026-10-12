# CMCE30005-Renascence
Our group is group 4

# CMCE30005 Business Analytics Challenge
## Group4-Renascence - AIRBNB

**Subject:** CMCE30005 Business Analytics Challenge, Semester 2 2026
**University:** University of Melbourne
**Team Members:** Qihang Sun, Loc Le

---

## Business Problem

**Status: not decided yet.** 

| | Problem | Outcome variable | Prescriptive output |
|---|---|---|---|
| A | Where and what should the client list? | `estimated_revenue_l365d` | Ranking of LGA x property type by risk-adjusted revenue |
| B | What separates listings that get booked from dormant ones? | `active_ltm` (1+ review in last 12 months) | Listing checklist that raises booking chance |
| C | What drives nightly price, and what should the client charge? | `log_price` | Recommended price range by property and season |

[Replace this section with the final one-paragraph problem statement: stakeholder,
question, why it matters, methods.]

---

## Dataset

**Dataset name:** Airbnb Melbourne - June 2026 Snapshot
**Source:** Inside Airbnb - http://insideairbnb.com/
**Coverage:** All active Airbnb listings in Greater Melbourne (30 LGAs) as of 16 June 2026

### Data Files

| File | Description | Rows | Size |
|------|-------------|------|------|
| `listings_airbnb.csv` | one row per listing (90 variables): property, host, location, price, review scores | 25,728 | ~72 MB |
| `reviews_airbnb.csv` | one row per guest review (Aug 2010 - Jun 2026), incl. free-text comments | 1,026,690 | ~279 MB |
| `calendar_airbnb.csv` | one row per listing per night for the next 365 days: available t/f, min/max nights (no price) | 9,390,720 | ~378 MB |

> **Note:** Data files are not committed to this repository due to size (GitHub limit is 100 MB per file; `*.csv` is in `.gitignore`).
> Download the three files from the subject LMS (or Inside Airbnb, Melbourne, 16 June 2026 snapshot) and put them in the `data/` folder.

---

## How to run

1. Open `CMCE30005-Renascence.Rproj` in RStudio (sets the working directory).
2. Put the three CSV files in `data/`.
3. Run the scripts in this order:

| Order | Script | What it does | Run time |
|---|---|---|---|
| 0 | `scripts/00_packages.R` | Installs missing packages and loads them
| 1 | `data/dataimport.R` | Reads the 3 CSVs with `data.table::fread()` (IDs kept as text)
| 2 | `data/Data Overview for listings.R` | Listings: missing values, types, outliers, first features
| 3 | `data/Data Overview for calendar.R` | Calendar: structure, availability patterns, match with listings
| 4 | `data/Data Overview for reviews.R` | Reviews: structure, demand over time, seasonality, text quality
| 5 | `data/Data cleaning .R` | Cleans all 3 files, builds features, saves `data/processed/*.rds` + `outputs/cleaning_log.txt`
| 6 | `data/EDA process.R` | 13 charts in `outputs/figures/` + `outputs/eda_summary.txt`
| 7 | `Analysis Process/Descriptive Analysis.R` | Skeleton - waiting for business problem
| 8 | `Analysis Process/Predictive Analysis.R` | Skeleton - waiting for business problem
| 9 | `Analysis Process/Prescriptive Analysis.R` | Skeleton - waiting for business problem

---

## Key facts from the data (EDA)

| Topic | Finding |
|---|---|
| Supply | 25,714 clean listings; 18,640 bookable with a price. City of Melbourne = 32.5% of listings |
| Room type | Entire home/apt 73%, private room 26%, shared/hotel ~1% |
| Price | Median entire home $280/night, private room $109/night |
| Demand | Reviews grew from 69k (2019) to 217k (2025) = 3.1x; COVID dip 2020-21 |
| Seasonality | Busiest months Oct, Nov, Dec and Mar; quietest May-Jun |
| Activity | 75.8% of city-scrape listings had 1+ stay in the last 12 months |
| Hosts | 55.8% of listings belong to hosts with 2+ listings |
| Quality | Median rating 4.86; 52.7% of rated listings score 4.85+ |
| Calendar | 23.8% of listings have zero open nights in the next year (booked or blocked) |

---

## Data cleaning rules (summary - full log in `outputs/cleaning_log.txt`)

| Rule | Action | Records |
|---|---|---|
| 13 columns 100% empty (e.g. `host_since`, `license`, `instant_bookable`) | dropped | - |
| `bathrooms` missing | filled from `bathrooms_text` | 8,135 |
| price < $20 | set to NA | 20 |
| `maximum_nights` >= 1125 (Airbnb "no limit") | set to NA | 9,444 |
| `minimum_nights` > 365 (a lease, not short stay) | row removed | 14 |
| price > Q3 + 1.5 x IQR ($633) | flagged `price_outlier`, kept | 1,129 |
| empty review comments | removed | 41 |

---

## Repository structure

```
CMCE30005-Renascence/
├── CMCE30005-Renascence.Rproj
├── README.md
├── scripts/00_packages.R
├── data/                 R scripts for import, overview, cleaning, EDA
│   ├── *.csv             (raw data - local only, not on GitHub)
│   └── processed/        (cleaned .rds - local only, rebuilt by cleaning script)
├── Analysis Process/     Descriptive / Predictive / Prescriptive analysis
└── outputs/
    ├── figures/          EDA charts (.png)
    ├── cleaning_log.txt
    └── eda_summary.txt
```

---

*Last updated: 11 October 2026*

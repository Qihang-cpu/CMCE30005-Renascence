# CMCE30005 Business Analytics Challenge
## Group4-Renascence - AIRBNB

**Subject:** CMCE30005 Business Analytics Challenge, Semester 2 2026

**University:** University of Melbourne

**Team Members:** Qihang Sun, Loc Le

## Download the Report

[Download the full PDF report](./Final%20Report.pdf)

---

## 1. Project Objective

### Background 

- **Background**  We are engaged by a client who intends to list multiple properties on Airbnb in Melbourne. We will act as their business analytics consultant.

- **Goal** goal of the project is supporting suggestions to our client who leases residential properties and runs them as Airbnb accommodation. 

- **Introduction about client**. A small operator preparing to list or manage short-term rental properties in Melbourne. The client needs to decide which accommodation product to launch first, what price to test, and which selling points to highlight.


Develop an evidence-based recommendation covering:

- **Product:** property type, guest capacity and accommodation experience.
- **Positioning:** amenities, photographs and listing-message priorities.
- **Launch price:** an initial nightly price supported by comparable listings and a pricing model.
- **Validation:** adjustments based on actual booking and cost information.

The project focuses on existing properties or properties being considered for management. It does not estimate property acquisition returns.

---

## 2. Business Problem and Challenges 

**Our problem will be: For new operators preparing to list or act as agents for Airbnb listings in Melbourne, how can they select appropriate rental products based on market data and determine the initial listing price and operation plan?**

### 2.1 Problem Split

Here will be our research questions that how we split our research problem step by step

| Questions | Methods |
| :--- | :--- |
| Which accommodation products are worth considering? | Comparison of locations, property types, bedroom counts, and guest capacities|
| What reference price is appropriate for a specified property? | Listing-price prediction model |
| Under the defined conditions, which option should be tested first, and at what initial price? | Candidate screening and trial-pricing rules |

### 2.2 Challenges

- **1** Our project focuses on product positioning and initial listing prices, as the model predicts advertised prices rather than bookings or profits. It therefore provides a pricing reference but cannot identify the most profitable option.

- **2** Using the same average price across regions ignores differences in property type, guest capacity, and experience. Choosing a region solely for its high listing prices can also overlook competition and review activity. The client therefore needs a clearly justified, actionable plan that can be refined using actual booking results.

- **3** Our client has limited funds, so poor choices can tie up their money, and the rent is difficult to adjust after signing a lease.

---

## 3. Data Sources

| Dataset | What Each Record Represents | Information Used in This Project | Corresponding Analysis |
| --- | --- | --- | --- |
| `listings` | A snapshot of one property listing | Location, coordinates, property type, bedrooms, guest capacity, amenities, pricing dates, and price | Describe the market and build a listing-price prediction model |
| `reviews` | One guest review | Review date, listing ID, and guest-experience keywords | Analyse review activity and guest-experience themes |
| `calendar` | One day for one listing | Availability indicator and minimum/maximum stay requirements | Describe stay rules and inform pilot settings |

**Reasons for variable selection:** Location and property type define comparable property groups. Bedrooms, guest capacity, bathrooms, and amenities support pricing. Reviews inform product positioning, while calendar data inform stay rules. Identifiers are used only to link datasets and are excluded from predictive features.

### 3.1 Data Understanding, Cleaning, and Exploration

**Our research focuses on small operators, so we include only non-Superhost listings. Given Airbnb’s demanding Superhost requirements, we assume that certified hosts already have strong property management skills and less need for our advisory services.**

The data stage consisted of three main tasks:
- Understanding the available datasets and their purposes.
- Cleaning and preparing the data for analysis.
- Exploring data quality and distributions to guide subsequent methods.

#### Data Sources

The project used Melbourne Airbnb data from June 2026, consisting of three datasets:

| Dataset | Unit of Observation | Main Information | Purpose |
|---|---|---|---|
| listings | One property | Location, property type, capacity, bedrooms, bathrooms, amenities, listing price, and quotation dates | Market comparisons and price prediction |
| reviews | One guest review | Property ID, review date, and review text | Review activity and accommodation experience themes |
| calendar | One property on one date | Availability, minimum stay, and maximum stay | Analysis of stay requirements |

#### Dataset Size and Linkage

- The listings dataset contained **25,728 properties and 90 variables**.
- The reviews dataset contained **1,026,690 reviews**.
- The datasets were linked using the property ID.

#### Interpretation of the Data

- Listing prices do not necessarily represent actual transaction prices.
- Review counts do not directly represent booking volumes.
- Unavailable calendar dates do not necessarily indicate confirmed bookings.

### 3.2 Data Cleaning and Preparation

#### Property ID Checks

- Checked for missing and duplicate property IDs.
- No missing or duplicate property IDs were found in this dataset.
- The cleaning logic retains the most recently scraped record if duplicates exist.

#### Price and Numeric Conversion

- Removed currency symbols and commas from price values.
- Converted prices, bedroom counts, guest capacity, and other relevant fields into numeric values.
- Extracted bathroom counts from bathroom descriptions.

#### Date Processing

- Converted date fields into date formats.
- Calculated:
  - The number of nights covered by each quotation.
  - The number of days between scraping and the quoted check-in date.

#### Property and Amenity Classification

- Grouped properties into four categories:
  - Apartments.
  - Houses and townhouses.
  - Cottages and guest accommodation.
  - Other property types.
- Created amenity indicators for features such as:
  - WiFi.
  - Kitchens.
  - Free on-site parking.
  - Self check-in.
  - Pools.
  - Fireplaces.
  - Gardens.
  - Air conditioning.

#### Missing Value Treatment

- Missing prices were not replaced with zero.
- Properties without prices remained available for supply analysis but were excluded from price modelling.
- Other numeric values requiring imputation were handled within the model training pipeline to avoid data leakage.

#### Review Preparation

- Applied a consistent **365-day review window**, from **17 June 2025 to 16 June 2026**.
- Aggregated review counts and theme mentions by property.
- Assigned zero recent reviews to properties with no matched reviews within the window.
- Identified the following themes using English keywords:
  - Walking and transport.
  - Peacefulness and nature.
  - Families and children.
  - Couples and celebrations.
  - Work and business.
- Theme measures captured keyword mentions only; they did not measure sentiment.


### 3.3 Defining the Analysis Scope

The sample was progressively restricted to listings relevant to the business problem, with a focus on the non-Superhost market.

| Filtering Stage | Listings Retained |
|---|---:|
| Original listing records | 25,728 |
| Listings captured in the current city scrape | 18,885 |
| Listings explicitly identified as non-Superhost | 11,674 |
| Non-Superhost entire homes and apartments | 8,214 |
| Nightly listing price between AUD 20 and AUD 2,000 | 8,024 |
| 1–3 bedrooms and capacity for 1–8 guests | 6,808 |
| Minimum stay of 1–7 nights | 6,533 |
| Quoted stay duration of 1–7 nights | 6,455 |
| Quoted check-in date 0–30 days after scraping | 5,673 |

The mainstream short-stay criteria were:

- Explicitly identified as **non-Superhost**.
- Listed as **Entire home/apt**.
- Nightly listing price between **AUD 20 and AUD 2,000**.
- **1–3 bedrooms**.
- Capacity for **1–8 guests**.
- Minimum stay of **1–7 nights**.
- Quoted stay duration of **1–7 nights**.
- Quoted check-in date **0–30 days after scraping**.

Two main analysis samples were established:

- **8,214 listings** for analysis of non-Superhost entire-home supply and market context.
- **5,673 listings** meeting the short-stay criteria for comparable-price analysis and subsequent predictive modelling.

Further eligibility requirements were applied within individual analyses, including sufficient review history and two-night comparability where relevant.

Superhost listings were excluded to align the analysis with the target market, rather than because their records were considered invalid. Listings outside the selected scope remained in the original data.

Non-Superhost status does not by itself establish that a host is an individual or a small-scale operator. The findings therefore apply to the defined non-Superhost sample and should not automatically be generalised to all hosts, long-stay accommodation, or specialised property types.


### 3.4 Visualizations and Deliverables

Here will be a discription about the main charts and graphs we posted in the output.
| Deliverable | Purpose |
|---|---|
| **Property distribution map** | Show the geographic distribution of accommodation types |
| **Comparable-price map** | Compare similar two-bedroom apartments across areas |
| **Product location map** | Present the locations of proposed launch plans |
| **Market comparison charts** | Explain supply, prices, review activity and amenities |
| **Calendar and activity charts** | Explain stay rules and historical review fluctuations |
| **Model evaluation charts** | Compare model performance with pricing baselines |
| **Product recommendation cards** | Specify product features, launch prices and stay rules |
| **30-day action plan** | Guide monitoring and price adjustments |

### 3.5 Exploratory Data Analysis (EDA)

#### Missing Data Assessment

Missingness was assessed across the **11,674 listings explicitly identified as non-Superhost in the current city scrape**, before restricting the sample to entire homes and applying the short-stay criteria.

| Variable | Missing Percentage |
|---|---:|
| Nightly listing price | 1.61% |
| Bedrooms | 15.73% |
| Bathroom count | 0.20% |
| Area | 0.00% |

Implications:

- Different analyses required different sample definitions.
- Listings without valid prices could still contribute to supply analysis.
- Price comparisons and predictive modelling required valid price information.
- Missing bedroom information prevented some listings from entering comparisons defined by bedroom count.
- These percentages describe the current non-Superhost sample, rather than all 25,728 original listing records.

#### Price Distribution

Among the **8,214 non-Superhost entire-home listings**, **8,094** had positive nightly listing prices.

Their observed price distribution was:

- Mean nightly listing price: **AUD 372.52**.
- Median nightly listing price: **AUD 281.79**.
- Maximum nightly listing price: **AUD 13,631.00**.
- P25–P75 range: **AUD 210.25–392.00**.

The distribution had a long right tail:

- A small number of expensive listings increased the mean.
- The median was less sensitive to extreme prices and provided a useful measure of the typical listing-price level.
- Subsequent comparisons used medians and quartiles within comparable product segments.
- The histogram displayed prices up to the **99th percentile, AUD 1,889.12**, for readability; higher-priced records remained in the underlying data.

These statistics describe the positive-price entire-home sample before applying the restricted short-stay price criteria.

#### Implications for Subsequent Analysis

- Comparable product segments were defined using:
  - Area.
  - Property group.
  - Bedroom count.
- Guest capacity was considered in sample eligibility and price modelling, rather than used as an additional segment identifier.
- Comparisons within segments reduced the influence of differences in property composition.
- The concentration of listings in central areas required caution when interpreting results for less-represented areas.
- Market comparisons and predictive modelling used explicitly defined samples.
- Observed listing prices represented advertised prices and did not establish actual transaction prices or booking outcomes.

### 3.6 Outputs of the Data Stage

The data stage produced:

- Cleaned listing records linked to aggregated review and calendar information at the listing level.
- Standardised numeric, date, property-type, and amenity variables.
- Review-activity measures calculated using a consistent observation window.
- A clearly defined target market of listings explicitly identified as non-Superhost.
- **8,214 entire-home listings** for supply and market-context analysis.
- **5,673 listings** meeting the short-stay criteria for comparable-price analysis and subsequent predictive modelling.
- Evidence supporting the use of medians and quartiles to describe the skewed listing-price distribution.
- Comparable product segments defined by **area, property group, and bedroom count**.

Individual analyses applied additional eligibility requirements where necessary, so their final sample sizes could differ.

At this stage, no final product selection or initial listing-price recommendation had been determined.
---

## 4. Analysis Roadmap 

### 4.1 Analysis Roadmap

Our analysis moves from defining the business problem to preparing the data, conducting descriptive, predictive, and prescriptive analysis, and developing operational recommendations.

The “existing four-person property” and “existing woodland property” are conditional client scenarios, not facts verified by the data.

### Overall Analysis Process

| Stage | Key Question | Methods | Main Output |
|---|---|---|---|
| **Business Problem** | Which rental product, initial price, and operating approach should be selected? | Define client objectives, scope, and conditional scenarios | A focused decision problem |
| **Data Understanding and Cleaning** | Which data are usable, and how can they be made consistent? | ID checks, type conversion, missing-value treatment, property and amenity coding, data linkage, time windows, and sample filtering | Prepared analysis datasets |
| **Exploratory Data Analysis** | What are the main data characteristics? | Missingness statistics, descriptive statistics, price histograms, and comparisons by bedroom count | Justification for medians and comparable property groups |
| **Descriptive Analytics** | How do locations and accommodation products differ? | Maps, grouped statistics, medians and quartiles, review keyword analysis, amenity proportions, calendar rules, and monthly trends | Evidence about market conditions and product positioning |
| **Predictive Analytics** | What is a suitable reference listing price for a specified product? | Host-grouped data splitting, regression models, baseline comparisons, and permutation importance | Evaluated pricing model and candidate predictions |
| **Prescriptive Analytics** | Which option meets the objectives and constraints? | Rule-based filtering, candidate ranking, constrained price selection, and sensitivity analysis | Conditional product choices, trial prices, and stay settings |
| **Integrated Findings** | How do the three types of analysis support the conclusions? | Connect market facts, model predictions, and decision rules | A traceable evidence chain |
| **Recommendations and Limitations** | How should the recommendations be implemented and validated? | Product cards, a 30-day action plan, price testing, financial scenarios, and limitations assessment | Operational actions and future evaluation measures |

### 4.2 Descriptive Analytics: Understand Market Differences

- **Geography and supply:** Map property locations and compare supply and property-type proportions across areas.
- **Comparable prices:** Group properties by area, property type, bedrooms, and capacity; compare median prices and quartiles.
- **Review activity:** Use a common 365-day window and, where relevant, properties with at least one year of review history.
- **Review themes:** Use English keyword matching to measure mentions of transport, nature, families, and other themes.
- **Amenities:** Compare the prevalence of pools, fireplaces, parking, gardens, and other facilities.
- **Stay rules and time patterns:** Analyse two-night stay rules within a 90-day calendar window and monthly review activity for a fixed property cohort.

### 4.3 Predictive Analytics: Estimate Reference Listing Prices

- **Target:** Nightly displayed listing price.
- **Inputs:** Area, property type, bedrooms, capacity, bathrooms, amenities, and quotation conditions.
- **Data splitting:** Group by host ID to prevent the same host’s properties from appearing across training and test sets.
- **Preprocessing:** Apply numeric imputation, standardisation, and categorical one-hot encoding within the training pipeline.
- **Models compared:**
  - Log-target ridge regression.
  - Random forest.
  - Gradient boosting.
- **Model selection:** Select the model with the lowest validation MAE; gradient boosting was selected.
- **Evaluation:** Compare test performance against an overall median price and an area-by-bedroom median price.
- **Interpretation:** Use permutation importance to identify which information the model relies on.
- **Candidate quotations:** Fix the month, lead time, check-in day type, and stay duration to generate comparable reference prices.

### 4.4 Prescriptive Analytics: Turn Evidence into Decisions

- **Eligibility checks:** Require sufficient comparable properties, review-history samples, and two-night quotations.
- **Scenario rules:**
  - **Urban one-bedroom pilot:** Among candidates meeting the review-activity threshold, select the area with the highest median listing price.
  - **Conditional four-person property:** Among eligible two-bedroom markets, select the area with the highest median annual review count.
  - **Conditional woodland property:** Use the assumed existing location and specified amenities to generate a quotation.
- **Trial price selection:** Within the comparable market’s 25th–75th percentile price range, choose the AUD 10 price increment closest to the model prediction.
- **Sensitivity analysis:** Change the review-activity threshold and check whether the preferred urban location changes.

### 4.5 Scope of the Analysis

- The project supports product selection and initial listing decisions.
- The model predicts listing prices.
- The decision rules align recommendations with stated objectives and constraints.
- The project does not establish profit-maximising prices.

### 4.6 Flowchart

```mermaid
flowchart TD
    A["`Business
Problem`"]
    B["`Data
Understanding
and Cleaning`"]
    C["`Exploratory
Data Analysis`"]
    D["`Descriptive
Analytics
Understand
market differences`"]
    E["`Predictive
Analytics
Estimate reference
listing prices`"]
    F["`Prescriptive
Analytics
Apply objectives
and constraints`"]
    G["`Integrated
Findings`"]
    H["`Recommendations
and Action Plan`"]
    I["`Limitations
and Future
Validation`"]

    A --> B
    B --> C
    C --> D
    D --> E
    D --> F
    E --> F
    D --> G
    E --> G
    F --> G
    G --> H
    H --> I
```

---

## 5. Descriptive Analysis

### 5.1 Purpose and Methods

- Examine differences across Melbourne’s short-term rental markets.
- Provide evidence for product selection, positioning, and operating settings.
- Use:
  - Descriptive statistics.
  - Group comparisons.
  - Geographic visualisation.
  - Review keyword matching.
  - Amenity proportions.
  - Monthly trend analysis.
- No machine learning, sentiment analysis, or time-series forecasting models were used in this section.

### 5.2 D1: Geographic Distribution and Property Types

- **Objective:** Identify where entire properties are concentrated and which accommodation types dominate.

- **Methods:**
  - Plot property coordinates on administrative maps.
  - Count properties by area.
  - Calculate property-type proportions.

- **Key findings:**
  - Approximately 97% of entire properties in the Melbourne administrative area were apartments.
  - In Yarra Ranges, approximately 41% were cottages or guest accommodation, and 45% were houses or townhouses.

- **Limitation:** Property counts measure supply, not demand.

### 5.3 D2: One-Bedroom Apartment Comparisons

- **Objective:** Compare listing prices and review activity across urban markets.

- **Methods:**
  - Select the four areas with the largest apartment supply.
  - Compare one-bedroom apartments accommodating 2–3 guests.
  - Calculate median listing prices.
  - Compare median review counts within a common 365-day window, using properties with at least one year of review history.
- **Key findings:**

| Area | Median Listing Price (AUD/Night) | Median Annual Review Count |
|---|---:|---:|
| Melbourne | 208 | 16 |
| Yarra | 232 | 17 |
| Port Phillip | 206.7 | 11 |
| Stonnington | 203 | 12 |

- **Implication:** Yarra combined a roughly 12% higher median listing price than Melbourne with similar review activity, supporting its inclusion in later candidate selection.

- **Limitation:** Review activity does not directly measure bookings.

### 5.4 D3: Bedrooms, Location, and Per-Person Prices

- **Objective:** Examine how prices and review activity vary by location and property size.

- **Methods:**
  - Map prices for two-bedroom apartments accommodating 4–5 guests.
  - Display areas only when at least 30 comparable properties are available.
  - Compare median prices and review counts by area and bedroom count.
  - Divide median listing prices by assumed guest numbers to illustrate per-person prices.

- **Key findings:**
  - Melbourne two-bedroom apartments: AUD 288 per night, or AUD 72 per person for four guests.
  - Melbourne one-bedroom apartments: AUD 208 per night, or AUD 104 per person for two guests.
  - Median annual reviews were higher for two-bedroom than one-bedroom apartments in Melbourne, but lower in Yarra.

- **Limitation:** Per-person prices are illustrative calculations, not observed guest payments.

### 5.5 D4: Review Themes and Amenities

- **Objective:** Identify differences in review topics and local amenity provision.

- **Methods:**
  - Calculate theme mentions as a proportion of non-empty reviews.
  - Calculate amenity availability as a proportion of entire properties.
  - Compare areas using grouped bar charts.

- **Key findings:**
  - Walking and transport appeared in approximately 27% of Melbourne reviews and 10% of Yarra Ranges reviews.
  - Peacefulness and nature appeared in approximately 5% and 35%, respectively.
  - Approximately 62% of Melbourne entire properties listed a pool.
  - Approximately 54% of Yarra Ranges entire properties listed a fireplace, and 91% listed free on-site parking.

- **Implication:** Urban products can emphasise convenience, while woodland products can emphasise nature and relevant holiday amenities.

- **Limitations:**
  - Keyword mentions do not establish positive sentiment.
  - Amenity prevalence does not demonstrate a causal price premium.

### 5.6 D5: Stay Rules and Monthly Review Activity

- **Objective:** Assess market support for two-night stays and examine changes in review activity.

- **Methods:**
  - Analyse calendar records from 17 June to 14 September 2026.
  - Calculate the proportion of available dates whose daily rules permit a two-night stay.
  - Track monthly reviews per 100 properties using a fixed cohort with sufficient review history.
  - Exclude incomplete months and display trends using line charts.
- **Key findings:**

  - Daily rules permitted two-night stays on approximately:
    - 70% of available dates in Melbourne.
    - 59% in Yarra.
    - 95% in Yarra Ranges.
  - Review activity varied across months.

- **Implication:** A two-night minimum stay provides an initial operating option to test.

- **Limitations:**
  - The analysis did not check availability for two consecutive nights.
  - Unavailable dates do not necessarily indicate bookings.
  - Monthly patterns were described, not forecast.

### 5.7 D6: Guest Ratings and Estimated Annual Revenue

- **Purpose:** Examine whether guest ratings are associated with estimated annual revenue after accounting for listing characteristics, and assess whether the relationship shows quadratic curvature.

- **Method:**
  - Use **multiple linear regression (OLS)** with `annual_revenue`, measured in AUD, as the dependent variable, without a logarithmic transformation.
  - Include the overall guest rating as the main explanatory variable.
  - Control for **area, property type, bedroom count, guest capacity, bathroom count, and minimum stay**.
  - Analyse **3,716 eligible listings**. All observations had complete model variables, so no additional listings were excluded due to missing values.
  - Use **HC3 heteroscedasticity-robust standard errors**.
  - Fit an additional model containing a centred rating term and its square to assess possible curvature.

- **Main findings:**
  - In the linear model, the rating coefficient was **AUD 12,531.19 per rating point**, with a **95% confidence interval of AUD 10,859.71–14,202.66** and **p < .001**.
  - Holding the included characteristics constant, a **0.1-point higher rating** was associated with approximately **AUD 1,253.12 higher fitted annual revenue**.
  - The linear model explained **16.66%** of the variation in estimated annual revenue, with an **adjusted R² of 0.1582**.
  - Adding the quadratic rating term increased **R² to 0.1706** and **adjusted R² to 0.1621**.
  - However, the squared rating term was **not statistically significant (p = .183)**. The analysis therefore did not detect statistically significant quadratic curvature.

  These results indicate that **higher guest ratings were significantly associated with higher estimated annual revenue after controlling for the included listing characteristics**. The quadratic model provided only a small improvement in fit and did not establish a curved relationship.

- **Implications:** Guest ratings are a relevant indicator when assessing estimated revenue differences between listings. However, the model's modest explanatory power means that ratings should be considered alongside property characteristics and operating conditions. The results support monitoring guest experience but do not quantify the financial return from a specific service improvement.

- **Limitations:**
  - Estimated annual revenue does not represent verified revenue or profit.
  - The association does not establish that improving ratings causes revenue to increase.
  - The coefficient describes an adjusted association within the analysed sample, rather than a guaranteed revenue increase for an individual listing.
  - A non-significant quadratic term does not prove that the relationship is exactly linear.
  - HC3 standard errors address heteroscedasticity but do not explicitly account for dependence between listings managed by the same host.
  - Overall ratings and estimated annual revenue may cover different time periods.
  - This analysis does not directly test the relationship between ratings and nightly listing prices or establish a revenue-maximising price.

### 5.8 Outputs

- Area- and property-type comparisons describing the non-Superhost entire-home market.
- Historical review-activity measures supporting the comparison of candidate product segments.
- Evidence on listing characteristics and amenities to inform product positioning.
- Market information on minimum-stay requirements.
- An exploratory assessment of the association between guest ratings and estimated annual revenue.
- Inputs for subsequent listing-price prediction, comparable-price analysis, and rule-based product recommendations.

The descriptive stage provided evidence for further evaluation; final product recommendations and initial reference prices were determined in the subsequent stages.


---

## 6. Predictive Analysis

### 6.1 Purpose

- Estimate reference nightly listing prices for specified accommodation products.
- Compare alternative models and assess whether they outperform simple pricing rules.
- Generate candidate quotations for the subsequent prescriptive analysis.
- Predict displayed listing prices, rather than future transaction prices, occupancy, or profit.

  **Models Used**

| Model | Target Treatment | Purpose |
|---|---|---|
| Ridge regression | Log-transformed price; predictions converted back to AUD | Provide a regularised linear benchmark |
| Random forest regression | Log-transformed price; predictions converted back to AUD | Capture nonlinear relationships and interactions |
| Histogram-based gradient boosting | Original price scale, using absolute-error loss | Capture nonlinear relationships while directly targeting absolute pricing error |

- Trained all three models on the same training set.
- Compared their performance on the same validation set.
- Selected the model with the lowest validation **Mean Absolute Error (MAE)**.

  **Model Selection**

| Model | Validation MAE (AUD) | Validation MedAE (AUD) | Predictions Within 25% |
|---|---:|---:|---:|
| Log-target ridge regression | 79.36 | 52.16 | 60.5% |
| Random forest | 76.10 | 46.51 | 61.8% |
| Gradient boosting | 74.89 | 46.91 | 63.4% |

- **Gradient boosting was selected** because it achieved the lowest validation MAE.
- The selected model was refitted on the combined training and validation sets.
- Final performance was assessed on the held-out test set.


### 6.2. Data and Variables

  **Modelling Sample**

- Used ** 5673 entire properties** meeting the project's mainstream short-stay criteria.
- Restricted the sample by price, bedrooms, capacity, minimum stay, quoted stay duration, and booking lead time.

The variables below will be used for all the three models

  **Dependent Variable**

| Variable | Description |
|---|---|
| `price_aud` | Nightly displayed listing price in AUD |

  **Independent Variables**

| Category | Variables | Description |
|---|---|---|
| Property size | `bedrooms`, `accommodates`, `bath_num` | Bedrooms, guest capacity, and parsed bathroom count |
| Location | `area` | Administrative area |
| Property category | `property_group` | Apartment, house/townhouse, cottage/guest accommodation, or other |
| Stay requirement | `minimum_nights` | Minimum permitted stay |
| Quotation conditions | `quote_nights`, `quote_lead` | Quoted stay duration and days between scraping and check-in |
| Check-in timing | `quote_weekend`, `quote_month` | Weekend check-in indicator and check-in month |
| Amenities | 12 binary indicators | Whether each listed amenity is present |

The amenity indicators covered:

- WiFi.
- Kitchen.
- Free on-site parking.
- Self check-in.
- Pool.
- Fireplace.
- Hot tub.
- Pets allowed.
- Dedicated workspace.
- BBQ.
- Garden or backyard.
- Air conditioning.

  **Other Variables**

- **`host_id`:** Used to group properties when splitting the data; not used as a predictor.
- **Property ID:** Used for data linkage; not used as a predictor.
- **Review counts and themes:** Used in descriptive analysis and decision-making; excluded from the pricing model.
- **Superhost status:** Not included in the current model.


### 6.3 Evaluation Methods and Results

#### Evaluation Metrics

- **MAE:** Average absolute difference between predicted and observed listing prices.
- **MedAE:** Median absolute difference, representing a typical pricing error.
- **RMSE:** An error measure that gives greater weight to large prediction errors.
- **R²:** Predictive performance relative to using the test-set mean price.
- **Within 25%:** Percentage of predictions within 25% of observed listing prices.

#### Baseline Comparisons

The selected model was compared with:

- **Overall median price:** Apply the same development-sample median price to every test listing.
- **Area-by-bedroom median:** Use the development-sample median for the same area and bedroom count, falling back to the overall median when no matching group is available.

Models were selected using validation-set MAE. The final evaluation used a separate test set, with hosts kept separate across training, validation, and test samples.

#### Test Results

| Method | MAE (AUD) | MedAE (AUD) | RMSE (AUD) | R² | Within 25% |
|---|---:|---:|---:|---:|---:|
| Overall median price | 109.32 | 67.11 | 196.66 | -0.049 | 47.8% |
| Area-by-bedroom median | 93.74 | 52.83 | 174.83 | 0.171 | 57.8% |
| Selected gradient boosting model | **87.78** | **51.34** | **165.98** | **0.253** | **60.9%** |

- The selected model outperformed both baseline pricing methods.
- Approximately **61 out of 100 predictions** were within 25% of observed listing prices.
- The typical absolute pricing error remained approximately **AUD 51 per night**.
- These results support using the model as an initial pricing reference, followed by checks against comparable listings.

### 6.4 Model Interpretation

- Used **permutation importance** on the validation set.
- Randomly shuffled one predictor at a time and measured the increase in MAE.
- Repeated the process **three times** to calculate average importance.
- A larger increase in MAE indicates that the model relied more heavily on that predictor.
- The model used property characteristics, location, amenities, and quotation conditions to estimate listing prices.
- Feature importance describes predictive contribution; it does not show how much installing an amenity or changing a property feature would increase revenue.
- The separate rating–revenue regression examines associations with estimated annual revenue and does not determine the pricing model’s feature importance.

### 6.5 Candidate Price Predictions

#### Comparable Quotation Approach

- Focus on non-Superhost entire homes/apartments within the study scope.
- Group comparable listings by **area, property type, and bedroom count**.
- Select actual listings with a **two-night quoted stay** and a minimum-stay requirement of **no more than two nights**.
- Retain each listing’s recorded guest capacity, bathrooms, amenities, quotation month, check-in day, and booking lead time.
- Generate predictions for these listings and use the **median predicted price within each product group** as its model reference price.
- A two-night quotation provides a comparison basis; it does not prescribe a two-night minimum stay for clients.

#### Product Configuration

- Use the characteristics of actual comparable listings rather than an invented client property.
- Report guest capacity as a reference based on the product group, subject to confirmation for the actual property.
- Do not assume that every apartment has air conditioning, self check-in, or other amenities.
- Recalculate the price reference once a client’s actual property and intended stay dates are known.

#### Example Predictions

| Candidate Product | Model Reference Price (AUD/Night) |
|---|---:|
| Melbourne three-bedroom apartment; approximately six guests | **406.4** |
| Yarra one-bedroom apartment; approximately two guests | **228.3** |
| Melbourne one-bedroom apartment; approximately two guests | **216.1** |

- Predictions were generated for the wider candidate set before the final product selection.
- Product selection combined sample-size requirements, independent host counts, review history, and review activity.
- Model reference prices were passed to prescriptive analysis alongside comparable-price distributions.
- Final trial prices were selected in **AUD 10 increments** within each group’s **25th–75th percentile price range**, choosing the available price closest to the model reference.
- This produced initial trial prices of **AUD 410, AUD 230, and AUD 220 per night**, respectively.


### 6.7 Outputs and Limitations

- **Outputs:**
  - An evaluated reference-pricing model.
  - Candidate product predictions.
  - Comparisons against simple pricing benchmarks.
  - Evidence about model error and predictor importance.

- **Limitations:**
  - The model matches historical listing prices, not actual booking outcomes.
  - Prediction errors remain material, requiring comparable-market checks and manual review.
  - Feature importance does not establish causal price premiums.
  - Results do not demonstrate profit-maximising prices or guaranteed business performance.

---

## 7 Prescriptive Analysis

### 7.1 Purpose

- Combine market evidence and predicted listing prices to select rental products and initial operating settings.
- Answer three questions:
  - Which product and location should be selected?
  - Which initial nightly price should be tested?
  - Which minimum-stay setting should be used?

### 7.2 Decision Model

- Use a **rule-based decision model with explicit constraints**.
- No additional machine learning model is trained at this stage.
- The gradient boosting model from predictive analysis supplies reference prices.
- The decision process consists of:
  - **Product selection:** Filter eligible candidates and rank them according to scenario-specific objectives.
  - **Trial price selection:** Choose an allowable price closest to the model prediction.

### 7.3 Methods

  **Candidate Eligibility**

Urban apartment candidates must satisfy the following conditions:

| Criterion | Requirement |
|---|---|
| Candidate areas | The four areas with the largest apartment supply |
| Comparable properties | At least 100 |
| Properties with at least one year of review history | At least 80 |
| Comparable two-night quotations | At least 30 |

For candidate $i$ within the four selected areas, sample eligibility is:

$$
E_i = \mathbf{1}(N_i \geq 100 \land H_i \geq 80 \land Q_i \geq 30)
$$

Where:

- $E_i$: Sample eligibility indicator.
- $N_i$: Number of comparable properties.
- $H_i$: Number of comparable properties with at least one year of review history.
- $Q_i$: Number of comparable two-night quotations.
- $\mathbf{1}(\cdot)$: Equals 1 when all three sample requirements are satisfied and 0 otherwise.

#### Scenario A: Review-Activity Constraint

The minimum acceptable review activity is:

$$
R_i \geq \alpha R_{\text{ref}}
$$

With the current settings:

$$
R_i \geq 0.90 \times 16 = 14.4
$$

Where:

- $R_i$: Median annual review count for candidate $i$.
- $R_{\text{ref}}$: Melbourne's comparable one-bedroom median annual review count.
- $\alpha$: Required proportion of the reference activity level.

The selection rule is:

$$
i_A^{*} = \arg\max_{i:\,E_i=1,\;R_i \geq \alpha R_{\text{ref}}} M_i
$$

Where:

- $E_i$: Sample eligibility indicator defined above.
- $M_i$: Median listing price for candidate $i$.
- $i_A^{*}$: Selected candidate under Scenario A.

Among eligible candidates that meet the review-activity threshold,
select the candidate with the highest median listing price.

If median listing prices are tied, prioritize the candidate
with higher review activity.

#### Scenario B: Review-Activity Objective

Select the eligible two-bedroom candidate with the highest median annual review count:

$$
i_B^{*} = \arg\max_{i:\,E_i=1} R_i
$$

Where:

- $E_i$: Sample eligibility indicator.
- $R_i$: Median annual review count for candidate $i$.
- $i_B^{*}$: Selected candidate under Scenario B.

If review activity is tied, prioritize the candidate with the higher median listing price.

  **Trial Price Selection**

- Restrict the trial price to the comparable two-night market's interquartile range.
- Use price increments of **AUD 10**.
- Select the allowable price closest to the gradient boosting prediction.

An allowable price $p$ must satisfy:

$$
p = 10k,\quad k \in \mathbb{Z}
$$

$$
P_{25,i} \leq p \leq P_{75,i}
$$

Let $G_i$ denote the set of prices satisfying both conditions.

Select the trial price:

$$
p_i^{*} = \arg\min_{p \in G_i} |p - \hat{p}_i|
$$

Where:

- $P_{25,i}$: 25th percentile of comparable two-night listing prices.
- $P_{75,i}$: 75th percentile of comparable two-night listing prices.
- $G_i$: Allowable prices in AUD 10 increments within this range.
- $\hat{p}_i$: Model-predicted reference price on the same two-night basis.
- $p_i^{*}$: Selected trial price.

The trial-price rule requires a non-empty allowable price set.
If two prices are equally close to the reference price, select the lower price.

This objective minimises the distance from the model prediction within market-based constraints. It does not maximise profit.

  **Minimum-Stay Setting**

- Propose an initial minimum stay of **two nights** for all three scenarios.
- Use descriptive calendar analysis as market context.
- Validate this setting against actual turnover costs and booking behaviour.
- The minimum stay is an operating proposal, not an optimised model output.

  **Sensitivity Analysis**

- Change the review-activity requirement for Scenario A.
- Test whether the preferred location remains eligible and selected.

| Reference Proportion | Minimum Annual Review Count | Eligible Areas | Selected Area |
|---|---:|---:|---|
| 75% | 12.0 | 3 | Yarra |
| 90% | 14.4 | 2 | Yarra |
| 100% | 16.0 | 2 | Yarra |
| 110% | 17.6 | 0 | No eligible candidate |

### 7.4 Results

#### Selected Products and Prices

| Scenario | Product and Location | Model Reference Price (AUD/Night) | Trial Price (AUD/Night) |
|---|---|---:|---:|
| **A: Melbourne Three-Bedroom Option** | Entire three-bedroom apartment in Melbourne; approximately six guests | 406.4 | **410** | 
| **B: Yarra One-Bedroom Option** | Entire one-bedroom apartment in Yarra; approximately two guests | 230.7 | **228.3** |
| **C: Melbourne One-Bedroom Option** | Entire one-bedroom apartment in Melbourne; approximately two guests | 220.0 | **216.1** |

#### Comparable-Market Price Constraints

Prices below are nightly rates from comparable two-night quotations.

| Scenario | Two-Night Comparables | 25th Percentile (AUD/Night) | Median (AUD/Night) | 75th Percentile (AUD/Night) | Trial Price (AUD/Night) |
|---|---:|---:|---:|---:|---:|
| A | 112 | 347.3 | 421.0 | 499.1 | **410** |
| B | 66 | 216.4 | 237.0 | 262.1 | **230** |
| C | 333 | 190.5 | 219.0 | 248.5 | **220** |

#### Conclusions

- **Melbourne three-bedroom apartments rank first under the selection rules:**
  - The group contains **240 listings**, **121 independent hosts**, and **151 listings with at least one year of review history**.
  - The median annual review count in the history-qualified sample is **11**.
  - The recommended initial trial price is **AUD 410 per night**.

- **Yarra one-bedroom apartments provide a second option:**
  - The group contains **111 listings**, **80 independent hosts**, and **66 listings with at least one year of review history**.
  - The median annual review count in the history-qualified sample is **11**.
  - The recommended initial trial price is **AUD 230 per night**.

- **Melbourne one-bedroom apartments provide a third option:**
  - The group contains **961 listings**, **387 independent hosts**, and **589 listings with at least one year of review history**.
  - The median annual review count in the history-qualified sample is **10**.
  - The recommended initial trial price is **AUD 220 per night**.

- **The same three products remain selected under the relaxed, main, and stricter sample requirements.**
  - Under the largest-sample requirements, Yarra one-bedroom apartments no longer qualify, and Melbourne two-bedroom apartments enter the top three.

- **All three trial prices satisfy the comparable-market price constraints.**
  - Each price falls within its product group’s 25th–75th percentile range.
  - Prices are selected in AUD 10 increments, choosing the available price closest to the model reference.
  - The two-night comparison does not impose a two-night minimum stay.

- **The recommendations support clients with different property situations.**
  - Clients without a property can use the three options to identify potential management opportunities.
  - Clients with other properties can apply the same comparable-listing approach to establish their own starting prices.
  - Selection ranks opportunities for further assessment; it does not establish which property will generate the highest profit.

### 7.5 Limitations

| Limitation | Implication |
|---|---|
| Analyst-defined thresholds | The 100/80/30 sample requirements and 90% activity threshold are adjustable business rules, not statistical significance criteria |
| No profit optimisation | Missing booking, demand-response, and cost data prevent identification of profit-maximising prices |
| Reviews as an activity proxy | Review counts do not directly measure bookings, occupancy, or profitability |
| Preference for higher listing prices | Scenario A favours higher listing-price positioning without demonstrating stronger realised performance |
| Prediction uncertainty | Trial prices depend on a model with a test median absolute error of approximately AUD 49 per night |
| Interquartile range interpretation | The comparable-price range is a market distribution, not a prediction confidence interval or guarantee of bookings |
| Limited sensitivity testing | Only Scenario A's review-activity threshold was varied; other thresholds and pricing constraints were not comprehensively tested |
| Unverified client property assumptions | Ownership, location, capacity, and amenities must be confirmed before implementing the conditional scenarios |

### 7.6 Outputs

- Three product recommendations with explicit applicability conditions.
- Initial nightly trial prices.
- A proposed two-night minimum stay.
- Transparent selection rules and price constraints.
- Sensitivity results showing when the urban recommendation remains feasible.

---

## 8 Results and Conclusion

After integrating the results of **Descriptive, Predictive, and Prescriptive Analysis**, our final conclusion is:

**Under the objective of prioritising an urban small-property pilot while balancing listing-price positioning and review activity, the preferred option is a one-bedroom apartment for two guests in Yarra, with an initial trial price of AUD 240 per night and a two-night minimum stay.** If the client already owns a four-person property or a woodland property meeting the specified requirements, the corresponding conditional scenario can be applied.

### 8.1 How Do the Three Analyses Support the Conclusion?

| Analytical Stage | Evidence | Contribution to the Final Decision |
|---|---|---|
| **Descriptive Analysis** | Yarra's median one-bedroom apartment price was AUD 232, compared with AUD 208 in Melbourne; median annual review counts were similar at 17 and 16 | Supports including Yarra as an urban pilot candidate |
| **Predictive Analysis** | Under the specified property configuration and quotation scenario, the model estimated approximately AUD 238 for a Yarra one-bedroom apartment | Provides a reference for initial pricing |
| **Prescriptive Analysis** | Yarra met the sample and activity requirements and had the highest median listing price among eligible candidates; the comparable-price range and AUD 10 increments produced a trial price of AUD 240 | Converts market evidence and predictions into an actionable proposal |

Therefore, **Yarra's preferred status follows from a rule-based comparison under a specific objective**. It does not mean that Yarra is optimal for every business objective.

### 8.2 Three Final Proposals

For small operators without Superhost status, we recommend the following property options for initial consideration.

| Proposal | Location and Product | Initial Trial Price | Minimum Stay | Product Positioning |
|---|---|---|---|---|
| **A: Melbourne Three-Bedroom Option** | Entire three-bedroom apartment in Melbourne; approximately **6 guests** | **AUD 410/night** | Set according to turnover costs and comparable listings | Three separate bedrooms and shared living space for families or groups |
| **B: Yarra One-Bedroom Option** | Entire one-bedroom apartment in Yarra; approximately **2 guests** | **AUD 230/night** | Set according to turnover costs and comparable listings | A comfortable space for two, with clear arrival and check-in arrangements |
| **C: Melbourne One-Bedroom Option** | Entire one-bedroom apartment in Melbourne; approximately **2 guests** | **AUD 220/night** | Set according to turnover costs and comparable listings | A compact urban stay for two, with accurately presented amenities and transparent fees |

- **Clients without a property:** use these options to approach owners and compare available properties, management arrangements, and operating costs.
- **Clients with a matching property:** confirm its capacity and amenities, then adjust the starting price for the intended stay dates.
- **Clients with other properties:** match nearby competitors by location, property type, bedroom count, and guest capacity to develop a suitable pricing plan.

### 8.3 Final Assessment of the Pricing Tool

**The selected gradient boosting model provides an initial pricing reference, supported by comparable listings and property-specific checks.**

- Approximately **60.9%** of its test predictions were within **25%** of observed listing prices, compared with **57.8%** for the area-by-bedroom median method.
- The median absolute prediction error was approximately **AUD 51 per night**.
- The recommended starting prices are **AUD 410, AUD 230, and AUD 220 per night**, adjusted to reflect actual amenities and stay dates.
- The two-night stay used for price comparison does not require every property to adopt a two-night minimum.

### 8.4 Final Action Recommendations

- **Before launch:** identify a suitable property, confirm guest capacity and operating costs, and compare competing listings for the same stay dates.
- **Listing preparation:** use accurate photos, describe the layout and amenities clearly, disclose all fees, and provide simple arrival, key-collection, and appliance instructions.
- **Cleaning and service:** thoroughly clean bedrooms, bathrooms, and kitchens between stays, verify standards with a checklist, respond promptly to guests, and address recurring complaints first.
- **Air conditioning:** clean and service existing units and advertise them accurately. Assess installation where guest demand, comparable properties, and installation costs justify it.
- **Weeks 2–3:** monitor views, enquiries, bookings, and guest feedback. Test one pricing or service change at a time.
- **Week 4:** review bookings, cancellations, income, and operating expenses to decide whether to retain or adjust the price and operating plan.

**The final recommendation combines property selection, initial pricing, and practical service improvements. Clients can use the three proposed products to explore management opportunities or apply the same pricing and operational approach to their existing properties.**


---

## 9. Recommendation

The recommendations translate the analytical findings into three areas of action: **configure the rental products, conduct a 30-day operational test, and adjust the proposals using actual business results.**

### 9.1 Product Launch Recommendations

| Proposal | Product and Location | Initial Settings | Configuration Requirements | Immediate Actions |
|---|---|---|---|---|
| **A: Melbourne Three-Bedroom Apartment** | Entire three-bedroom apartment in Melbourne; approximately **6 guests** | **AUD 410/night**; adjust for amenities and stay dates | Verify sleeping arrangements and guest capacity; maintain clean bedrooms, bathrooms and kitchen; service existing air conditioning | Approach suitable owners, compare operating costs, and showcase the three bedrooms, shared living space and actual amenities |
| **B: Yarra One-Bedroom Apartment** | Entire one-bedroom apartment in Yarra; approximately **2 guests** | **AUD 230/night**; adjust for amenities and stay dates | Prepare a clean space for two; provide clear arrival and key-collection instructions; check existing appliances | Verify transport access, use accurate photos, clearly explain fees, and test the check-in process |
| **C: Melbourne One-Bedroom Apartment** | Entire one-bedroom apartment in Melbourne; approximately **2 guests** | **AUD 220/night**; adjust for amenities and stay dates | Verify sleeping arrangements; maintain the bedroom, bathroom and kitchen; provide appliance instructions | Compare nearby one-bedroom listings, highlight the property's actual features, and clearly describe access and facilities |

#### Recommended Property Options

- **Melbourne: three-bedroom apartment**
  - Guest capacity: approximately 6 people.
  - Initial price: **AUD 410 per night**.

- **Yarra: one-bedroom apartment**
  - Guest capacity: approximately 2 people.
  - Initial price: **AUD 230 per night**.

- **Melbourne: one-bedroom apartment**
  - Guest capacity: approximately 2 people.
  - Initial price: **AUD 220 per night**.

#### Property Selection and Pricing

- Adjust starting prices based on amenities and intended stay dates.
- **Clients without a property:** approach owners of the recommended property types and compare management fees and operating costs.
- **Clients with other properties:** set prices using nearby listings with similar property types and guest capacities.

#### Operational Improvements

- **Cleaning:** thoroughly clean bedrooms, bathrooms and kitchens between stays, and verify standards using a checklist.
- **Listing accuracy:** provide realistic photos and clear descriptions of layouts, fees and amenities.
- **Check-in:** provide simple instructions for arrival, key collection and appliance use.
- **Communication:** respond promptly to guests and prioritise recurring complaints.
- **Air conditioning:** clean and service existing units and clearly advertise them. Consider installation based on guest demand, comparable properties and costs.

### 9.2 30-Day Action Plan

Here we posted a monthly plan for our client that they can followed to operate the properties:

| Timing | Actions | Information to Record | Basis for the Next Decision |
|---|---|---|---|
| **Before launch** | Select a proposal based on the actual property; verify amenities, costs, applicable rental requirements, and approximately 10 comparable listings for the same dates | Differences between the actual property and the proposal template | Reassess pricing if differences are substantial |
| **Week 1** | Launch at the starting price with a two-night minimum; complete photographs and listing descriptions | Exposure, views, enquiries, booked nights, and average stay duration | If exposure is low, first review listing content and distribution |
| **Weeks 2–3** | Test one price change at a time under comparable days of the week and booking lead times | View-to-booking conversion, transaction amounts, cancellations, and variable costs | If views are sufficient but conversion is weak and competitors are cheaper, consider testing a price reduction of approximately 10% |
| **Week 4** | Review actual net contribution and turnover costs | Net contribution per available night and guest feedback | If nights fill quickly and net contribution is acceptable, consider testing an increase of approximately 10%; continue observing if evidence is insufficient |

### 9.3 Suggested Price Test Levels

The following levels are approximately 10% below and above the starting prices, rounded to AUD 10 increments. They are **analyst-defined test settings**.

| Proposal | Lower Test Price | Starting Price | Higher Test Price |
|---|---:|---:|---:|
| A: Melbourne: three-bedroom apartment | AUD 380 | AUD 420 | AUD 460 |
| B: Yarra: one-bedroom apartment | AUD 200 | AUD 240 | AUD 280 |
| C: Melbourne: one-bedroom apartment | AUD 190 | AUD 220 | AUD 250 |

- Change one pricing setting at a time to make results easier to interpret.
- Account for differences in day of the week, dates, and booking lead time when comparing results.
- Sequential price changes for the same property are affected by time-related factors and cannot automatically be described as rigorous A/B experiments.

### 9.4 Illustrative Financial Scenarios

Use **trial price × assumed booked nights** to illustrate the amounts associated with different sales volumes.

| Proposal | Nightly Trial Price | Assuming 10 Booked Nights | Assuming 15 Booked Nights | Assuming 20 Booked Nights |
|---|---:|---:|---:|---:|
| A: Melbourne: three-bedroom apartment | AUD 410 | AUD 4,100 | AUD 6,150 | AUD 8,200 |
| B: Yarra: one-bedroom apartment | AUD 230 | AUD 2,300 | AUD 3,450 | AUD 4,600 |
| C: Melbourne: one-bedroom apartment | AUD 220 | AUD 2,200 | AUD 3,300 | AUD 4,400 |

These are illustrative financial scenarios, **not revenue forecasts or net profit estimates**. Actual evaluation must also incorporate fees, variable costs, and property holding costs.

### 9.5 Evaluating the Recommendations

- **Conversion performance:** Whether views and enquiries translate into actual bookings.
- **Booking performance:** Booked nights, average stay duration, and cancellations.
- **Operating performance:** Turnover costs, variable costs, and net contribution per available night.
- **Guest experience:** Whether actual guest feedback supports the intended product positioning.

The model's ability to match listing prices evaluates the pricing tool only. **The recommendations must ultimately be assessed using actual bookings, costs, and net contribution.**

---

## 10. Future analysis based on the limitations of our project

### 10.1 Limitations

| Limitation | Impact on the Conclusions |
|---|---|
| **Historical listing data** | The data reflect listings from June 2026 and do not directly represent current transaction prices or optimal year-round prices. Differences in quotation dates and stay durations also affect comparability. |
| **Missing actual bookings and costs** | Actual occupancy, net profit, and investment returns cannot be directly evaluated, and the recommended prices cannot be shown to maximise profit. |
| **Reviews as an activity proxy** | Review counts do not equal booking counts, and higher review activity does not necessarily indicate greater profitability. |
| **Missing data and restricted sample scope** | Some properties lack price and bedroom information. The analysis focuses on mainstream entire-property short stays, so the findings cannot be directly extended to long-term, luxury, or other specialised markets. |
| **Limited review theme analysis** | English keywords identify theme mentions but do not establish sentiment, actual guest characteristics, or the full meaning of multilingual reviews. |
| **Remaining prediction errors** | The selected model has a median absolute error of approximately AUD 49 per night, requiring comparable-market checks and manual review. Feature importance does not establish causality. |
| **Analyst-defined decision rules** | Sample thresholds, review-activity requirements, and pricing constraints are project assumptions. Recommendations may change when client objectives change. |
| **Unverified client property scenarios** | The four-person and woodland properties are conditional scenarios. The data do not establish that the client owns these properties or that they have the specified amenities. |
| **Location and stay-rule interpretation limits** | Map coordinates may be deliberately obscured. The calendar analysis does not confirm availability for two consecutive nights or establish that a two-night minimum is optimal after accounting for turnover costs. |
| **Time-related influences on price testing** | Sequential price changes for the same property may be affected by dates, events, and market changes, so they cannot automatically be treated as rigorous A/B experiments. |

### 10.2 Future Plan

#### Short Term: Verify Conditions and Conduct Operational Tests

- Confirm the client's actual property location, type, capacity, amenities, and costs to determine whether Proposal A, B, or C applies.
- Verify the address, transport access, and walking routes, and update comparable prices for the same dates and stay conditions.
- Use the recommended prices and two-night minimum stay as initial test settings.
- During the first 30 days, record exposure, views, enquiries, booked nights, cancellations, stay duration, costs, and guest feedback.
- Adjust the proposal based on actual conversion and net contribution per available night.

#### Medium Term: Improve Data and Validate Analytical Methods

- Continuously collect listing prices, actual transaction data, quotation conditions, and operating costs to build records over time.
- Use actual bookings to validate the reliability of review activity as a demand proxy.
- Investigate missing price and bedroom information and assess sample bias.
- Manually review multilingual comments to improve theme identification.
- Test the pricing model on subsequently collected data and assess whether information about renovation, photo quality, and event dates improves predictions.
- Expand sensitivity analysis to examine recommendations under different client objectives, sample thresholds, and pricing ranges.

#### Long Term: Investigate Dynamic Pricing and Operational Optimisation

- After collecting sufficient booking and cost data, investigate the relationship between price changes and booking demand.
- Design more rigorous pricing tests that account for day of the week, booking lead time, and concurrent market changes.
- Compare conversion, turnover frequency, and net contribution under different minimum-stay settings.
- Analyse long-term, luxury, and other specialised products separately rather than directly applying the current findings.
- Explore dynamic pricing and profit optimisation once sufficient demand and cost evidence is available.

**The sequence of future work is to verify property conditions, validate conversion and net contribution, improve the data and models, and then investigate dynamic pricing and operational optimisation.**

---

## 11 Appendix and Reference 

### 11.1 Appendices

#### Appendix A: Technical Validation**

**A.1 Validation-Set Performance**

| Model | MAE (AUD) | MedAE (AUD) | RMSE (AUD) | R² | Within 25% |
|---|---:|---:|---:|---:|---:|
| Log-target ridge regression | 79.36 | 52.155 | 146.039 | 0.340 | 60.5% |
| Random forest | 76.10 | 46.506 | 146.371 | 0.337 | 61.8% |
| Gradient boosting | 74.89 | 46.913 | 144.793 | 0.351 | 63.4% |

- Gradient boosting was selected because it achieved the lowest validation MAE.

**A.2 Test-Set Performance**

| Method | MAE (AUD) | MedAE (AUD) | RMSE (AUD) | R² | Within 25% |
|---|---:|---:|---:|---:|---:|
| Overall median price | 106.624 | 76.000 | 173.734 | -0.031 | 45.1% |
| Area-by-bedroom median | 84.367 | 56.500 | 143.739 | 0.294 | 56.4% |
| Selected model | 75.714 | 49.183 | 133.105 | 0.395 | 62.8% |

**A.3 Metric Definitions**

- **MAE:** Mean absolute difference between predicted and observed listing prices.
- **MedAE:** Median absolute difference between predicted and observed listing prices.
- **RMSE:** Root mean squared error, giving greater weight to large errors.
- **R²:** Predictive fit relative to a mean-price benchmark; it is not a measure of business success.
- **Within 25%:** Percentage of predictions within 25% of observed listing prices.

**A.4 Validation Checks**

- Checked property IDs for missing values and duplicates.
- Separated hosts across training, validation, and test sets.
- Fitted preprocessing within the training pipeline.
- Verified that selected scenarios met the minimum two-night comparable count.
- Verified that trial prices:
  - Fell within the comparable-price interquartile range.
  - Were multiples of AUD 10.

#### Appendix B: Data Scope and Reproducibility**

**B.1 Analysis Windows**

| Component | Period |
|---|---|
| Main city-listing snapshot | June 2026 |
| Review analysis | 17 June 2025–16 June 2026 |
| Calendar analysis | 17 June–14 September 2026 |

- Historical reviews extend beyond the review window.
- Calendar records include future dates beyond the calendar analysis window.
- Analysis windows should not be confused with the full date ranges of the source files.

**B.2 Software Environment**

| Software | Version |
|---|---|
| Python | 3.12, as recorded in the notebook metadata |
| pandas | 2.2.3 |
| NumPy | 2.3.5 |
| Matplotlib | 3.10.8 |
| scikit-learn | 1.8.0 |

**B.3 Reproduction Instructions**

- Use the same data snapshot to reproduce the reported results.
- Place the following files alongside the notebook:
  - `listings (1).csv.gz`
  - `reviews (1).csv.gz`
  - `calendar (1).csv.gz`
- The notebook also supports standard filenames such as `listings.csv.gz` or `listings.csv`.
- Files named `listings_airbnb.csv`, `reviews_airbnb.csv`, and `calendar_airbnb.csv` require renaming or an update to the file-loading function.
- Install the recorded package versions and run the notebook cells in order.
- Maps and its licence are embedded in the notebook.
- Generated figures, tables, and supporting files are saved under `analysis_outputs_v3`.
- Replacing the source snapshot may change the results and requires updating the written conclusions.

#### Appendix C: Sources and Attribution

- **Primary data:** Inside Airbnb listings, reviews, and calendar data.
- **Geographic boundaries:** Inside Airbnb Melbourne neighbourhood boundaries embedded in the notebook.
- **Data licence:** Creative Commons Attribution 4.0 International.
- **Font:** Noto Sans CJK SC subset, with the SIL Open Font License included among the embedded resources.
- **External case studies:** Used to inform analytical presentation and visualisation. Their prices, occupancy estimates, and historical findings were not incorporated into this project's results.
- The notebook's dated boundary-file URL could not be independently verified during the link check. The public Inside Airbnb data page is provided below for access to available datasets and boundaries.

### 11.2 References

1. Inside Airbnb. (n.d.). *Get the data*.  
   [https://insideairbnb.com/get-the-data/](https://insideairbnb.com/get-the-data/)

2. Inside Airbnb. (n.d.). *Data assumptions*.  
   [https://insideairbnb.com/data-assumptions/](https://insideairbnb.com/data-assumptions/)

3. Krause, A., & Aschwanden, G. (n.d.). *A census of Airbnb in Melbourne*.  
   [https://www.andykrause.com/files/krause_aschwanden_airbnb_melb.pdf](https://www.andykrause.com/files/krause_aschwanden_airbnb_melb.pdf)

4. San Francisco Chronicle. (2023). *Bay Area Airbnb words* [Interactive article].  
   [https://www.sfchronicle.com/projects/2023/bay-area-airbnb-words/](https://www.sfchronicle.com/projects/2023/bay-area-airbnb-words/)

5. Project Wondrous Raichu. (2023). *Analyzing Airbnb data: Exploratory data analysis*. Cornell University INFO 2950 course project.  
   [https://pages.github.coecis.cornell.edu/info2950-s23/project-wondrous-raichu/eda.html](https://pages.github.coecis.cornell.edu/info2950-s23/project-wondrous-raichu/eda.html)

6. Doorstep Analytics. (n.d.). *Open Airbnb datasets for Melbourne, Australia*.  
   [https://doorstepanalytics.com/report?country=Australia&location=Melbourne](https://doorstepanalytics.com/report?country=Australia&location=Melbourne)


# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: data/Data Overview for reviews.R
# Purpose: Understand reviews_airbnb.csv before we clean or analyse it
# Author: Group 4 - Renascence

# one row per guest review, with the date and the
# free-text comment. A review can only be left after a completed stay, so the number of reviews over time is the best DEMAND proxy 
# we have (Inside Airbnb assumes roughly 1 review for every 2 stays).
# ============================================================

library(data.table)
library(ggplot2)

# (Re)load if missing - or if "Data Overview for listings.R" replaced listings
# with a read.csv() data.frame, whose numeric IDs do not match the reviews
if (!exists("reviews") || !exists("listings") || !is.data.table(listings)) source("data/dataimport.R")

blue   <- "#2a78d6"
orange <- "#eb6834"

rv <- copy(reviews)

# STEP 1 - STRUCTURE

dim(rv)                        
str(rv)
head(rv[, .(listing_id, date, reviewer_name, comments = substr(comments, 1, 60))])

uniqueN(rv$listing_id)          # listings with at least one review
uniqueN(rv$reviewer_id)         # distinct guests
range(rv$date)                  # first and last review date

# STEP 2 - MISSING, DUPLICATE AND UNUSUAL VALUES

colSums(is.na(rv))
sum(duplicated(rv$id))                                  
sum(duplicated(rv, by = c("listing_id", "reviewer_id", "date")))  # same guest, same day

# Automated messages: older Inside Airbnb files contain system-generated
# "reviews" when a host cancels. They are not real guest opinions.
# (Result for this snapshot: none found - Airbnb no longer publishes them.)
rv[, auto_cancel := grepl("automated posting|The host canceled this reservation",
                          comments, ignore.case = TRUE)]
rv[, .N, by = auto_cancel]

# Comment length (characters)
rv[, n_char := nchar(comments)]
summary(rv$n_char)

# Very short comments ("Great!", ".") carry little information for text mining
rv[n_char < 10, .N]

# Rough language check: share of characters that are plain English letters.
# Many Melbourne guests write in Chinese, Korean, French etc.
rv[, mostly_ascii := !is.na(comments) &
       nchar(gsub("[^A-Za-z]", "", comments)) / pmax(n_char, 1) > 0.6]
rv[, .N, by = mostly_ascii]


# STEP 3 - REVIEWS OVER TIME (DEMAND PROXY)

rv[, year  := as.integer(format(date, "%Y"))]
rv[, month := as.integer(format(date, "%m"))]

by_year <- rv[, .N, by = year][order(year)]
by_year

monthly <- rv[, .N, by = .(ym = as.IDate(format(date, "%Y-%m-01")))][order(ym)]

ggplot(monthly, aes(ym, N)) +
  geom_line(colour = blue, linewidth = 0.6) +
  scale_y_continuous(labels = scales::comma) +
  labs(title = "Airbnb reviews per month, Melbourne",
       subtitle = "COVID collapse in 2020-21, then strong recovery; June 2026 is a partial month",
       x = NULL, y = "Reviews") +
  theme_minimal()

# Seasonality: average share of a year's reviews falling in each month
# (use complete years 2023-2025 only, so the partial 2026 does not bias it)
season <- rv[year %in% 2023:2025, .N, by = .(year, month)]
season[, share := N / sum(N), by = year]
season_avg <- season[, .(avg_share = mean(share)), by = month][order(month)]
season_avg

ggplot(season_avg, aes(factor(month.abb[month], levels = month.abb), avg_share)) +
  geom_col(fill = blue, width = 0.7) +
  scale_y_continuous(labels = scales::percent) +
  labs(title = "Seasonality of stays (share of yearly reviews by month, 2023-2025)",
       x = NULL, y = "Share of year's reviews") +
  theme_minimal()

# =============================================================================
# STEP 4 - REVIEWS PER LISTING AND LINK TO LISTINGS FILE
# =============================================================================

per_listing <- rv[, .(n_reviews = .N, last_review = max(date)), by = listing_id]
summary(per_listing$n_reviews)
quantile(per_listing$n_reviews, c(.5, .9, .99))

# Reviews whose listing is not in listings.csv (should be zero)
length(setdiff(per_listing$listing_id, listings$id))

# Listings with NO reviews at all
sum(!listings$id %in% per_listing$listing_id)

# Does our count match number_of_reviews in listings? (small gaps are normal:
# listings.csv is scraped on a slightly different day)
chk <- merge(per_listing, listings[, .(listing_id = id, number_of_reviews)],
             by = "listing_id")
cor(chk$n_reviews, chk$number_of_reviews)

# Repeat guests
guest <- rv[, .N, by = reviewer_id]
mean(guest$N > 1)               # share of guests with 2+ reviews

# =============================================================================
# KEY TAKEAWAYS (results from the 16 June 2026 snapshot)
# -----------------------------------------------------------------------------
# STRUCTURE
# 1,026,690 reviews of 21,251 listings, written by 794,203 distinct guests.
# Reviews run from 4 Aug 2010 to 28 Jun 2026 (2026 is a partial year).
#
# DATA QUALITY
# Only 41 comments are missing (0.004%) - all other columns are complete.
# No duplicate review IDs; 150 cases of the same guest reviewing the same
#  isting on the same day (likely double submissions - minor).
# No automated "host cancelled" messages in this snapshot.
# Comment length: median 146 characters, mean 201, max 5,255.
# 18,689 comments are under 10 characters ("Great!", ".") - little value
#   for text analysis.
# 36,880 comments (3.6%) are mostly non-English (Chinese, Korean, etc.).
#
# DEMAND OVER TIME (reviews = proxy for completed stays)
# Strong growth: 69,662 reviews in 2019 -> 217,035 in 2025 (3.1x).
# COVID collapse: 2020 fell 55% vs 2019 (31,126); recovery from 2022.
# Yearly: 2022 = 105,689 | 2023 = 142,080 | 2024 = 182,317 | 2025 = 217,035.
# 2026 has 114,799 reviews up to 28 June - do not compare it as a full year.
#
# SEASONALITY (average share of yearly reviews, 2023-2025)
# Peak months: Nov 10.0%, Dec 9.9%, Oct 9.3%, Mar 9.2%, Jan 8.8%.
# Quietest months: May 6.8%, Jun 7.2% (Melbourne winter).
# An even spread would be 8.3% per month, so Nov is ~20% above average
#  and May ~19% below.
#
# REVIEWS PER LISTING
# Median 17 reviews per reviewed listing; mean 48.3 (heavily skewed).
# 90th percentile 131, 99th percentile 393, maximum 3,131.
# 4,477 listings (17.4% of all listings) have never been reviewed.
# 17.6% of guests have written 2+ reviews (repeat Airbnb users).
#
# LINK TO LISTINGS FILE
# Every reviewed listing exists in listings.csv (0 orphan reviews).
# Our review counts match number_of_reviews exactly (correlation = 1.00).
#
# IMPLICATIONS FOR THE PROJECT
# Reviews are the best DEMAND measure we have: use them for trends,
#   seasonality and recent activity (reviews in the last 12 months).
# A review is not a booking: not every guest leaves one, so treat counts
#   as a relative measure, not exact occupancy.
# Before text mining: drop missing comments, comments under 10 characters
#   and non-English comments (all flagged in "Data cleaning .R").
# =============================================================================

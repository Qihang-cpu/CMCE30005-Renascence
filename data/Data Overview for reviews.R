# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: data/Data Overview for reviews.R
# Purpose: Understand reviews_airbnb.csv before we clean or analyse it
# Author: Group 4 - Renascence
#
# What this file is: one row per guest review, with the date and the
# free-text comment. A review can only be left after a completed stay, so
# the number of reviews over time is the best DEMAND proxy we have
# (Inside Airbnb assumes roughly 1 review for every 2 stays).
# ============================================================

library(data.table)
library(ggplot2)

# (Re)load if missing - or if "Data Overview for listings.R" replaced listings
# with a read.csv() data.frame, whose numeric IDs do not match the reviews
if (!exists("reviews") || !exists("listings") || !is.data.table(listings)) source("data/dataimport.R")

blue   <- "#2a78d6"
orange <- "#eb6834"

rv <- copy(reviews)

# =============================================================================
# STEP 1 - STRUCTURE
# =============================================================================

dim(rv)                         # ~1.03 million reviews, 6 columns
str(rv)
head(rv[, .(listing_id, date, reviewer_name, comments = substr(comments, 1, 60))])

uniqueN(rv$listing_id)          # listings with at least one review
uniqueN(rv$reviewer_id)         # distinct guests
range(rv$date)                  # first and last review date

# =============================================================================
# STEP 2 - MISSING, DUPLICATE AND UNUSUAL VALUES
# =============================================================================

colSums(is.na(rv))
sum(duplicated(rv$id))                                   # duplicate review IDs
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

# =============================================================================
# STEP 3 - REVIEWS OVER TIME (DEMAND PROXY)
# =============================================================================

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
# * 1,026,690 reviews of 21,251 listings by 794,203 guests (Aug 2010 - Jun 2026).
# * Only 41 comments missing; no duplicate review IDs; 150 same-guest-same-day
#   repeats; no automated cancellation notes in this snapshot.
# * Median comment = 146 characters; 18,689 comments are under 10 characters.
# * ~3.6% of comments (36,880) are mostly non-English.
# * Demand grew fast: 69.7k reviews in 2019 -> 217k in 2025 (3.1x); 2020-21
#   COVID dip. 2026 is a partial year (to 28 June).
# * Seasonality (2023-25): busiest Oct-Dec (9.3-10.0% of the year each) and
#   Jan/Mar; quietest May-Jun (6.8-7.2%).
# * Median listing has 17 reviews (90th pct 131, max 3,131). 4,477 listings
#   (17%) have never been reviewed. 17.6% of guests reviewed 2+ times.
# * All reviewed listings exist in listings.csv; our counts match
#   number_of_reviews exactly (r = 1.00).
# * Use: demand over time, seasonality, recency of bookings per listing,
#   and free-text themes (cleanliness, location, host communication ...).
# * Before text analysis: drop NA comments, automated cancellation notes,
#   very short comments, and (if using English dictionaries) non-English text.
# =============================================================================

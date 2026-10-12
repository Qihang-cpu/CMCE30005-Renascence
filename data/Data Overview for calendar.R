# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: data/Data Overview for calendar.R
# Purpose: Understand calendar_airbnb.csv before we clean or analyse it
# Author: Group 4 - Renascence
#
# IMPORTANT LIMITATION: "not available" mixes two things we cannot separate:
#   (a) the night is BOOKED, and 
#   (b) the host BLOCKED the night.
# So availability is a rough demand signal, not a clean occupancy rate.
# This file has NO price column.
# ============================================================

library(data.table)
library(ggplot2)

if (!exists("calendar") || !exists("listings") || !is.data.table(listings)) source("data/dataimport.R")

blue   <- "#2a78d6"
orange <- "#eb6834"
red    <- "#e34948"

cal <- copy(calendar)


# STEP 1 - STRUCTURE


dim(cal)                      
str(cal)
head(cal)

uniqueN(cal$listing_id)       
range(cal$date)                

# Every listing should have one row per day - check how many days each has
days_per_listing <- cal[, .N, by = listing_id]
summary(days_per_listing$N)
table(days_per_listing$N)

# Any duplicate listing-day rows?
sum(duplicated(cal, by = c("listing_id", "date")))


# STEP 2 - MISSING AND INVALID VALUES

colSums(is.na(cal))
table(cal$available, useNA = "ifany")   # should only be "t" / "f"

# Convert t/f text to TRUE/FALSE so we can take averages
cal[, available := available == "t"]

summary(cal$minimum_nights)
summary(cal$maximum_nights)

# Extreme rules: minimum stay over 365 nights is a lease, not a short stay
cal[minimum_nights > 365, uniqueN(listing_id)]
# maximum_nights of 1125 / 9999+ are Airbnb defaults ("no limit")
cal[, .N, by = .(max_is_default = maximum_nights >= 1125)]


# STEP 3 - HOW AVAILABLE ARE LISTINGS?


# Overall share of listing-nights that are available
cal[, mean(available)]

# One row per listing: share of the next 365 days that is available
listing_avail <- cal[, .(
  days         = .N,
  avail_rate   = mean(available),
  avail_30     = mean(available[date <  min(date) + 30]),
  min_nights   = median(minimum_nights)
), by = listing_id]

summary(listing_avail$avail_rate)

# Listings that are never available (fully booked OR switched off by host)
listing_avail[avail_rate == 0, .N]
# Listings available every single night (no bookings at all on the calendar)
listing_avail[avail_rate == 1, .N]

ggplot(listing_avail, aes(avail_rate)) +
  geom_histogram(bins = 40, fill = blue, colour = "white") +
  scale_x_continuous(labels = scales::percent) +
  labs(title = "Share of the next 12 months each listing is open for booking",
       subtitle = "Peaks at 0% (never open) and 100% (no bookings yet) need care",
       x = "Nights available (%)", y = "Number of listings") +
  theme_minimal()


# STEP 4 - AVAILABILITY OVER TIME


daily <- cal[, .(share_available = mean(available), n = .N), by = date]
setorder(daily, date)

ggplot(daily, aes(date, share_available)) +
  geom_line(colour = blue, linewidth = 0.6) +
  scale_y_continuous(labels = scales::percent) +
  labs(title = "Share of Melbourne listings available, by night",
       subtitle = "Falls for far-off months: many hosts close distant dates, so this is not pure demand",
       x = NULL, y = "Listings available") +
  theme_minimal()

# Weekday vs weekend nights (Fri/Sat nights should book first)
cal[, weekday := weekdays(date)]
cal[, .(share_available = round(mean(available), 3)), by = weekday][order(share_available)]

# By month of stay
cal[, month := format(date, "%Y-%m")]
cal[, .(share_available = round(mean(available), 3)), by = month][order(month)]


# STEP 5 - DOES THE CALENDAR MATCH THE LISTINGS FILE?


# Listings in calendar but not in listings (and the reverse)
length(setdiff(unique(cal$listing_id), listings$id))
length(setdiff(listings$id, unique(cal$listing_id)))

# Sanity check: our 365-day count vs the availability_365 column in listings
check <- merge(listing_avail[, .(id = listing_id, avail_days = round(avail_rate * days))],
               listings[, .(id, availability_365)], by = "id")
cor(check$avail_days, check$availability_365, use = "complete.obs")

# =============================================================================
# KEY TAKEAWAYS:
# * 25,728 listings x 365 days = 9.39 m rows 
#   No missing values, no duplicate listing-days, every listing has 365 days.
# * Every calendar listing is in listings.csv and vice versa (perfect match);
#   our 365-day count matches availability_365
# * 45.5% of all listing-nights are available.
# * 6,117 listings (23.8%) are NEVER available -> fully booked or switched off.
#   676 listings (2.6%) are available every night -> no bookings at all.
#   Flag both groups before any demand analysis.
# * Fri/Sat nights are slightly less available (44.4%) than Tue (46.5%).
# * Availability FALLS for far-off months (Aug-26 57% -> Jun-27 31%) because
#   hosts close distant dates - "not available" is not the same as "booked".
# * minimum_nights: median 2; 16 listings have rules over 365 nights.
#   maximum_nights uses 1125 / 99999 as "no limit" placeholders.
# * No price in this file -> nightly price must come from listings.csv.
# =============================================================================

# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: Analysis Process/Descriptive Analysis.R
# Purpose: WHAT is happening? - describe the market for our business problem
# Author: Group 4 - Renascence
#
# STATUS: SKELETON - business problem not decided yet.
#         Fill in once the group agrees on the problem (see README.md).
#
# INPUT   data/processed/listings_master.rds  (run "data/Data cleaning .R")
# ============================================================

library(data.table)
library(ggplot2)
library(scales)

if (!file.exists("data/processed/listings_master.rds")) source("data/Data cleaning .R")
lm_all <- readRDS("data/processed/listings_master.rds")
bk     <- lm_all[bookable == TRUE]   # bookable listings with a price

# -----------------------------------------------------------------------------
# CANDIDATE BUSINESS PROBLEMS (client = investor listing several properties)
# -----------------------------------------------------------------------------
# A. WHERE and WHAT to list
#    "Which LGA x property type gives the best revenue potential?"
#    Descriptive: price, estimated occupancy and revenue by LGA x room type.
#
# B. ACTIVE vs DORMANT listings
#    "What separates listings that get booked from those that don't?"
#    Descriptive: compare active_ltm = TRUE / FALSE on price, amenities,
#    minimum nights, room type, host type, location.
#
# C. PRICING a new listing
#    "What drives nightly price, and what should the client charge?"
#    Descriptive: price by room type, capacity, LGA, amenities, season.
# -----------------------------------------------------------------------------

# Useful starting table for any of A / B / C: market by LGA x room type
market <- bk[room_type %in% c("Entire home/apt", "Private room"), .(
  listings         = .N,
  median_price     = median(price),
  median_occupancy = median(estimated_occupancy_l365d, na.rm = TRUE),
  median_revenue   = median(estimated_revenue_l365d, na.rm = TRUE),
  active_rate      = mean(active_ltm)
), by = .(lga, room_type)][order(-median_revenue)]
market

# TODO: descriptive analysis for the chosen problem

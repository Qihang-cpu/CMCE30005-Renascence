# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: Analysis Process/Predictive Analysis.R
# Purpose: WHAT WILL happen? - model the outcome behind our business problem
# Author: Group 4 - Renascence
#
# STATUS: SKELETON - business problem not decided yet.
#
# INPUT   data/processed/listings_master.rds  (run "data/Data cleaning .R")
# ============================================================

library(data.table)

if (!file.exists("data/processed/listings_master.rds")) source("data/Data cleaning .R")
lm_all <- readRDS("data/processed/listings_master.rds")

# -----------------------------------------------------------------------------
# POSSIBLE TARGET VARIABLE, depending on the problem chosen (see README.md)
#   A. Revenue potential -> estimated_revenue_l365d (regression)
#   B. Active vs dormant -> active_ltm (classification: logistic regression,
#                           random forest)
#   C. Pricing           -> log_price (regression)
#
# MODELLING RULES TO REMEMBER
#   * Use bookable listings only (bookable == TRUE) - others have no price.
#   * Avoid LEAKAGE: do not use variables that are a result of the outcome
#     (e.g. for target B do not use number_of_reviews, review scores,
#     availability or estimated occupancy as predictors).
#   * Split train/test (e.g. 70/30, set.seed(2026)) or cross-validate,
#     grouping by host_id so one host's listings are not in both sets.
#   * Compare against a simple baseline (e.g. median by LGA x room type).
# -----------------------------------------------------------------------------

# Candidate predictors that are known BEFORE a listing goes live
predictors <- c("room_type", "property_group", "lga", "dist_cbd_km",
                "accommodates", "bedrooms", "bathrooms", "bath_shared",
                "n_amenities", "has_wifi", "has_kitchen", "has_aircon",
                "has_washer", "has_free_parking", "has_pool", "has_workspace",
                "has_self_checkin", "pets_allowed", "minimum_nights",
                "host_type", "host_identity_verified")

# TODO: build model for the chosen target

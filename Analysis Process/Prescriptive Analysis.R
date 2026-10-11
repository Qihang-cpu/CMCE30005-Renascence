# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: Analysis Process/Prescriptive Analysis.R
# Purpose: WHAT SHOULD the client do? - turn the model into recommendations
# Author: Group 4 - Renascence
#
# STATUS: SKELETON - business problem not decided yet.
#
# INPUT   data/processed/listings_master.rds + results of Predictive Analysis.R
# ============================================================

library(data.table)

if (!file.exists("data/processed/listings_master.rds")) source("data/Data cleaning .R")
lm_all <- readRDS("data/processed/listings_master.rds")

# -----------------------------------------------------------------------------
# IDEAS, depending on the problem chosen (see README.md)
#   A. Where/what to list -> rank LGA x property type by expected revenue,
#      adjusted for risk (spread of revenue) and competition (listing count);
#      recommend a portfolio for a given budget.
#   B. Active vs dormant -> "listing checklist": which changes (amenities,
#      minimum nights, price for size) raise the predicted chance of bookings.
#   C. Pricing -> recommended nightly price range for a new listing, with
#      seasonal uplift for Oct-Dec and March (peak months in the EDA).
# -----------------------------------------------------------------------------

# TODO: recommendations for the chosen problem

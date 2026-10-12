# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: data/dataimport.R
# Purpose: Read the three Inside Airbnb files into R
# Author: Group 4 - Renascence
# ============================================================

library(data.table)

data_dir <- "data"

id_cols_listings <- c("id", "scrape_id", "host_id")
id_cols_calendar <- c("listing_id")
id_cols_reviews  <- c("listing_id", "id", "reviewer_id")

stopifnot(
  "CSV files not found - put them in the data/ folder and open the .Rproj" =
    file.exists(file.path(data_dir, c("listings_airbnb.csv",
                                      "calendar_airbnb.csv",
                                      "reviews_airbnb.csv")))
)

listings <- fread(file.path(data_dir, "listings_airbnb.csv"),
                  colClasses = list(character = id_cols_listings),
                  na.strings = c("", "NA"), encoding = "UTF-8")

calendar <- fread(file.path(data_dir, "calendar_airbnb.csv"),
                  colClasses = list(character = id_cols_calendar),
                  na.strings = c("", "NA"))

reviews  <- fread(file.path(data_dir, "reviews_airbnb.csv"),
                  colClasses = list(character = id_cols_reviews),
                  na.strings = c("", "NA"), encoding = "UTF-8")

# Quick check: rows x columns of each table
sapply(list(listings = listings, calendar = calendar, reviews = reviews), dim)

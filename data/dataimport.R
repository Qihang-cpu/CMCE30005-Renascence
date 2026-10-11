# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: data/dataimport.R
# Purpose: Read the three Inside Airbnb files into R
# Author: Group 4 - Renascence
#
# BEFORE RUNNING
#   1. Open CMCE30005-Renascence.Rproj in RStudio (this sets the working
#      directory to the project folder, so the relative paths below work).
#   2. Put the three CSV files inside the data/ folder:
#        data/listings_airbnb.csv   (~72 MB,  25,728 rows)
#        data/calendar_airbnb.csv   (~378 MB, 9,390,720 rows)
#        data/reviews_airbnb.csv    (~279 MB, 1,026,690 rows)
#      The CSVs are listed in .gitignore, so they are never pushed to GitHub.
#
# WHY fread() AND NOT read.csv()
#   data.table::fread() reads the 378 MB calendar in ~3 seconds; read.csv()
#   takes minutes. fread() returns a data.table, which also works with dplyr.
#
# WHY READ THE ID COLUMNS AS TEXT
#   Newer Airbnb IDs have 18-19 digits. Stored as numbers they lose precision
#   (two different listings can end up with the same ID), so joins between
#   the three files would silently break. Text keeps every digit.
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

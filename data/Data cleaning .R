# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: data/Data cleaning .R
# Purpose: Turn the three raw CSV files into clean, analysis-ready tables
# Author: Group 4 - Renascence

# INPUT   data/listings_airbnb.csv, calendar_airbnb.csv, reviews_airbnb.csv
# OUTPUT  data/processed/   (ignored by git - re-create by running this file)
#           listings_clean.rds    one row per listing, cleaned + new features
#           calendar_listing.rds  one row per listing, availability summary
#           calendar_daily.rds    one row per night, market availability
#           reviews_clean.rds     one row per review, cleaned text
#           reviews_listing.rds   one row per listing, review/demand summary
#           listings_master.rds   listings_clean + calendar + review summaries
#         outputs/cleaning_log.txt  every rule and how many records it changed

# PRINCIPLES (same as "Data Overview for listings.R")
#   * ERROR (impossible value)  -> set the cell to NA, keep the row
#   * OUT OF SCOPE (not a short-stay listing) -> remove the row
#   * OUTLIER (surprising but possible) -> keep it and FLAG it
#   * Every rule is logged with the number of records it affected.

# The business problem is not fixed yet, so this file keeps everything that
# could be useful and only removes what is clearly wrong. Analysis scripts
# filter further for their own question.
# ============================================================

library(data.table)

# (Re)load if missing - or if "Data Overview for listings.R" replaced listings
# with a read.csv() data.frame (numeric IDs lose precision)
if (!exists("listings") || !exists("calendar") || !exists("reviews") ||
    !is.data.table(listings) || !is.character(listings$id)) {
  source("data/dataimport.R")
}

dir.create("data/processed", showWarnings = FALSE, recursive = TRUE)
dir.create("outputs",        showWarnings = FALSE, recursive = TRUE)

snapshot_date <- as.IDate("2026-06-16")   # Inside Airbnb scrape date

# Small helper to record each cleaning rule
cleaning_log <- data.table(table = character(), step = character(), records = integer())
log_step <- function(table, step, records) {
  cleaning_log <<- rbind(cleaning_log,
                         data.table(table = table, step = step, records = as.integer(records)))
}

# =============================================================================
# PART A - LISTINGS
# =============================================================================

li <- copy(listings)
log_step("listings", "Raw rows", nrow(li))

# --- A1. Drop columns that are 100% empty in this snapshot -------------------
empty_cols <- names(li)[vapply(li, function(x) all(is.na(x)), logical(1))]
empty_cols     # e.g. host_since, host_response_rate, license, instant_bookable
li[, (empty_cols) := NULL]
log_step("listings", paste("Columns dropped - 100% empty:", length(empty_cols)), 0)

# --- A2. Drop columns with no analytical value -------------------------------
# URLs/images, scrape bookkeeping, and the raw price-quote JSON
useless_cols <- intersect(c("listing_url", "scrape_id", "picture_url", "host_url",
                            "host_profile_id", "host_profile_url", "host_picture_url",
                            "price_quote_raw", "host_verifications"),
                          names(li))
li[, (useless_cols) := NULL]
log_step("listings", paste("Columns dropped - no analytical value:", length(useless_cols)), 0)

# --- A3. Fix data types --------------------------------------------------------
# Price: "$1,250.00" -> 1250
li[, price := as.numeric(gsub("[$,]", "", price))]

# t/f text -> TRUE/FALSE
tf_cols <- intersect(c("host_is_superhost", "host_has_profile_pic",
                       "host_identity_verified", "has_availability"), names(li))
for (col in tf_cols) set(li, j = col, value = li[[col]] == "t")

# Dates
date_cols <- intersect(c("last_scraped", "calendar_last_scraped",
                         "first_review", "last_review"), names(li))
for (col in date_cols) set(li, j = col, value = as.IDate(li[[col]]))

# Categories
li[, room_type := factor(room_type, levels = c("Entire home/apt", "Private room",
                                               "Shared room", "Hotel room"))]
li[, lga := factor(neighbourhood_cleansed)]   # 30 Local Government Areas

# --- A4. Fill missing bathrooms from the bathrooms_text column ----------------
# bathrooms is 32% missing but bathrooms_text ("1.5 baths", "Half-bath") is not
n_before <- sum(is.na(li$bathrooms))
li[, bath_from_text := suppressWarnings(as.numeric(sub("^([0-9.]+).*", "\\1", bathrooms_text)))]
li[is.na(bath_from_text) & grepl("half", bathrooms_text, ignore.case = TRUE), bath_from_text := 0.5]
li[is.na(bathrooms), bathrooms := bath_from_text]
li[, bath_shared := grepl("shared", bathrooms_text, ignore.case = TRUE)]
li[, bath_from_text := NULL]
log_step("listings", "bathrooms filled from bathrooms_text", n_before - sum(is.na(li$bathrooms)))

# --- A5. ERRORS -> set to NA ---------------------------------------------------
# Prices under $20 a night are not credible in Melbourne
n <- li[!is.na(price) & price < 20, .N]
li[!is.na(price) & price < 20, price := NA]
log_step("listings", "price < $20 set to NA", n)

# maximum_nights of 1125 or more is Airbnb's 'no limit' placeholder
n <- li[maximum_nights >= 1125, .N]
li[maximum_nights >= 1125, maximum_nights := NA]
log_step("listings", "maximum_nights >= 1125 (placeholder) set to NA", n)

# 0 bedrooms is valid (studio); beds = 0 with accommodates > 0 is an error
n <- li[!is.na(beds) & beds == 0, .N]
li[!is.na(beds) & beds == 0, beds := NA]
log_step("listings", "beds = 0 set to NA", n)

# --- A6. OUT OF SCOPE -> remove rows ------------------------------------------
# A minimum stay over 365 nights is a residential lease, not short-stay
n <- li[!is.na(minimum_nights) & minimum_nights > 365, .N]
li <- li[is.na(minimum_nights) | minimum_nights <= 365]
log_step("listings", "Rows removed - minimum_nights > 365", n)

# --- A7. FLAGS (keep the rows, mark them) -------------------------------------
# Price outlier: above Q3 + 1.5 x IQR
q <- quantile(li$price, c(.25, .75), na.rm = TRUE)
price_fence <- q[2] + 1.5 * diff(q)
li[, price_outlier := !is.na(price) & price > price_fence]
log_step("listings", sprintf("Flag price_outlier (price > $%.0f)", price_fence), sum(li$price_outlier))

# Has a price = currently bookable. Most 'previous scrape' listings have no
# price: they were not bookable on the scrape date.
li[, has_price := !is.na(price)]
li[, city_scrape := source == "city scrape"]
li[, bookable := has_price & city_scrape]
log_step("listings", "Flag bookable (city scrape AND has price)", sum(li$bookable))

li[, long_stay_only   := minimum_nights > 30]
li[, never_reviewed   := number_of_reviews == 0]
li[, always_available := availability_365 == 365]
li[, never_available  := availability_365 == 0]
log_step("listings", "Flag long_stay_only (min nights > 30)", sum(li$long_stay_only, na.rm = TRUE))
log_step("listings", "Flag never_reviewed",                   sum(li$never_reviewed))

# Active = at least one review in the last 12 months (a stay happened)
li[, active_ltm := number_of_reviews_ltm >= 1]
log_step("listings", "Flag active_ltm (>= 1 review in last 12 months)", sum(li$active_ltm))

# --- A8. FEATURE ENGINEERING --------------------------------------------------
# Amenities come as a JSON-style list: ["Wifi", "Kitchen", ...] -> count items
li[, n_amenities := lengths(regmatches(amenities, gregexpr('"[^"]+"', amenities)))]

# Each pattern matches a whole amenity item (starting right after its opening
# quote), so "Dishwasher" does not count as a washer and "Pool table" or
# "Pool view" do not count as a pool.
amenity_flags <- c(has_wifi         = '"(Fast )?[Ww]ifi',
                   has_kitchen      = '"Kitchen"',
                   has_aircon       = '"(Central |Portable )?[Aa]ir conditioning|"AC - ',
                   has_heating      = '"[^"]*[Hh]eating',
                   has_washer       = '"(Free |Paid )?[Ww]asher',
                   has_free_parking = '"Free (parking|street parking)',
                   has_pool         = '"(Shared |Private )?((indoor|outdoor|rooftop) )?[Pp]ool( -[^"]*)?"',
                   has_workspace    = '"Dedicated workspace',
                   has_self_checkin = '"Self check-in"',
                   pets_allowed     = '"Pets allowed"')
for (flag in names(amenity_flags)) {
  set(li, j = flag, value = grepl(amenity_flags[[flag]], li$amenities))
}

li[, price_per_person  := round(price / accommodates, 2)]
li[, price_per_bedroom := round(price / pmax(bedrooms, 1), 2)]
li[, log_price         := log(price)]

# Host features
li[, host_listings := calculated_host_listings_count]
li[, host_type := factor(fcase(host_listings == 1,  "Single listing",
                               host_listings <= 5,  "2-5 listings",
                               host_listings <= 20, "6-20 listings",
                               default = "21+ listings (commercial)"),
                         levels = c("Single listing", "2-5 listings",
                                    "6-20 listings", "21+ listings (commercial)"))]

# Property group: simplify 60+ property types
li[, property_group := fcase(
  grepl("^Entire (rental unit|condo|serviced apartment|loft)", property_type), "Apartment",
  grepl("^Entire (home|townhouse|villa|cottage|bungalow|cabin|vacation home)", property_type), "House",
  grepl("^Entire", property_type), "Other entire",
  grepl("^Private room", property_type), "Private room",
  default = "Other")]

# Review score bands
li[, rating_band := cut(review_scores_rating, c(0, 4.5, 4.7, 4.85, 5.0001),
                        labels = c("< 4.50", "4.50-4.69", "4.70-4.84", "4.85+"),
                        right = FALSE)]

# Distance to Melbourne CBD (Flinders St Station), in km - haversine formula
cbd <- c(lat = -37.8183, lon = 144.9671)
to_rad <- pi / 180
li[, dist_cbd_km := round(6371 * 2 * asin(sqrt(
  sin((latitude - cbd["lat"]) * to_rad / 2)^2 +
  cos(cbd["lat"] * to_rad) * cos(latitude * to_rad) *
  sin((longitude - cbd["lon"]) * to_rad / 2)^2)), 2)]

log_step("listings", "Clean rows", nrow(li))

# =============================================================================
# PART B - CALENDAR
# =============================================================================

cal <- calendar[, .(listing_id, date, available = available == "t",
                    minimum_nights, maximum_nights)]
log_step("calendar", "Raw rows", nrow(cal))

# Keep only listings that survived listings cleaning
n <- cal[!listing_id %in% li$id, .N]
cal <- cal[listing_id %in% li$id]
log_step("calendar", "Rows removed - listing dropped in listings cleaning", n)

# Placeholder maximum_nights -> NA (same rule as listings)
cal[maximum_nights >= 1125, maximum_nights := NA]

# One row per listing
start <- min(cal$date)
cal[, month := as.integer(format(date, "%m"))]
cal[, weekend := weekdays(date) %in% c("Friday", "Saturday")]

calendar_listing <- cal[, .(
  avail_rate_30     = mean(available[date <  start + 30]),
  avail_rate_90     = mean(available[date <  start + 90]),
  avail_rate_365    = mean(available),
  avail_rate_summer = mean(available[month %in% c(12, 1, 2)]),
  avail_rate_wkend  = mean(available[weekend]),
  cal_min_nights    = as.numeric(median(minimum_nights))
), by = listing_id]

# One row per night: share of all listings available
calendar_daily <- cal[, .(share_available = mean(available), listings = .N), by = date]
setorder(calendar_daily, date)

log_step("calendar", "Listings summarised", nrow(calendar_listing))

# =============================================================================
# PART C - REVIEWS
# =============================================================================

rv <- copy(reviews)
log_step("reviews", "Raw rows", nrow(rv))

n <- rv[is.na(comments) | trimws(comments) == "", .N]
rv <- rv[!is.na(comments) & trimws(comments) != ""]
log_step("reviews", "Rows removed - empty comment", n)

n <- sum(duplicated(rv$id))
rv <- unique(rv, by = "id")
log_step("reviews", "Rows removed - duplicate review id", n)

n <- rv[!listing_id %in% li$id, .N]
rv <- rv[listing_id %in% li$id]
log_step("reviews", "Rows removed - listing dropped in listings cleaning", n)

# Clean the text: remove HTML line breaks and extra spaces
rv[, comments := gsub("<br\\s*/?>", " ", comments)]
rv[, comments := gsub("\\s+", " ", trimws(comments))]

rv[, n_char       := nchar(comments)]
rv[, short_review := n_char < 10]
rv[, english      := nchar(gsub("[^A-Za-z]", "", comments)) / pmax(n_char, 1) > 0.6]
rv[, year         := as.integer(format(date, "%Y"))]
log_step("reviews", "Flag short_review (< 10 characters)", sum(rv$short_review))
log_step("reviews", "Flag non-English (mostly non-Latin letters)", sum(!rv$english))

# One row per listing
reviews_listing <- rv[, .(
  rv_total        = .N,
  rv_last_12m     = sum(date >  snapshot_date - 365),
  rv_prev_12m     = sum(date <= snapshot_date - 365 & date > snapshot_date - 730),
  rv_first_date   = min(date),
  rv_last_date    = max(date),
  rv_mean_chars   = round(mean(n_char))
), by = listing_id]
reviews_listing[, days_since_last_review := as.integer(snapshot_date - rv_last_date)]
reviews_listing[, rv_growth := rv_last_12m - rv_prev_12m]

log_step("reviews", "Clean rows", nrow(rv))

# =============================================================================
# PART D - MASTER TABLE (one row per listing, everything joined)
# =============================================================================

listings_master <- merge(li, calendar_listing, by.x = "id", by.y = "listing_id", all.x = TRUE)
listings_master <- merge(listings_master, reviews_listing, by.x = "id", by.y = "listing_id", all.x = TRUE)
listings_master[is.na(rv_total), `:=`(rv_total = 0L, rv_last_12m = 0L, rv_prev_12m = 0L)]

stopifnot(nrow(listings_master) == nrow(li), !anyDuplicated(listings_master$id))

# =============================================================================
# SAVE
# =============================================================================

saveRDS(li,               "data/processed/listings_clean.rds")
saveRDS(calendar_listing, "data/processed/calendar_listing.rds")
saveRDS(calendar_daily,   "data/processed/calendar_daily.rds")
saveRDS(rv,               "data/processed/reviews_clean.rds")
saveRDS(reviews_listing,  "data/processed/reviews_listing.rds")
saveRDS(listings_master,  "data/processed/listings_master.rds")

print(cleaning_log)
writeLines(c("Cleaning log - generated by data/Data cleaning .R",
             paste("Run on:", Sys.Date()), "",
             capture.output(print(as.data.frame(cleaning_log), row.names = FALSE, right = FALSE))),
           "outputs/cleaning_log.txt")

rm(cal, rv)   # free memory
invisible(gc())

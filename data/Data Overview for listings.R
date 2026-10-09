library(dplyr)

# A consistent colour set for every plot in this script
blue   <- "#2a78d6"   # main colour for single-series plots
orange <- "#eb6834"   # second, contrasting category
grey   <- "#d8d8d4"   # background / "nothing to see here"
red    <- "#e34948"   # errors and things to worry about

# 1. Read your data
listings <- read.csv("~/Downloads/listings_airbnb.csv", stringsAsFactors = FALSE, na.strings = c("NA", ""))

# rows, then columns
dim(listings)          
# rows only
nrow(listings)        
# columns only
ncol(listings)    
# Examine the structure of every variable
glimpse(listings)

# --- 1a. Which variables contain only NA values? -----------------------------
all_missing <- sapply(listings, function(x) all(is.na(x)))
names(listings)[all_missing]
sum(all_missing)

# --- A column that is empty but does not LOOK empty --------------------------
table(listings$host_verifications, useNA = "ifany")

missing_pct <- colMeans(is.na(listings)) * 100
missing_pct <- round(sort(missing_pct, decreasing = TRUE), 1)

head(missing_pct, 25)


# --- Visualisation 1: how much is missing, by variable -----------------------

to_plot <- missing_pct[missing_pct > 0]     # only columns with missing data
par(mar = c(4, 14, 3, 2))                   # wide left margin for long names
barplot(
  rev(to_plot),                             # rev() puts the worst at the top
  horiz = TRUE, las = 1, col = blue, border = NA,
  xlim = c(0, 100), xlab = "Percentage of values missing",
  main = "How much is missing, variable by variable",
  cex.names = 0.7
)
abline(v = 50, col = red, lwd = 2, lty = 2) # our 50% drop threshold
text(50, 1, " 50% threshold", col = red, adj = 0, cex = 0.8)

# --- Drop columns that are more than 50% missing -----------------------------
columns_to_drop <- names(missing_pct)[missing_pct > 50]
length(columns_to_drop)

listings_reduced <- listings[, !(names(listings) %in% columns_to_drop)]
dim(listings_reduced)

# Also remove host_verifications - not missing, but the same value every row
listings_reduced <- listings_reduced[, names(listings_reduced) != "host_verifications"]
dim(listings_reduced)
listings_cleaned <- listings_reduced

# --- 3a. Text to numeric: price ----------------------------------------------
head(listings_cleaned$price, 4)      # before
class(listings_cleaned$price)
listings_cleaned$price <- as.numeric(gsub("[$,]", "", listings_cleaned$price))
head(listings_cleaned$price, 4)      # after
class(listings_cleaned$price)
sum(is.na(listings_reduced$price))   # missing before
sum(is.na(listings_cleaned$price))              # missing after - should be the same
summary(listings_cleaned$price)

# --- 3b. Text to date --------------------------------------------------------

# as.Date() needs the layout of the text.
# %Y = four-digit year, %m = two-digit month, %d = two-digit day

date_columns <- c("last_scraped", "calendar_last_scraped",
                  "first_review", "last_review")

for (column in date_columns) {
  listings_cleaned[[column]] <- as.Date(listings_cleaned[[column]], format = "%Y-%m-%d")
}

sapply(listings_cleaned[date_columns], class)
summary(listings_cleaned$first_review)

# Now dates behave like dates - you can do arithmetic with them
head(listings_cleaned$last_review - listings_cleaned$first_review, 5)



# --- 3c. Text to factor ------------------------------------------------------

# Categorical variables with a small, fixed set of values are best stored as
# FACTORS, so table(), plots and models treat them as categories.

listings_cleaned$room_type              <- factor(listings_cleaned$room_type)
listings_cleaned$neighbourhood_cleansed <- factor(listings_cleaned$neighbourhood_cleansed)
listings_cleaned$source                 <- factor(listings_cleaned$source)

levels(listings_cleaned$room_type)
table(listings_cleaned$room_type)



# =============================================================================
# STEP 4 - IDENTIFY AND MANAGE EXTREME VALUES
# =============================================================================

key_numeric <- c("price", "accommodates", "bedrooms", "beds", "bathrooms",
                 "minimum_nights", "maximum_nights", "availability_365",
                 "number_of_reviews", "reviews_per_month",
                 "review_scores_rating", "estimated_revenue_l365d")

summary(listings_cleaned[key_numeric])



# --- A reusable outlier summary ----------------------------------------------

# The standard rule of thumb flags a value as an outlier if it sits more than
# 1.5 x IQR beyond the quartiles (IQR = interquartile range).

outlier_summary <- function(x) {
  x   <- x[!is.na(x)]
  q1  <- quantile(x, 0.25)
  q3  <- quantile(x, 0.75)
  iqr <- q3 - q1
  lower <- q1 - 1.5 * iqr
  upper <- q3 + 1.5 * iqr
  data.frame(
    min          = round(min(x), 2),
    median       = round(median(x), 2),
    max          = round(max(x), 2),
    lower_fence  = round(lower, 2),
    upper_fence  = round(upper, 2),
    n_outliers   = sum(x < lower | x > upper),
    pct_outliers = round(100 * mean(x < lower | x > upper), 1)
  )
}

# lapply() runs the function on each column; do.call(rbind, ...) stacks the
# one-row results into a table.
do.call(rbind, lapply(listings_cleaned[key_numeric], outlier_summary))



# --- Visualising the extremes ------------------------------------------------

par(mar = c(4, 5, 3, 2), mfrow = c(2, 2))

boxplot(listings_cleaned$price, horizontal = TRUE, col = blue, border = "black",
        main = "Price per night (AUD)", xlab = "")
boxplot(listings_cleaned$price, horizontal = TRUE, col = blue, border = "black",
        log = "x", main = "Price per night (log scale)", xlab = "")
boxplot(listings_cleaned$minimum_nights, horizontal = TRUE, col = blue, border = "black",
        main = "Minimum nights", xlab = "")
boxplot(listings_cleaned$maximum_nights, horizontal = TRUE, col = blue, border = "black",
        main = "Maximum nights", xlab = "")
par(mfrow = c(1, 1))


# The first two panels show the SAME variable. On the raw scale one $23,000
# listing squashes every real price into a single line at the left edge - the
# plot tells you nothing. On a LOG SCALE the distribution becomes readable.
# When a variable spans several orders of magnitude, plot it on a log scale
# before deciding anything.

par(mar = c(4, 4, 3, 2))
hist(listings_cleaned$price[listings_cleaned$price < 1000], breaks = 50, col = blue, border = "white",
     main = "Distribution of nightly price (under $1,000)",
     xlab = "Price per night (AUD)", ylab = "Number of listings")
abline(v = median(listings_cleaned$price, na.rm = TRUE), col = orange, lwd = 3)
abline(v = mean(listings_cleaned$price,   na.rm = TRUE), col = red,    lwd = 3, lty = 2)
legend("topright", legend = c("Median", "Mean"), col = c(orange, red),
       lwd = 3, lty = c(1, 2), bty = "n")


# --- 4a. Remove values that are CLEARLY ERRORS -------------------------------

# The key distinction:
#   an ERROR   is a value that CANNOT be true      -> remove
#   an OUTLIER is surprising but POSSIBLE          -> flag

n_before <- nrow(listings_cleaned)
listings_cleaned[listings_cleaned$minimum_nights > 365 & !is.na(listings_cleaned$minimum_nights),
      c("name", "minimum_nights", "maximum_nights", "price")]
table(listings_cleaned$maximum_nights[listings_cleaned$maximum_nights > 1125])
listings_cleaned[listings_cleaned$price < 20 & !is.na(listings_cleaned$price),
      c("name", "room_type", "accommodates", "price")]
n_before - nrow(listings_cleaned)

# 1. maximum_nights of 9999 is a placeholder, not a measurement -> set to NA
listings_cleaned$maximum_nights <- ifelse(listings_cleaned$maximum_nights >= 9999, NA, listings_cleaned$maximum_nights)

# 2. A "minimum stay" over 365 nights is not a short-stay listing -> remove row
listings_cleaned <- listings_cleaned[is.na(listings_cleaned$minimum_nights) | listings_cleaned$minimum_nights <= 365, ]

# 3. Prices under $20 a night are not credible in this market -> set price NA
# (keep the row - everything else about the listing is still valid)
listings_cleaned$price <- ifelse(listings_cleaned$price < 20, NA, listings_cleaned$price)
n_before - nrow(listings_cleaned)              # rows removed
sum(is.na(listings_cleaned$maximum_nights))


# NOTICE THE THREE DIFFERENT RESPONSES. They are chosen deliberately:
#
#   SET THE CELL TO NA when one value is wrong but the rest of the row is fine
#   (maximum_nights, price). Deleting the whole listing would throw away good
#   data about room type, location and reviews.
#
#   DELETE THE ROW when the record does not belong in the dataset at all. A
#   400-night minimum stay is a residential lease, not a short-stay listing -
#   it is out of scope, not mis-recorded.
#
#   NEVER SILENTLY OVERWRITE a value with a guess. Every rule above is stated,
#   counted and justified. Document each rule and how many records it affected:


# --- 4b. Flag the remaining outliers -----------------------------------------

# The extreme prices that survive are probably real: penthouses, event-week
# pricing, or hosts pricing high to block bookings without delisting. We do not
# know, so we DO NOT DELETE them - we mark them.

q1 <- quantile(listings_cleaned$price, 0.25, na.rm = TRUE)
q3 <- quantile(listings_cleaned$price, 0.75, na.rm = TRUE)
upper_fence <- q3 + 1.5 * (q3 - q1)
upper_fence
listings_cleaned$price_outlier <- ifelse(listings_cleaned$price > upper_fence, TRUE, FALSE)
table(listings_cleaned$price_outlier, useNA = "ifany")
# A few more flags
listings_cleaned$long_stay_only   <- listings_cleaned$minimum_nights > 30
listings_cleaned$never_reviewed   <- listings_cleaned$number_of_reviews == 0
listings_cleaned$always_available <- listings_cleaned$availability_365 == 365

flag_columns <- c("price_outlier", "long_stay_only", "never_reviewed",
                  "always_available")

# How many flags does each listing raise?
listings_cleaned$n_flags <- rowSums(listings_cleaned[flag_columns], na.rm = TRUE)
table(listings_cleaned$n_flags)


# The most suspicious listings, for manual inspection
listings_cleaned %>%
  filter(n_flags >= 3) %>%
  select(name, neighbourhood_cleansed, room_type, price,
         minimum_nights, number_of_reviews, availability_365) %>%
  head(8)

par(mar = c(4, 4, 3, 2))
boxplot(listings_cleaned$price ~ listings_cleaned$price_outlier,
        log = "y", col = c(blue, orange), border = "black",
        names = c("Within fence", "Flagged as outlier"),
        xlab = "", ylab = "Price per night (AUD, log scale)",
        main = "What the outlier flag actually separates")

listings_cleaned %>%
  filter(!is.na(price)) %>%
  group_by(price_outlier) %>%
  summarise(n = n(), mean_price = round(mean(price)), median_price = median(price))
round(mean(listings_cleaned$price, na.rm = TRUE))                        # all listings
round(mean(listings_cleaned$price[!listings_cleaned$price_outlier], na.rm = TRUE))  # flagged removed
median(listings_cleaned$price, na.rm = TRUE)

# The mean moves by about $70 depending on the choice; the median barely moves
# at all. That is the whole argument for medians in one line.


# =============================================================================
# STEP 5 - FEATURE ENGINEERING
# =============================================================================

# A FEATURE is a new variable you calculate from existing ones because it
# answers your question better than the raw columns do.


# --- Feature 1: number of amenities (unpacking the JSON) ---------------------

# This turns the unusable amenities column from Step 1e into a useful number.
# Each amenity is separated by '", "', so split on that and count the pieces.

listings_cleaned$n_amenities <- sapply(strsplit(listings_cleaned$amenities, '", "'), length)

summary(listings_cleaned$n_amenities)
head(listings_cleaned[, c("name", "n_amenities")], 5)

par(mar = c(4, 4, 3, 2))
hist(listings_cleaned$n_amenities, breaks = 40, col = blue, border = "white",
     main = "Number of amenities per listing",
     xlab = "Amenities listed", ylab = "Number of listings")

# We can also test for individual amenities without unpacking the whole thing
listings_cleaned$has_wifi         <- grepl("Wifi",             listings_cleaned$amenities)
listings_cleaned$has_pool         <- grepl("Pool",             listings_cleaned$amenities)
listings_cleaned$has_aircon       <- grepl("Air conditioning", listings_cleaned$amenities)
listings_cleaned$has_free_parking <- grepl("Free parking",     listings_cleaned$amenities)

round(colMeans(listings_cleaned[, c("has_wifi", "has_pool", "has_aircon",
                         "has_free_parking")]), 3)

# --- Feature 2: price per person ---------------------------------------------

# Two listings at $300 a night are not comparable if one sleeps two and the
# other sleeps eight.

listings_cleaned$price_per_person <- round(listings_cleaned$price / listings_cleaned$accommodates, 2)
summary(listings_cleaned$price_per_person)

listings_cleaned %>%
  filter(!is.na(price_per_person)) %>%
  group_by(room_type) %>%
  summarise(
    n                       = n(),
    median_price            = median(price),
    median_price_per_person = median(price_per_person)
  )


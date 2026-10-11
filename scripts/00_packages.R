# ============================================================
# CMCE30005 Business Analytics Challenge
# Script: 00_packages.R
# Purpose: Install (if missing) and load all packages for this project
# Author: Group 4 - Renascence
# Run this ONCE at the start of a session, before any other script.
# ============================================================

packages <- c(
  "data.table",   # Fast reading of the big CSV files (fread)
  "tidyverse",    # Data manipulation and visualisation (dplyr, ggplot2, tidyr ...)
  "lubridate",    # Date handling
  "janitor",      # Data cleaning utilities
  "skimr",        # Quick data summary
  "naniar",       # Missing data visualisation
  "ggcorrplot",   # ggplot2-style correlation matrices
  "scales",       # Number formatting in plots
  "patchwork",    # Combining ggplot2 plots
  "here",         # File paths relative to the project root
  "knitr",        # Report generation
  "rmarkdown"     # R Markdown rendering
)

# Install only the packages that are not installed yet
missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) > 0) install.packages(missing)

# Load packages
invisible(lapply(packages, library, character.only = TRUE))

# Session info (for reproducibility)
sessionInfo()

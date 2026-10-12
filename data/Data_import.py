# ==================== Install missing packages ====================

import sys
import subprocess
import importlib.util

# Map import names to installation names.
required_packages = {
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "sklearn": "scikit-learn",
    "IPython": "ipython"
}

missing_packages = [
    package_name
    for import_name, package_name in required_packages.items()
    if importlib.util.find_spec(import_name) is None
]

if missing_packages:
    print(f"Python interpreter: {sys.executable}")
    print(f"Installing missing packages: {', '.join(missing_packages)}")

    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        *missing_packages
    ])

    importlib.invalidate_caches()
    print("Package installation completed.")
else:
    print("All required packages are already installed.")

# ==================== Import packages ====================

from pathlib import Path
import json
import re
import pickle
import urllib.request
import warnings


import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from IPython.display import display, Markdown

from sklearn.compose import (
    ColumnTransformer,
    TransformedTargetRegressor
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import (
    HistGradientBoostingRegressor,
    RandomForestRegressor
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    mean_absolute_error,
    median_absolute_error,
    mean_squared_error,
    r2_score
)
from sklearn.base import clone
from sklearn.inspection import permutation_importance

# ==================== Display settings ====================

pd.set_option("display.max_columns", 20)
pd.set_option("display.max_rows", 35)

# ==================== Output folders ====================

OUT = Path("analysis_outputs")
F = OUT / "figures"
T = OUT / "tables"
ASSET = Path("assets")

for folder in [OUT, F, T, ASSET]:
    folder.mkdir(parents=True, exist_ok=True)

# ==================== Dataset paths ====================

DATA_FOLDER = Path.home() / "Downloads"


def locate(stem):
    """Find a dataset in the Downloads folder."""
    for name in [
        f"{stem} (1).csv.gz",
        f"{stem}.csv.gz",
        f"{stem} (1).csv",
        f"{stem}.csv"
    ]:
        path = DATA_FOLDER / name
        if path.is_file():
            return path

    raise FileNotFoundError(
        f"Cannot find the {stem} dataset in {DATA_FOLDER}. "
        "Please check the filename and folder."
    )


listing_path = locate("listings_airbnb")
review_path = locate("reviews_airbnb")
calendar_path = locate("calendar_airbnb")

# ==================== Save datasets to the data folder ====================

# Use the data folder containing this Python script.
# Script location: CMCE30005-Renascence/data/dataimport.py
DATA_OUTPUT = Path(__file__).resolve().parent
DATA_OUTPUT.mkdir(parents=True, exist_ok=True)


def save_dataset(source_path, stem):
    """Copy a dataset to the data folder using a standard filename."""
    source_path = Path(source_path).resolve()

    # Preserve the source file format.
    if source_path.name.endswith(".csv.gz"):
        filename = f"{stem}.csv.gz"
    elif source_path.name.endswith(".csv"):
        filename = f"{stem}.csv"
    else:
        raise ValueError(f"Unsupported file format: {source_path.name}")

    destination = DATA_OUTPUT / filename

    if source_path == destination:
        print(f"Already in the data folder: {destination}")
        return destination

    # Avoid overwriting an existing dataset.
    if destination.exists():
        raise FileExistsError(
            f"Destination already exists: {destination}"
        )

    # Copy the file without loading the full dataset into memory.
    shutil.copy2(source_path, destination)
    print(f"Dataset saved to: {destination}")

    return destination


# These source paths are defined by the preceding locate() calls.
listing_path = save_dataset(listing_path, "listings_airbnb")
review_path = save_dataset(review_path, "reviews_airbnb")
calendar_path = save_dataset(calendar_path, "calendar_airbnb")

print("All dataset files are available in:", DATA_OUTPUT)

# ==================== Verify imported data ====================

for name, path in [
    ("Listings", listing_path),
    ("Reviews", review_path),
    ("Calendar", calendar_path)
]:
    print(f"{name} file: {path}")
    print(f"File exists: {path.is_file()}")

    if path.is_file():
        size_mb = path.stat().st_size / (1024 ** 2)
        print(f"File size: {size_mb:.2f} MB")

    print()

print("Dataset file verification completed.")
import numpy as np
import pandas as pd
from ydata_profiling import ProfileReport

df = pd.read_csv("data/listings.csv")
profile = ProfileReport(df, title="Airbnb Listings EDA Report", explorative=True, minimal=True)
profile.to_file("airbnb_listings_eda_report.html")

if __name__ == "__main__":
    print("EDA report generated: airbnb_listings_eda_report.html")

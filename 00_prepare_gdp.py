"""
GDP per capita (current US$, NY.GDP.PCAP.CD), 2019-2024, long format.
Input : World Bank CSV export API_NY.GDP.PCAP.CD_DS2_*.csv
Output: gdp_by_year.csv (iso3, year, gdp_pc_usd)
"""
import glob
import os
import sys

import pandas as pd

os.chdir(os.environ.get("DATA_DIR", "data"))


def main():
    files = sorted(glob.glob("API_NY.GDP.PCAP.CD_DS2_*.csv"))
    if not files:
        sys.exit("missing: API_NY.GDP.PCAP.CD_DS2_*.csv")
    w = pd.read_csv(files[-1], skiprows=4)
    years = [str(y) for y in range(2019, 2025)]
    g = (w.melt(id_vars="Country Code", value_vars=years, var_name="year", value_name="gdp_pc_usd")
          .rename(columns={"Country Code": "iso3"})
          .dropna(subset=["gdp_pc_usd"]))
    g["year"] = g.year.astype(int)
    g = g.sort_values(["year", "iso3"])
    g.to_csv("gdp_by_year.csv", index=False)
    print(f"gdp_by_year.csv: {len(g)} rows, {g.iso3.nunique()} codes")


if __name__ == "__main__":
    main()

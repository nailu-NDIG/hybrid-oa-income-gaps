"""
Journal x country x year panel (zeros filled), with APC, GDP per capita and
year-specific World Bank income group (calendar year Y -> FY(Y+2), OGHIST).
n_all: research articles with >= 1 author in the country; n_hybrid: of those,
hybrid OA (defined only in hybrid journal-years).
Inputs : journals_eligible.csv, scholcommlab_apc_dataset_2019_2025-2.csv,
         openalex_country_journal_year.csv, openalex_journal_year_totals.csv,
         openalex_log.csv, gdp_by_year.csv (iso3, year, gdp_pc_usd), OGHIST.xlsx,
         sample_top50_by_area_sjr{2019,2023,2025}.csv
Output : panel_jcy.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pycountry
import os

os.chdir(os.environ.get("DATA_DIR", "data"))

YEARS = list(range(2019, 2025))
# ScholCommLab record whose ISSNs belong to two journals (J Phys Chem A and C)
EXCLUDE = {"1089-5639"}
INCOME_LABELS = {"L": "Low income", "LM": "Lower-middle income",
                 "UM": "Upper-middle income", "H": "High income"}


def read_keep_na(path, **kw):
    # keep Namibia's "NA" as a code, not a missing value
    return pd.read_csv(path, keep_default_na=False, na_values=[""], **kw)


def iso2_to_iso3(code):
    if code == "XK":
        return "XKX"
    c = pycountry.countries.get(alpha_2=code)
    return c.alpha_3 if c else None


def load_apc():
    s = pd.read_csv("scholcommlab_apc_dataset_2019_2025-2.csv", low_memory=False)
    s = s[(s.apc_year.between(2019, 2024)) & (s.apc_usd > 0)].copy()
    s["issn_l"] = s.issn_l.fillna(s.issn1).fillna(s.issn2)
    g = (s.groupby(["issn_l", "apc_year"])
           .agg(apc_usd=("apc_usd", "median"),
                oa_status_year=("oa_status", lambda x: x.mode().iat[0]))
           .reset_index().rename(columns={"apc_year": "year"}))
    return g


def load_income():
    raw = pd.read_excel("OGHIST.xlsx", sheet_name="Country Analytical History", header=None)
    hdr = raw.apply(lambda r: r.astype(str).str.match(r"^FY\d{2}$").sum(), axis=1).idxmax()
    df = raw.iloc[hdr + 1:].copy()
    df.columns = raw.iloc[hdr].astype(str)
    df = df.rename(columns={df.columns[0]: "iso3"})
    df = df[df.iso3.astype(str).str.fullmatch(r"[A-Z]{3}")]
    rows = []
    for y in YEARS:
        fy = f"FY{str(y + 2)[-2:]}"
        if fy not in df.columns:
            sys.exit(f"OGHIST.xlsx has no column {fy}")
        t = df[["iso3", fy]].rename(columns={fy: "code"})
        t["year"] = y
        rows.append(t)
    inc = pd.concat(rows)
    inc["income_group"] = inc.code.astype(str).str.strip().map(INCOME_LABELS)
    # unclassified country-years take the nearest classified year
    inc = inc.sort_values(["iso3", "year"])
    inc["income_group"] = inc.groupby("iso3").income_group.transform(lambda s: s.ffill().bfill())
    return inc[["iso3", "year", "income_group"]]


def main():
    counts = read_keep_na("openalex_country_journal_year.csv")
    totals = pd.read_csv("openalex_journal_year_totals.csv")
    log = pd.read_csv("openalex_log.csv")
    ok = set(log.loc[log.status == "ok", "issn_l"]) - EXCLUDE
    counts = counts[counts.issn_l.isin(ok)]
    print(f"journals with data: {len(ok)}")

    wide = (counts.pivot_table(index=["issn_l", "iso2", "year"], columns="variant",
                               values="n_works", aggfunc="sum")
                  .reset_index().rename(columns={"all": "n_all", "hybrid": "n_hybrid"}))

    apc = load_apc()
    apc = apc[apc.issn_l.isin(ok)]

    # universe: journal-country pairs ever observed x journal-years with APC
    pairs = wide.loc[wide.n_all > 0, ["issn_l", "iso2"]].drop_duplicates()
    grid = pairs.merge(apc, on="issn_l")
    panel = grid.merge(wide, on=["issn_l", "iso2", "year"], how="left")
    panel["n_all"] = panel.n_all.fillna(0).astype(int)
    hybrid_year = panel.oa_status_year.eq("Hybrid OA")
    panel["n_hybrid"] = np.where(hybrid_year, panel.n_hybrid.fillna(0), np.nan)

    tot = (panel.groupby(["issn_l", "year"])
                .agg(tot_all=("n_all", "sum"), tot_hybrid=("n_hybrid", "sum"))
                .reset_index())
    panel = panel.merge(tot, on=["issn_l", "year"])
    raw_tot = totals.pivot_table(index=["issn_l", "year"], columns="variant",
                                 values="total_works").reset_index()
    raw_tot.columns = ["issn_l", "year"] + [f"openalex_total_{c}" for c in raw_tot.columns[2:]]
    panel = panel.merge(raw_tot, on=["issn_l", "year"], how="left")

    panel["iso3"] = panel.iso2.map(iso2_to_iso3)
    # French overseas departments are reported separately by OpenAlex but are
    # part of France for World Bank income and GDP purposes
    panel.loc[panel.iso2.isin(["RE", "GP", "GF", "MQ", "YT"]), "iso3"] = "FRA"
    unmapped = sorted(panel.loc[panel.iso3.isna(), "iso2"].unique())
    if unmapped:
        print("ISO2 codes without ISO3 (dropped):", unmapped)
    panel = panel[panel.iso3.notna()]

    gdp = pd.read_csv("gdp_by_year.csv")[["iso3", "year", "gdp_pc_usd"]]
    panel = panel.merge(gdp, on=["iso3", "year"], how="left")
    inc = load_income()
    panel = panel.merge(inc, on=["iso3", "year"], how="left")
    inc19 = inc[inc.year == 2019][["iso3", "income_group"]].rename(columns={"income_group": "income_group_2019"})
    panel = panel.merge(inc19, on="iso3", how="left")

    j = pd.read_csv("journals_eligible.csv", dtype=str)[["issn_l", "journal", "publisher"]]
    panel = panel.merge(j, on="issn_l", how="left")
    # main sample (2019) and sensitivity samples (2023, 2025), flag only
    for y in (2019, 2023, 2025):
        f = Path(f"sample_top50_by_area_sjr{y}.csv")
        if f.exists():
            top = set(pd.read_csv(f, dtype=str).issn_l)
            panel[f"top50_sjr{y}"] = panel.issn_l.isin(top)
            print(f"top50_sjr{y}: {panel.loc[panel[f'top50_sjr{y}'], 'issn_l'].nunique()} journals with data")

    panel["log_apc"] = np.log(panel.apc_usd)
    miss_inc = panel.income_group.isna().mean()
    miss_gdp = panel.gdp_pc_usd.isna().mean()
    print(f"rows: {len(panel):,}  journals: {panel.issn_l.nunique()}  "
          f"countries: {panel.iso2.nunique()}")
    print(f"missing income group: {miss_inc:.1%}  missing GDP: {miss_gdp:.1%}")
    print(panel.groupby("income_group").agg(rows=("n_all", "size"),
                                            articles=("n_all", "sum")).to_string())
    panel.to_csv("panel_jcy.csv", index=False)
    print("panel_jcy.csv saved")


if __name__ == "__main__":
    main()

"""
Sensitivity analysis: first-author analysis in all hoaddata hybrid journals
(no ranking or APC-data restriction). Income group from OGHIST.xlsx.
Inputs : hoaddata/, jct_data/, OGHIST.xlsx, journals_eligible.csv,
         sample_top50_by_area_sjr2019.csv
Counting unit: article x first-author affiliation country (see hoad_common.py).
Outputs: hoad_all_jcy.csv, uptake_firstauthor_all_hoad.csv,
         gap_vs_high_income_all_hoad.csv, gap_share_agreement_all_hoad.csv
"""
import os

import pandas as pd
import pycountry

from hoad_common import YEARS, gaps, hoad_counts, rates

os.chdir(os.environ.get("DATA_DIR", "data"))

INCOME_LABELS = {"L": "Low income", "LM": "Lower-middle income",
                 "UM": "Upper-middle income", "H": "High income"}
FRENCH_DOM = {"RE", "GP", "GF", "MQ", "YT"}


def iso2_to_iso3(code):
    if code == "XK":
        return "XKX"
    if code in FRENCH_DOM:
        return "FRA"
    c = pycountry.countries.get(alpha_2=code)
    return c.alpha_3 if c else None


def load_income():
    raw = pd.read_excel("OGHIST.xlsx", sheet_name="Country Analytical History", header=None)
    hdr = raw.apply(lambda r: r.astype(str).str.match(r"^FY\d{2}$").sum(), axis=1).idxmax()
    df = raw.iloc[hdr + 1:].copy()
    df.columns = raw.iloc[hdr].astype(str)
    df = df.rename(columns={df.columns[0]: "iso3"})
    df = df[df.iso3.astype(str).str.fullmatch(r"[A-Z]{3}")]
    rows = []
    for y in range(YEARS[0], YEARS[1] + 1):
        fy = f"FY{str(y + 2)[-2:]}"
        t = df[["iso3", fy]].rename(columns={fy: "code"})
        t["year"] = y
        rows.append(t)
    inc = pd.concat(rows)
    inc["income_group"] = inc.code.astype(str).str.strip().map(INCOME_LABELS)
    inc = inc.sort_values(["iso3", "year"])
    inc["income_group"] = inc.groupby("iso3").income_group.transform(lambda s: s.ffill().bfill())
    return inc[["iso3", "year", "income_group"]]


def summarise(d, label):
    g = rates(d)
    gap, share = gaps(g)
    print(f"\n=== {label}: {d.issn_l.nunique():,} journals, "
          f"{int(d.articles.sum()):,} article-country units ===")
    print((g.pivot(index="year", columns="income_group", values="oa_rate") * 100).round(1).to_string())
    print(share.round(3).to_string(index=False))
    return g, gap, share


def main():
    d = hoad_counts()

    # income group by country-year
    d["iso3"] = d.iso2.map(iso2_to_iso3)
    d = d.merge(load_income(), on=["iso3", "year"], how="left")
    miss = d.loc[d.income_group.isna(), "articles"].sum() / d.articles.sum()
    print(f"articles without income group (dropped): {miss:.2%}")
    d = d[d.income_group.notna()]

    # flag journals in the main sample (any ISSN variant)
    elig = pd.read_csv("journals_eligible.csv", dtype=str)
    top = set(pd.read_csv("sample_top50_by_area_sjr2019.csv", dtype=str).issn_l) - {"1089-5639"}
    keys = pd.concat([pd.DataFrame({"jid": elig.issn_l, "k": elig[c]})
                      for c in ("issn_l", "issn1", "issn2")]).dropna()
    top_keys = set(keys.loc[keys.jid.isin(top), "k"])
    d["top50_sjr2019"] = d.issn_l.isin(top_keys)
    d.to_csv("hoad_all_jcy.csv", index=False)

    g_all, gap_all, share_all = summarise(d, "All hoaddata hybrid journals")
    summarise(d[~d.top50_sjr2019], "hoaddata journals outside the main sample")
    g_all.to_csv("uptake_firstauthor_all_hoad.csv", index=False)
    gap_all.to_csv("gap_vs_high_income_all_hoad.csv", index=False)
    share_all.to_csv("gap_share_agreement_all_hoad.csv", index=False)
    print("\nsaved hoad_all_jcy.csv, uptake_firstauthor_all_hoad.csv, gap_vs_high_income_all_hoad.csv")


if __name__ == "__main__":
    main()

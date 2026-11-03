"""
Descriptive results for samples based on SJR 2019, 2023 and 2025 ranks.
Inputs : panel_jcy_ta.csv, hoad_all_jcy.csv, journals_eligible.csv
Output : sensitivity_samples.csv
"""
import os

import pandas as pd

from hoad_common import gaps, rates

os.chdir(os.environ.get("DATA_DIR", "data"))

SAMPLES = ["top50_sjr2019", "top50_sjr2023", "top50_sjr2025"]
GROUPS = ["High income", "Upper-middle income", "Lower-middle income", "Low income"]


def main():
    p = pd.read_csv("panel_jcy_ta.csv", keep_default_na=False, na_values=[""], low_memory=False)
    p = p[p.income_group.notna()]
    for s in SAMPLES:
        p[s] = p[s].astype(str).str.lower().eq("true")

    # hoaddata first-author counts mapped to our journal ids
    h = pd.read_csv("hoad_all_jcy.csv", keep_default_na=False, na_values=[""])
    elig = pd.read_csv("journals_eligible.csv", dtype=str)
    keys = pd.concat([pd.DataFrame({"jid": elig.issn_l, "k": elig[c]})
                      for c in ("issn_l", "issn1", "issn2")]).dropna().drop_duplicates("k")
    h = (h.merge(keys, left_on="issn_l", right_on="k")
          .groupby(["jid", "year", "iso2", "income_group"], as_index=False)[["articles", "oa", "oa_ta"]].sum()
          .rename(columns={"jid": "issn_l"}))
    hyb_years = p.loc[p.oa_status_year == "Hybrid OA", ["issn_l", "year"]].drop_duplicates()
    h = h.merge(hyb_years, on=["issn_l", "year"])

    rows = []
    for s in SAMPLES:
        m = p[p[s]]
        r = {"sample": s, "journals": m.issn_l.nunique()}
        # APC burden, medians 2019 and 2024
        b = m[(m.n_all > 0) & m.gdp_pc_usd.notna()].assign(b=lambda d: 100 * d.apc_usd / d.gdp_pc_usd)
        for g in GROUPS:
            for y in (2019, 2024):
                r[f"burden_{g.split()[0]}_{y}"] = b[(b.income_group == g) & (b.year == y)].b.median()
        # full-count paid OA uptake, hybrid journal-years
        hy = m[m.n_hybrid.notna() & (m.n_all > 0)]
        u = hy.groupby(["year", "income_group"])[["n_hybrid", "n_all"]].sum()
        u = (u.n_hybrid / u.n_all).unstack()
        for g in GROUPS:
            for y in (2019, 2024):
                r[f"uptake_all_{g.split()[0]}_{y}"] = 100 * u.loc[y, g]
        # first-author: gap vs high income and share via agreements
        sj = set(m.issn_l)
        f = h[h.issn_l.isin(sj)]
        r["fa_journals"] = f.issn_l.nunique()
        _, sh = gaps(rates(f))
        for x in sh.itertuples():
            k = x.group.split()[0]
            r[f"gap_{k}_2019"] = 100 * x.gap_start
            r[f"gap_{k}_2024"] = 100 * x.gap_end
            r[f"share_ta_{k}"] = 100 * x.share_agreement
        rows.append(r)

    out = pd.DataFrame(rows).set_index("sample").T
    out.to_csv("sensitivity_samples.csv")
    pd.set_option("display.width", 200)
    print(out.round(1).to_string())


if __name__ == "__main__":
    main()

"""
Any-OA vs hybrid OA by income group, all authors (full counting), hybrid journal-years
of the main sample, 2019 and 2024. Gaps: high income minus group, percentage points.
Input : anyoa_country_journal_year.csv, panel_jcy.csv
Output: any_oa_by_income.csv
"""
import os

import pandas as pd

os.chdir(os.environ.get("DATA_DIR", "data"))

LV = ["High income", "Upper-middle income", "Lower-middle income", "Low income"]
a = pd.read_csv("anyoa_country_journal_year.csv", keep_default_na=False, na_values=[""])
a = a.drop_duplicates(["issn_l", "year", "variant", "iso2"], keep="last")
a = a.pivot_table(index=["issn_l", "year", "iso2"], columns="variant", values="n_works",
                  aggfunc="sum", fill_value=0).reset_index()
p = pd.read_csv("panel_jcy.csv", keep_default_na=False, na_values=[""],
                usecols=["issn_l", "year", "iso2", "n_hybrid", "income_group", "top50_sjr2019"])
p = p[p.top50_sjr2019 & p.year.isin([2019, 2024]) & p.n_hybrid.notna() & p.income_group.isin(LV)]
d = p[["issn_l", "year", "iso2", "income_group"]].merge(a, on=["issn_l", "year", "iso2"], how="inner")
d = d[d["all"] > 0]
g = d.groupby(["year", "income_group"]).agg(journals=("issn_l", "nunique"), articles=("all", "sum"),
                                            hybrid=("hybrid", "sum"), any_oa=("any_oa", "sum")).reset_index()
g["hybrid_pct"] = 100 * g.hybrid / g.articles
g["any_oa_pct"] = 100 * g.any_oa / g.articles
g["other_oa_pct"] = g.any_oa_pct - g.hybrid_pct
for c in ["hybrid_pct", "any_oa_pct", "other_oa_pct"]:
    hic = g[g.income_group == "High income"].set_index("year")[c]
    g[c.replace("_pct", "_gap_pp")] = g.year.map(hic) - g[c]
g["income_group"] = pd.Categorical(g.income_group, LV)
g = g.sort_values(["year", "income_group"])
g.to_csv("any_oa_by_income.csv", index=False)
pd.set_option("display.width", 200)
print(g.round(1).to_string(index=False))

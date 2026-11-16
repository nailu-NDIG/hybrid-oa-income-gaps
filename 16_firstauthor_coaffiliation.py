"""
First-author hybrid OA units by income group: share whose article also lists a first-author
affiliation in another country, in a high-income country, or at an institution with
identified agreement eligibility in another country. Same sample and units as step 5
(main-sample hybrid journal-years, 2019-2024).
Input : hoaddata/data/*.rda, jct_data/, journals_eligible.csv, hoad_jcy.csv
Output: firstauthor_coaffiliation.csv
"""
import os

import pandas as pd

os.chdir(os.environ.get("DATA_DIR", "data"))
from hoad_common import hoad_counts  # noqa: E402

LV = ["High income", "Upper-middle income", "Lower-middle income", "Low income"]
h = pd.read_csv("hoad_jcy.csv", keep_default_na=False, na_values=[""])
s = h[h.top50_sjr2019]

_, dc = hoad_counts(return_units=True)
elig = pd.read_csv("journals_eligible.csv", dtype=str)
keys = pd.concat([pd.DataFrame({"jid": elig.issn_l, "k": elig[c]})
                  for c in ("issn_l", "issn1", "issn2")]).dropna().drop_duplicates("k")
pairs = s[["issn_l", "year"]].drop_duplicates().rename(columns={"issn_l": "jid"})
dc = dc.merge(keys, left_on="issn_l", right_on="k").merge(pairs, on=["jid", "year"])

inc = h[["iso2", "year", "income_group"]].drop_duplicates()
dc = dc.merge(inc, left_on=["country_code", "year"], right_on=["iso2", "year"], how="left")
dc["hic"] = dc.income_group == "High income"
g = dc.groupby("doi").agg(n=("country_code", "size"), any_hic=("hic", "max"), any_ta=("ta", "max"))
dc = dc.merge(g, on="doi")

rows = []
for period, d in (("2019-2024", dc), ("2024", dc[dc.year == 2024])):
    for grp in LV:
        e = d[d.income_group == grp]
        rows.append({
            "period": period, "income_group": grp, "oa_units": len(e),
            "eligible_pct": 100 * e.ta.mean(),
            "multi_country_pct": 100 * (e.n > 1).mean(),
            "also_high_income_pct": 100 * (e.any_hic & ~e.hic).mean(),
            "eligible_other_country_pct": 100 * (e.any_ta & ~e.ta).mean(),
        })
out = pd.DataFrame(rows)
out.to_csv("firstauthor_coaffiliation.csv", index=False)
print(out.round(1).to_string(index=False))

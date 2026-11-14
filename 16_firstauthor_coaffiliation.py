"""
First-author hybrid OA units by income group: share whose first author also lists an
affiliation in another country, in a high-income country, or at an institution with
identified agreement eligibility in another country. Main sample, 2019-2024.
Input : hoaddata/data/cc_articles.rda, jct_data/, hoad_jcy.csv
Output: firstauthor_coaffiliation.csv
"""
import os

import pandas as pd
import pyreadr

os.chdir(os.environ.get("DATA_DIR", "data"))
from hoad_common import agreement_coverage  # noqa: E402

LV = ["High income", "Upper-middle income", "Lower-middle income", "Low income"]
h = pd.read_csv("hoad_jcy.csv", keep_default_na=False, na_values=[""])
h = h[h.top50_sjr2019]
issns = set(h.issn_l.unique())

cc = next(iter(pyreadr.read_r("hoaddata/data/cc_articles.rda").values()))
cc = cc[cc.cr_year.between(2019, 2024) & cc.country_code.notna() & cc.issn_l.isin(issns)]
cc = cc[["doi", "issn_l", "cr_year", "country_code", "ror"]]

ta = agreement_coverage()
m = cc.merge(ta, left_on=["issn_l", "ror"], right_on=["issn_l", "ror_id"], how="left")
m["active"] = (m.cr_year >= m.y0) & (m.cr_year <= m.y1)
dc = (m.groupby(["doi", "country_code"]).agg(ta=("active", "max"), year=("cr_year", "first"))
        .reset_index())
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

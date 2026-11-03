"""
First-author hybrid OA in hybrid journal-years of the main sample, split into
OA with agreement eligibility (an active ESAC agreement covers the journal and
one of the first author's institutions in that country) and other OA.
Counting unit: article x first-author affiliation country (see hoad_common.py).
Inputs : hoaddata/data/{cc_articles,jn_aff}.rda, jct_data/data/*.csv,
         panel_jcy_ta.csv, journals_eligible.csv
Outputs: hoad_jcy.csv, uptake_firstauthor_by_year_income.csv,
         gap_vs_high_income.csv, gap_share_agreement.csv, gap_share_agreement_ci.csv
"""
import os

import numpy as np
import pandas as pd

from hoad_common import YEARS, gaps, hoad_counts, rates

os.chdir(os.environ.get("DATA_DIR", "data"))


def main():
    d, dc = hoad_counts(return_units=True)

    # hoaddata ISSN-L -> our journal id; journals with two hoaddata ISSN-Ls are summed
    elig = pd.read_csv("journals_eligible.csv", dtype=str)
    keys = pd.concat([pd.DataFrame({"jid": elig.issn_l, "k": elig[c]})
                      for c in ("issn_l", "issn1", "issn2")]).dropna().drop_duplicates("k")
    d = (d.merge(keys, left_on="issn_l", right_on="k")
          .groupby(["jid", "year", "iso2"], as_index=False)[["articles", "oa", "oa_ta"]].sum()
          .rename(columns={"jid": "issn_l"}))

    p = pd.read_csv("panel_jcy_ta.csv", keep_default_na=False, na_values=[""], low_memory=False,
                    usecols=["issn_l", "iso2", "year", "income_group", "income_group_2019",
                             "top50_sjr2019", "oa_status_year"])
    inc = p[["iso2", "year", "income_group", "income_group_2019"]].dropna().drop_duplicates(["iso2", "year"])
    # hybrid journal-years of journals retained in the panel (exclusions applied there)
    hyb = p.loc[p.oa_status_year == "Hybrid OA", ["issn_l", "year"]].drop_duplicates()
    top = set(p.loc[p.top50_sjr2019.astype(str) == "True", "issn_l"])
    d = d.merge(hyb, on=["issn_l", "year"]).merge(inc, on=["iso2", "year"])
    d["top50_sjr2019"] = d.issn_l.isin(top)
    assert not d.duplicated(["issn_l", "iso2", "year"]).any()
    d.to_csv("hoad_jcy.csv", index=False)

    s = d[d.top50_sjr2019]
    # OA articles whose first author has affiliations in > 1 country (main sample)
    u = (dc.merge(keys, left_on="issn_l", right_on="k")
           .merge(s[["issn_l", "year"]].drop_duplicates(), left_on=["jid", "year"], right_on=["issn_l", "year"]))
    k = u.groupby("doi").country_code.nunique()
    print(f"main-sample OA articles: {len(k):,}; with > 1 first-author country: {(k > 1).mean():.1%}")
    n_j = s.groupby("year").issn_l.nunique()
    print(f"main sample: {s.issn_l.nunique()} hybrid journals; per year: {n_j.to_dict()}")
    g = rates(s)
    g.to_csv("uptake_firstauthor_by_year_income.csv", index=False)
    print((g.pivot(index="year", columns="income_group", values="oa_rate") * 100).round(1).to_string())
    print((g.pivot(index="year", columns="income_group", values="ta_oa_rate") * 100).round(1).to_string())

    gap, share = gaps(g)
    gap.to_csv("gap_vs_high_income.csv", index=False)
    share.to_csv("gap_share_agreement.csv", index=False)
    print(share.round(3).to_string(index=False))

    # journal-cluster bootstrap (1,000 resamples) for gaps and shares
    agg = s.groupby(["issn_l", "year", "income_group"], as_index=False)[["articles", "oa", "oa_ta"]].sum()
    by = dict(tuple(agg.groupby("issn_l")))
    ids = np.array(list(by))
    rng = np.random.default_rng(1)
    boot = []
    for b in range(1000):
        _, sh = gaps(rates(pd.concat([by[j] for j in rng.choice(ids, len(ids))])))
        boot.append(sh.assign(rep=b))
    boot = pd.concat(boot)
    ci = (boot.groupby("group")[["gap_start", "gap_end", "share_agreement"]]
              .quantile([0.025, 0.975]).unstack())
    ci.columns = [f"{a}_{'lo' if q == 0.025 else 'hi'}" for a, q in ci.columns]
    ci = share.set_index("group").join(ci).reset_index()
    ci.to_csv("gap_share_agreement_ci.csv", index=False)
    print("bootstrap 95% CI:")
    print(ci.round(3).to_string(index=False))

    # sensitivity: income group fixed at 2019 classification
    g19 = rates(s.drop(columns="income_group").rename(columns={"income_group_2019": "income_group"}))
    g19.to_csv("uptake_firstauthor_by_year_income2019.csv", index=False)
    _, share19 = gaps(g19)
    share19.to_csv("gap_share_agreement_income2019.csv", index=False)
    print("income group fixed at 2019:")
    print(share19.round(3).to_string(index=False))

    # sensitivity: journals observed as hybrid in all six years (fixed composition)
    ny = s.groupby("issn_l").year.nunique()
    bal = s[s.issn_l.isin(ny[ny == YEARS[1] - YEARS[0] + 1].index)]
    gb = rates(bal)
    gb.to_csv("uptake_firstauthor_by_year_income_balanced.csv", index=False)
    _, shareb = gaps(gb)
    shareb.to_csv("gap_share_agreement_balanced.csv", index=False)
    print(f"balanced panel: {bal.issn_l.nunique()} journals hybrid in every year")
    print((gb.pivot(index="year", columns="income_group", values="oa_rate") * 100).round(1).to_string())
    print(shareb.round(3).to_string(index=False))


if __name__ == "__main__":
    main()

"""
Completeness of ESAC journal and institution lists by year, and a broad-eligibility scenario
for first-author agreement eligibility: for agreements without lists, every
first author in a listed country publishing in a journal of the agreement's
publisher is counted as eligible.
Inputs : jct_data/data/*.csv, hoaddata/, journals_eligible.csv, hoad_jcy.csv
Outputs: esac_list_coverage.csv, gap_share_agreement_upper.csv
"""
import importlib.util
import os
from pathlib import Path

import pandas as pd

from hoad_common import YEARS, agreement_coverage, gaps, rates, rda

HERE = Path(__file__).resolve().parent
os.environ["DATA_DIR"] = os.path.abspath(os.environ.get("DATA_DIR", "data"))
os.chdir(os.environ["DATA_DIR"])
spec = importlib.util.spec_from_file_location("m04", HERE / "04_add_agreements.py")
m04 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m04)


def main():
    e = pd.read_csv("jct_data/data/esac_df.csv")
    e["y0"] = pd.to_datetime(e.start_date).dt.year
    e["y1"] = pd.to_datetime(e.end_date).dt.year
    jn = set(pd.read_csv("jct_data/data/jct_jn_short.csv", usecols=["esac_id"]).esac_id)
    ins = set(pd.read_csv("jct_data/data/jct_inst_all.csv", usecols=["esac_id"]).esac_id)
    e["lists"] = e.id.isin(jn) & e.id.isin(ins)

    cov = []
    for y in range(YEARS[0], YEARS[1] + 1):
        a = e[(e.y0 <= y) & (e.y1 >= y)]
        cov.append({"year": y, "agreements": len(a), "with_lists": int(a.lists.sum()),
                    "share_agreements": a.lists.mean(),
                    "share_publications": a.loc[a.lists, "annual_publications"].sum() / a.annual_publications.sum()})
    cov = pd.DataFrame(cov)
    cov.to_csv("esac_list_coverage.csv", index=False)
    print(cov.round(3).to_string(index=False))

    # publisher x country x year covered by agreements without lists
    nl = e[~e.lists].assign(publisher=lambda d: d.publisher.map(m04.PUBLISHER_MAP))
    rows = [(r.publisher, m04.to_iso2(c), y)
            for r in nl.itertuples() for c in str(r.country).split(", ")
            for y in range(max(r.y0, YEARS[0]), min(r.y1, YEARS[1]) + 1)]
    nolist = (pd.DataFrame(rows, columns=["publisher", "iso2", "year"]).dropna()
                .drop_duplicates().assign(nolist=True))

    ta = agreement_coverage()
    cc = rda("hoaddata/data/cc_articles.rda")
    cc = cc[cc.cr_year.between(*YEARS) & cc.country_code.notna()]
    m = cc.merge(ta, left_on=["issn_l", "ror"], right_on=["issn_l", "ror_id"], how="left")
    m["active"] = (m.cr_year >= m.y0) & (m.cr_year <= m.y1)
    dc = (m.groupby(["doi", "country_code"])
            .agg(ta=("active", "max"), issn_l=("issn_l", "first"), year=("cr_year", "first"))
            .reset_index())

    elig = pd.read_csv("journals_eligible.csv", dtype=str)
    keys = pd.concat([pd.DataFrame({"jid": elig.issn_l, "k": elig[c]})
                      for c in ("issn_l", "issn1", "issn2")]).dropna().drop_duplicates("k")
    pub = elig.drop_duplicates("issn_l").set_index("issn_l").publisher
    dc = dc.merge(keys, left_on="issn_l", right_on="k")
    dc["publisher"] = dc.jid.map(pub)
    dc = dc.merge(nolist, left_on=["publisher", "country_code", "year"],
                  right_on=["publisher", "iso2", "year"], how="left")
    dc["ta_upper"] = dc.ta | dc.nolist.fillna(False).astype(bool)
    up = (dc.groupby(["jid", "year", "country_code"]).ta_upper.sum().reset_index()
            .rename(columns={"jid": "issn_l", "country_code": "iso2", "ta_upper": "oa_ta_upper"}))

    h = pd.read_csv("hoad_jcy.csv", keep_default_na=False, na_values=[""])
    h = h[h.top50_sjr2019].merge(up, on=["issn_l", "year", "iso2"], how="left").fillna({"oa_ta_upper": 0})
    g = rates(h.assign(oa_ta=h.oa_ta_upper))
    print((g.pivot(index="year", columns="income_group", values="ta_oa_rate") * 100).round(1).to_string())
    _, share = gaps(g)
    share.to_csv("gap_share_agreement_upper.csv", index=False)
    print(share.round(3).to_string(index=False))


if __name__ == "__main__":
    main()

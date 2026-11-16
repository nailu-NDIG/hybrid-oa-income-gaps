"""
Shared hoaddata/ESAC routines for 05 and 06.
Counting unit: article x first-author affiliation country (full counting).
An article whose first author lists affiliations in k countries counts once in
each of the k countries, in both numerator and denominator.
"""
import pandas as pd
import pyreadr

YEARS = (2019, 2024)


def rda(path):
    return next(iter(pyreadr.read_r(path).values()))


def agreement_coverage():
    """journal (ISSN-L) x institution (ROR) x active years, from ESAC via jct_data"""
    inst = (pd.read_csv("jct_data/data/jct_inst_all.csv", usecols=["esac_id", "ror_id"])
              .dropna(subset=["ror_id"]).drop_duplicates())  # institutions without ROR cannot be matched
    jn = pd.read_csv("jct_data/data/jct_jn_short.csv", usecols=["esac_id", "issn_l"]).drop_duplicates()

    # a journal can carry a different ISSN-L in hoaddata than in the registry:
    # also list each agreement journal under all of its ISSNs (journals_eligible.csv)
    elig = pd.read_csv("journals_eligible.csv", dtype=str)
    alias = (pd.concat([pd.DataFrame({"jid": elig.issn_l, "k": elig[c]})
                        for c in ("issn_l", "issn1", "issn2")]).dropna().drop_duplicates())
    expanded = (jn.merge(alias.drop_duplicates("k"), left_on="issn_l", right_on="k")[["esac_id", "jid"]]
                  .merge(alias[["jid", "k"]], on="jid")
                  .rename(columns={"k": "issn_l"})[["esac_id", "issn_l"]])
    jn = pd.concat([jn, expanded]).drop_duplicates()  # journals outside the list keep their own ISSN-L

    esac = pd.read_csv("jct_data/data/esac_df.csv", usecols=["id", "start_date", "end_date"])
    esac["y0"] = pd.to_datetime(esac.start_date).dt.year
    esac["y1"] = pd.to_datetime(esac.end_date).dt.year
    return (jn.merge(inst, on="esac_id")
              .merge(esac[["id", "y0", "y1"]], left_on="esac_id", right_on="id")
              [["issn_l", "ror_id", "y0", "y1"]].drop_duplicates())


def hoad_counts(return_units=False):
    """
    hoaddata ISSN-L x year x country: articles (all), oa (CC-licensed hybrid OA),
    oa_ta (OA with an active agreement covering the journal and at least one of
    the first author's institutions in that country).
    """
    ta = agreement_coverage()
    cc = rda("hoaddata/data/cc_articles.rda")
    cc = cc[cc.cr_year.between(*YEARS) & cc.country_code.notna()]
    # articles without ROR keep ta = False; NaN keys would otherwise match NaN keys in merge
    m = cc.merge(ta, left_on=["issn_l", "ror"], right_on=["issn_l", "ror_id"], how="left")
    m["active"] = (m.cr_year >= m.y0) & (m.cr_year <= m.y1)
    dc = (m.groupby(["doi", "country_code"])
            .agg(ta=("active", "max"), issn_l=("issn_l", "first"), year=("cr_year", "first"))
            .reset_index())
    oa = (dc.groupby(["issn_l", "year", "country_code"])
            .agg(oa=("doi", "size"), oa_ta=("ta", "sum")).reset_index()
            .rename(columns={"country_code": "iso2"}))

    ja = rda("hoaddata/data/jn_aff.rda")
    ja = ja[ja.cr_year.between(*YEARS) & ja.country_code.notna()]
    tot = (ja.groupby(["issn_l", "cr_year", "country_code"]).articles_total.max()
             .reset_index().rename(columns={"cr_year": "year", "country_code": "iso2",
                                            "articles_total": "articles"}))
    d = tot.merge(oa, on=["issn_l", "year", "iso2"], how="outer", indicator=True)
    orphan = d.loc[d._merge == "right_only", "oa"].sum()
    assert orphan == 0, f"{orphan} OA article-countries without denominator"
    d = d.drop(columns="_merge").fillna({"oa": 0, "oa_ta": 0})
    assert (d.oa <= d.articles).all() and (d.oa_ta <= d.oa).all()
    print(f"article-country units {YEARS[0]}-{YEARS[1]}: {int(d.articles.sum()):,}; "
          f"OA {int(d.oa.sum()):,}; OA with agreement eligibility {int(d.oa_ta.sum()):,}")
    return (d, dc) if return_units else d


def gaps(g, groups=("Upper-middle income", "Lower-middle income", "Low income")):
    """gap vs high income in total, agreement-eligible and other OA rates"""
    hi = g[g.income_group == "High income"].set_index("year")
    rows = []
    for grp in groups:
        o = g[g.income_group == grp].set_index("year")
        for y in sorted(g.year.unique()):
            rows.append({"group": grp, "year": y,
                         "gap_total": hi.oa_rate[y] - o.oa_rate[y],
                         "gap_agreement": hi.ta_oa_rate[y] - o.ta_oa_rate[y],
                         "gap_other": hi.other_oa_rate[y] - o.other_oa_rate[y]})
    gap = pd.DataFrame(rows)
    w = gap[gap.year.isin(YEARS)].pivot(index="group", columns="year")
    d_tot = w["gap_total"][YEARS[1]] - w["gap_total"][YEARS[0]]
    d_ag = w["gap_agreement"][YEARS[1]] - w["gap_agreement"][YEARS[0]]
    share = pd.DataFrame({"gap_start": w["gap_total"][YEARS[0]], "gap_end": w["gap_total"][YEARS[1]],
                          "d_gap_total": d_tot, "d_gap_agreement": d_ag, "d_gap_other": d_tot - d_ag,
                          "share_agreement": d_ag / d_tot}).reset_index()
    # reporting convention: shares are reported only when the baseline gap was positive
    share["share_reported"] = share.gap_start > 0
    return gap, share


def rates(d, by=("year", "income_group")):
    g = d.groupby(list(by))[["articles", "oa", "oa_ta"]].sum()
    g["oa_rate"] = g.oa / g.articles
    g["ta_oa_rate"] = g.oa_ta / g.articles
    g["other_oa_rate"] = (g.oa - g.oa_ta) / g.articles
    return g.reset_index()

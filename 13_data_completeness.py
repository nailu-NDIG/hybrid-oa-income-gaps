"""
Data completeness for the first-author analysis (main sample hybrid journal-years)
and income classification gap filling.
Inputs : hoaddata/, journals_eligible.csv, hoad_jcy.csv, panel_jcy_ta.csv, OGHIST.xlsx
Outputs: completeness_by_year.csv, ror_missing_by_income.csv, income_filled.csv
"""
import os

import pandas as pd

from hoad_common import YEARS, rda

os.chdir(os.environ.get("DATA_DIR", "data"))
INCOME = {"L": "Low income", "LM": "Lower-middle income", "UM": "Upper-middle income", "H": "High income"}


def main():
    elig = pd.read_csv("journals_eligible.csv", dtype=str)
    keys = pd.concat([pd.DataFrame({"jid": elig.issn_l, "k": elig[c]})
                      for c in ("issn_l", "issn1", "issn2")]).dropna().drop_duplicates("k")
    h = pd.read_csv("hoad_jcy.csv", keep_default_na=False, na_values=[""])
    jy = h.loc[h.top50_sjr2019, ["issn_l", "year"]].drop_duplicates()

    def in_sample(d):
        d = d.merge(keys, left_on="issn_l", right_on="k")
        return d.merge(jy, left_on=["jid", "cr_year"], right_on=["issn_l", "year"], suffixes=("_h", ""))

    # denominator records (journal x year x first-author country) without country
    ja = rda("hoaddata/data/jn_aff.rda")
    ja = in_sample(ja[ja.cr_year.between(*YEARS)])
    tot = (ja.groupby(["jid", "cr_year", "country_code"], dropna=False).articles_total.max()
             .reset_index())
    tot["no_country"] = tot.country_code.isna()
    den = tot.groupby(["cr_year", "no_country"]).articles_total.sum().unstack(fill_value=0)
    den.columns = ["with_country", "without_country"]

    # CC-licensed records without country or ROR
    cc = rda("hoaddata/data/cc_articles.rda")
    cc = in_sample(cc[cc.cr_year.between(*YEARS)])
    oa = cc.groupby("cr_year").agg(oa_records=("doi", "size"),
                                   oa_no_country=("country_code", lambda s: s.isna().sum()),
                                   oa_no_ror=("ror", lambda s: s.isna().sum()))
    out = den.join(oa).reset_index().rename(columns={"cr_year": "year"})
    out["share_without_country"] = out.without_country / (out.with_country + out.without_country)
    out["share_oa_no_ror"] = out.oa_no_ror / out.oa_records
    out.to_csv("completeness_by_year.csv", index=False)
    print(out.round(3).to_string(index=False))

    # ROR missing by income group among OA records with country
    p = pd.read_csv("panel_jcy_ta.csv", keep_default_na=False, na_values=[""], low_memory=False,
                    usecols=["iso2", "year", "income_group"]).dropna().drop_duplicates(["iso2", "year"])
    k = cc[cc.country_code.notna()].merge(p, left_on=["country_code", "cr_year"], right_on=["iso2", "year"], how="left")
    print(f"OA records with country but no income group: {k.income_group.isna().sum()}")
    r = k.groupby("income_group").agg(records=("doi", "size"), no_ror=("ror", lambda s: s.isna().sum()))
    r["share_no_ror"] = r.no_ror / r.records
    r.to_csv("ror_missing_by_income.csv")
    print(r.round(3).to_string())

    # income classification gap filling
    raw = pd.read_excel("OGHIST.xlsx", sheet_name="Country Analytical History", header=None)
    hdr = raw.apply(lambda x: x.astype(str).str.match(r"^FY\d{2}$").sum(), axis=1).idxmax()
    df = raw.iloc[hdr + 1:].copy()
    df.columns = raw.iloc[hdr].astype(str)
    df = df.rename(columns={df.columns[0]: "iso3"})
    df = df[df.iso3.astype(str).str.fullmatch(r"[A-Z]{3}")]
    cols = [f"FY{str(y + 2)[-2:]}" for y in range(YEARS[0], YEARS[1] + 1)]
    lab = df[cols].apply(lambda s: s.astype(str).str.strip().map(INCOME))
    filled = lab.isna() & lab.notna().any(axis=1).values[:, None]
    f = pd.DataFrame({"iso3": df.iso3.values, "years_filled": filled.sum(axis=1).values,
                      "never_classified": lab.isna().all(axis=1).values})
    f = f[(f.years_filled > 0) | f.never_classified]
    f.to_csv("income_filled.csv", index=False)
    print(f"economies with filled years: {(f.years_filled > 0).sum()} "
          f"({int(f.years_filled.sum())} economy-years); never classified 2019-2024: {f.never_classified.sum()}")
    print(f[f.years_filled > 0].to_string(index=False))


if __name__ == "__main__":
    main()

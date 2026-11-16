"""
Adds agreement coverage to panel_jcy.csv from the ESAC registry as archived from
the cOAlition S Journal Checker Tool (github.com/njahn82/jct_data).
ta_publisher: active agreement with the journal's publisher in the country-year.
ta_journal  : active agreement in the country-year that lists the journal.
ta_journal_lead: ta_journal in the following year.
A country counts as covered when any of its institutions is covered.
Inputs : panel_jcy.csv, journals_eligible.csv, jct_data/data/{esac_df,jct_jn_short}.csv
Output : panel_jcy_ta.csv, agreement_journal_country_year.csv
"""
import pandas as pd
import pycountry
import os

os.chdir(os.environ.get("DATA_DIR", "data"))

JCT = "jct_data/data"

PUBLISHER_MAP = {
    "Elsevier": "ELSEVIER", "Springer Nature": "SPRINGER_NATURE", "Springer": "SPRINGER_NATURE", "Wiley": "WILEY",
    "Sage": "SAGE", "Oxford University Press": "OUP",
    "Cambridge University Press": "CAMBRIDGE_UNIVERSITY_PRESS_-_CUP",
    "American Chemical Society": "ACS", "IOP Publishing": "IOP",
    "Walter de Gruyter": "DE_GRUYTER", "IEEE": "IEEE", "EDP Sciences": "EDP",
    "Frontiers": "FRONTIERS", "MDPI": "MDPI", "PLOS": "PLOS",
    "Public Library of Science": "PLOS",
}
FUZZY = {}  # names resolved by approximate matching, reported in main()
COUNTRY_OVERRIDES = {
    # "Congo" is ambiguous in the registry (CG vs CD); no active agreement listing it
    # covers a sample journal-country-year of either country, so the choice has no effect
    "Chinese Taipei": "TW", "Taiwan": "TW", "Congo": "CG", "Congo (DR)": "CD",
    "Ivory Coast": "CI", "Côte d'Ivoire": "CI", "Kosovo": "XK", "Laos": "LA",
    "Palestine": "PS", "South Korea": "KR", "Czech Republic": "CZ",
    "Hong Kong": "HK", "Moldova": "MD", "Turkey": "TR", "Russia": "RU",
    "Vietnam": "VN", "Iran": "IR", "Bolivia": "BO", "Tanzania": "TZ",
    "Venezuela": "VE", "Syria": "SY",
}


def to_iso2(name):
    name = name.strip()
    if name in COUNTRY_OVERRIDES:
        return COUNTRY_OVERRIDES[name]
    try:
        return pycountry.countries.lookup(name).alpha_2
    except LookupError:
        try:
            hit = pycountry.countries.search_fuzzy(name)[0]
            FUZZY[name] = hit.alpha_2
            return hit.alpha_2
        except LookupError:
            return None


def main():
    esac = pd.read_csv(f"{JCT}/esac_df.csv")
    esac["y0"] = pd.to_datetime(esac.start_date).dt.year
    esac["y1"] = pd.to_datetime(esac.end_date).dt.year
    esac["publisher_scl"] = esac.publisher.map(PUBLISHER_MAP)

    # agreement x country x year (active years within 2019-2024)
    rows = []
    for r in esac.itertuples():
        for c in str(r.country).split(", "):
            iso2 = to_iso2(c)
            for y in range(max(r.y0, 2019), min(r.y1, 2025) + 1):
                rows.append((r.id, r.publisher_scl, iso2, y, c))
    acy = pd.DataFrame(rows, columns=["esac_id", "publisher", "iso2", "year", "country_name"])
    if FUZZY:
        print("ESAC country names matched approximately:", FUZZY)
    bad = sorted(acy.loc[acy.iso2.isna(), "country_name"].unique())
    if bad:
        print("ESAC country names not mapped:", bad)
    acy = acy.dropna(subset=["iso2"])

    panel = pd.read_csv("panel_jcy.csv", keep_default_na=False, na_values=[""], low_memory=False)

    # publisher-level coverage
    pub = (acy.dropna(subset=["publisher"])[["publisher", "iso2", "year"]]
              .drop_duplicates().assign(ta_publisher=1))
    panel = panel.merge(pub, on=["publisher", "iso2", "year"], how="left")
    panel["ta_publisher"] = panel.ta_publisher.fillna(0).astype(int)

    # journal-level coverage (JCT journal lists, matched on any ISSN)
    jn = pd.read_csv(f"{JCT}/jct_jn_short.csv", usecols=["esac_id", "issn_l"]).drop_duplicates()
    elig = pd.read_csv("journals_eligible.csv", dtype=str)
    keys = pd.concat([pd.DataFrame({"issn_l": elig.issn_l, "k": elig[c]})
                      for c in ("issn_l", "issn1", "issn2")])
    keys = keys.dropna().drop_duplicates()
    jn = jn.merge(keys, left_on="issn_l", right_on="k", suffixes=("_jct", "")).drop(columns=["k", "issn_l_jct"])
    jcy = (jn.merge(acy[["esac_id", "iso2", "year"]], on="esac_id")[["issn_l", "iso2", "year"]]
             .drop_duplicates().assign(ta_journal=1))
    jcy.to_csv("agreement_journal_country_year.csv", index=False)
    panel = panel.merge(jcy, on=["issn_l", "iso2", "year"], how="left")
    panel["ta_journal"] = panel.ta_journal.fillna(0).astype(int)
    # eligibility in the following year (placebo lead)
    lead = jcy.assign(year=jcy.year - 1).rename(columns={"ta_journal": "ta_journal_lead"})
    panel = panel.merge(lead, on=["issn_l", "iso2", "year"], how="left")
    panel["ta_journal_lead"] = panel.ta_journal_lead.fillna(0).astype(int)

    m = panel[panel.n_all > 0]
    w = (m.assign(cov=m.ta_publisher * m.n_all)
          .groupby(["year", "income_group"]).apply(lambda d: d["cov"].sum() / d.n_all.sum())
          .unstack().round(3))
    print("Share of articles from countries with an active agreement with the journal's publisher:")
    print(w.to_string())
    panel.to_csv("panel_jcy_ta.csv", index=False)
    print("panel_jcy_ta.csv saved")


if __name__ == "__main__":
    main()

"""
Top 50 journals by SJR within each SCImago subject area (a journal counts in every
area it belongs to), among journals_eligible.csv. Years: 2019 (main), 2023, 2025.
Inputs : journals_eligible.csv, sjr2019.csv, sjr2023.csv, sjr2025.csv
Outputs: sample_top50_by_area_sjr{2019,2023,2025}.csv, issns_extract.txt
"""
import sys
from pathlib import Path

import pandas as pd
import os

os.chdir(os.environ.get("DATA_DIR", "data"))

YEARS = [2019, 2023, 2025]


def norm(x):
    return str(x).replace("-", "").strip().upper()


def build(year, elig_keys):
    s = pd.read_csv(f"sjr{year}.csv", sep=";", dtype=str)
    s = s[s.Type == "journal"].copy()
    s["sjr"] = pd.to_numeric(s.SJR.str.replace(",", "."), errors="coerce")
    s = s.dropna(subset=["sjr"])
    s["issn_list"] = s.Issn.fillna("").str.split(",")
    long = s.explode("issn_list")
    long["k"] = long.issn_list.map(norm)
    m = long.merge(elig_keys, on="k").drop_duplicates(["Sourceid", "issn_l"])
    # one SCImago record per journal: keep the highest SJR if several match
    m["file_rank"] = pd.to_numeric(m.Rank, errors="coerce")
    m = m.sort_values(["sjr", "file_rank"], ascending=[False, True], kind="mergesort").drop_duplicates("issn_l")
    m["sjr_area"] = m.Areas.fillna("").str.split("; ")
    a = m.explode("sjr_area")
    a = a[a.sjr_area.str.len() > 0]
    # ties broken by position in the SCImago file
    a = a.sort_values(["sjr_area", "sjr", "file_rank"], ascending=[True, False, True], kind="mergesort")
    a["rank_in_area"] = a.groupby("sjr_area").cumcount() + 1
    top = a[a.rank_in_area <= 50]
    out = (top[["sjr_area", "rank_in_area", "issn_l", "Title", "sjr", "Areas"]]
             .rename(columns={"sjr": f"sjr{year}"})
             .sort_values(["sjr_area", "rank_in_area"]))
    out.to_csv(f"sample_top50_by_area_sjr{year}.csv", index=False)
    print(f"SJR {year}: {top.issn_l.nunique()} journals in {top.sjr_area.nunique()} areas")
    return set(top.issn_l)


def main():
    elig = pd.read_csv("journals_eligible.csv", dtype=str)
    keys = pd.concat([pd.DataFrame({"issn_l": elig.issn_l, "k": elig[c].map(norm)})
                      for c in ("issn_l", "issn1", "issn2") if c in elig]).dropna()
    keys = keys[keys.k != "NAN"].drop_duplicates("k")

    missing = [f"sjr{y}.csv" for y in YEARS if not Path(f"sjr{y}.csv").exists()]
    if missing:
        sys.exit(f"missing: {', '.join(missing)}")
    samples = {y: build(y, keys) for y in YEARS}
    union = set().union(*samples.values())
    Path("issns_extract.txt").write_text("\n".join(sorted(union)) + "\n")
    print(f"issns_extract.txt: {len(union)} journals")


if __name__ == "__main__":
    main()

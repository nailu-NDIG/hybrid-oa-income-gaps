"""
Sensitivity: any OA status (open_access.is_oa:true) vs hybrid OA, OpenAlex,
journals hybrid in 2019 or 2024 (main sample), years 2019 and 2024.
Variants: all, hybrid, any_oa; full counting via authorships.countries. Resumable.
Input : panel_jcy.csv, journals_eligible.csv
Output: anyoa_country_journal_year.csv, anyoa_log.csv
Usage : python3 14_extract_any_oa.py
"""
import csv
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

os.chdir(os.environ.get("DATA_DIR", "data"))

BASE = "https://api.openalex.org/works"
YEARS = (2019, 2024)
VARIANTS = {"all": None, "hybrid": "open_access.oa_status:hybrid", "any_oa": "open_access.is_oa:true"}
OUT = Path("anyoa_country_journal_year.csv")
LOG = Path("anyoa_log.csv")
API_KEY = os.environ.get("OPENALEX_API_KEY", "")
EMAIL = os.environ.get("OPENALEX_EMAIL", "")
S = requests.Session()


def get(params, tries=6):
    if API_KEY:
        params["api_key"] = API_KEY
    if EMAIL:
        params["mailto"] = EMAIL
    last = ""
    for i in range(tries):
        try:
            r = S.get(BASE, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}"
            if r.status_code in (401, 403):
                sys.exit(f"HTTP {r.status_code}: check OPENALEX_API_KEY")
            if r.status_code == 429 and "budget" in r.text.lower():
                sys.exit("API daily budget exhausted; rerun later to resume")
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i)
                continue
            raise RuntimeError(last)
        except requests.RequestException as e:
            last = type(e).__name__
            time.sleep(2 ** i)
    raise RuntimeError(f"failed: {last}")


def append(path, header, rows):
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerows(rows)


def main():
    p = pd.read_csv("panel_jcy.csv", usecols=["issn_l", "year", "n_hybrid", "top50_sjr2019"])
    keep = set(p.loc[p.top50_sjr2019 & p.year.isin(YEARS) & p.n_hybrid.notna(), "issn_l"])
    j = pd.read_csv("journals_eligible.csv", dtype=str)
    j = j[j.issn_l.isin(keep)]
    done = set(pd.read_csv(LOG, dtype=str).query("status == 'ok'").issn_l) if LOG.exists() else set()
    todo = j[~j.issn_l.isin(done)]
    print(f"{len(j)} journals, {len(todo)} to run")
    for k, row in enumerate(todo.itertuples(index=False), 1):
        issns = sorted({str(v).strip() for v in (row.issn_l, row.issn1, row.issn2) if pd.notna(v) and str(v).strip()})
        src = "primary_location.source.issn:" + "|".join(issns)
        rows = []
        try:
            for year in YEARS:
                for var, extra in VARIANTS.items():
                    flt = ",".join(x for x in (src, f"publication_year:{year}", "type:article", extra) if x)
                    cursor = "*"
                    while cursor:
                        js = get({"filter": flt, "group_by": "authorships.countries", "per_page": 100, "cursor": cursor})
                        page = js.get("group_by", [])
                        for g in page:
                            key = str(g["key"]).rsplit("/", 1)[-1]
                            if key and key.lower() != "unknown":
                                rows.append((row.issn_l, year, var, key, g["count"]))
                        cursor = js.get("meta", {}).get("next_cursor") if len(page) == 100 else None
                    time.sleep(0.05)
            append(OUT, ["issn_l", "year", "variant", "iso2", "n_works"], rows)
            append(LOG, ["issn_l", "status"], [(row.issn_l, "ok")])
        except Exception as e:
            append(LOG, ["issn_l", "status"], [(row.issn_l, "error")])
            print(f"  error {row.issn_l}: {e}", flush=True)
        print(f"  {k}/{len(todo)} {row.issn_l}", flush=True)
    print("done")


if __name__ == "__main__":
    sys.exit(main())

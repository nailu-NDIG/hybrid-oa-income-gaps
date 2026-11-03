"""
Research articles per journal x year x author country from OpenAlex, 2019-2024
(full counting via authorships.countries). Variants: all articles; hybrid OA only.
Resumable: journals already in openalex_log.csv are skipped; errors are retried.
Environment: OPENALEX_API_KEY, OPENALEX_EMAIL (optional).
Outputs: openalex_country_journal_year.csv, openalex_journal_year_totals.csv, openalex_log.csv
Usage  : python3 02_extract_openalex.py --issns issns_extract.txt
"""
import argparse
import csv
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

os.chdir(os.environ.get("DATA_DIR", "data"))

BASE = "https://api.openalex.org/works"
YEARS = range(2019, 2025)
VARIANTS = {"all": None, "hybrid": "open_access.oa_status:hybrid"}
TYPES = "type:article"

OUT_COUNTS = Path("openalex_country_journal_year.csv")
OUT_TOTALS = Path("openalex_journal_year_totals.csv")
OUT_LOG = Path("openalex_log.csv")

API_KEY = os.environ.get("OPENALEX_API_KEY", "")
EMAIL = os.environ.get("OPENALEX_EMAIL", "")
SESSION = requests.Session()


class BudgetExhausted(Exception):
    pass


def get(params, tries=6):
    if API_KEY:
        params["api_key"] = API_KEY
    if EMAIL:
        params["mailto"] = EMAIL
    last = ""
    for i in range(tries):
        try:
            r = SESSION.get(BASE, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            last = f"HTTP {r.status_code}: {r.text[:300]}"
            if r.status_code == 429 and "budget" in r.text.lower():
                raise BudgetExhausted(r.text[:300])
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** i)
                continue
            raise RuntimeError(last)
        except requests.RequestException as e:
            last = f"{type(e).__name__}: {e}"[:300]
            time.sleep(2 ** i)
    raise RuntimeError(f"failed after {tries} tries; last: {last}")


def issn_filter(row):
    vals = (getattr(row, c, None) for c in ("issn_l", "issn1", "issn2"))
    issns = {str(v).strip() for v in vals if pd.notna(v) and str(v).strip()}
    return "primary_location.source.issn:" + "|".join(sorted(issns))


def done_journals():
    if not OUT_LOG.exists():
        return set()
    log = pd.read_csv(OUT_LOG, dtype=str)
    return set(log.loc[log.status != "error", "issn_l"])   # errors are retried


def append(path, header, rows):
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerows(rows)


def extract_journal(row):
    src = issn_filter(row)
    counts, totals = [], []
    gold_only = str(getattr(row, "oa_status", "")) == "Gold OA"
    variants = {"all": None} if gold_only else VARIANTS
    for year in YEARS:
        for variant, extra in variants.items():
            flt = ",".join(x for x in (src, f"publication_year:{year}", TYPES, extra) if x)
            # cursor paging over all country groups; meta.count = journal-year total
            cursor, groups, total = "*", [], None
            while cursor:
                js = get({"filter": flt, "group_by": "authorships.countries",
                          "per_page": 200, "cursor": cursor})
                if total is None:
                    total = js.get("meta", {}).get("count", 0)
                page = js.get("group_by", [])
                groups.extend(page)
                cursor = js.get("meta", {}).get("next_cursor") if len(page) == 200 else None
            totals.append((row.issn_l, year, variant, total))
            for g in groups:
                key = str(g["key"]).rsplit("/", 1)[-1]   # .../countries/BR -> BR
                if key and key.lower() != "unknown":
                    counts.append((row.issn_l, year, variant, key, g["count"]))
            time.sleep(0.05)
    return counts, totals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--journals", default="journals_eligible.csv")
    ap.add_argument("--issns", help="text file with one ISSN-L per line (subset)")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()

    j = pd.read_csv(a.journals, dtype=str)
    if a.issns:
        keep = {l.strip() for l in open(a.issns) if l.strip()}
        j = j[j.issn_l.isin(keep)]
    done = done_journals()
    todo = j[~j.issn_l.isin(done)]
    if a.limit:
        todo = todo.head(a.limit)
    print(f"{len(j)} journals selected, {len(done)} already done, {len(todo)} to run")

    for k, row in enumerate(todo.itertuples(index=False), 1):
        try:
            counts, totals = extract_journal(row)
            n_all = sum(t[3] for t in totals if t[2] == "all")
            status = "ok" if n_all > 0 else "no_works_found"
            append(OUT_COUNTS, ["issn_l", "year", "variant", "iso2", "n_works"], counts)
            append(OUT_TOTALS, ["issn_l", "year", "variant", "total_works"], totals)
            append(OUT_LOG, ["issn_l", "status", "message"], [(row.issn_l, status, n_all)])
        except BudgetExhausted:
            print(f"API budget exhausted after {k - 1} journals; rerun to resume.")
            return 0
        except Exception as e:
            append(OUT_LOG, ["issn_l", "status", "message"], [(row.issn_l, "error", str(e)[:200])])
        print(f"  {k}/{len(todo)} {row.issn_l}", flush=True)
    print("done")


if __name__ == "__main__":
    sys.exit(main())

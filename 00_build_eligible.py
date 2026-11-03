"""
Journals with a positive list APC in >= 2 years, 2019-2024.
Input : scholcommlab_apc_dataset_2019_2025-2.csv
Output: journals_eligible.csv
"""
import pandas as pd
import os

os.chdir(os.environ.get("DATA_DIR", "data"))


def main():
    s = pd.read_csv("scholcommlab_apc_dataset_2019_2025-2.csv", low_memory=False,
                    dtype={"issn1": str, "issn2": str, "issn_l": str})
    s = s[s.apc_year.between(2019, 2024) & (s.apc_usd > 0)].copy()
    s["issn_l"] = s.issn_l.fillna(s.issn1).fillna(s.issn2)
    g = (s.sort_values("record_id").groupby("issn_l")
           .agg(journal=("journal", "first"), publisher=("publisher", "first"),
                issn1=("issn1", "first"), issn2=("issn2", "first"),
                n_years=("apc_year", "nunique"),
                oa_status=("oa_status", lambda x: "|".join(sorted(set(x.fillna("unknown").astype(str))))))
           .reset_index())
    g = g[g.n_years >= 2]
    g.to_csv("journals_eligible.csv", index=False)
    print(f"journals_eligible.csv: {len(g)} journals")


if __name__ == "__main__":
    main()

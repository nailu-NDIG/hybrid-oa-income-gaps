# Income gaps in hybrid open access and transformative agreement eligibility in highly ranked journals, 2019–2024

Code for a longitudinal bibliometric analysis of hybrid open access and transformative agreement eligibility in highly ranked journals by World Bank income group.

## Inputs

All inputs are public. Scripts read and write in `data/` (override with the environment variable `DATA_DIR`). Run all scripts from the repository root.

| Input | File(s) in `data/` | How obtained |
|---|---|---|
| hoaddata, commit `24391d4` (version 0.3.1) | `hoaddata/` | `get_data.sh` |
| ESAC registry, JCT archive, commit `8f5caa7` | `jct_data/` | `get_data.sh` |
| World Bank GDP per capita, NY.GDP.PCAP.CD | `API_NY.GDP.PCAP.CD_DS2_*.csv` | `get_data.sh` (accessed October 2026) |
| World Bank historical income classification | `OGHIST.xlsx` | `get_data.sh`, from https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups (accessed October 2026) |
| ScholCommLab APC dataset, version 2 | `scholcommlab_apc_dataset_2019_2025-2.csv` | manual download, Harvard Dataverse, https://doi.org/10.7910/DVN/AZ985C |
| SCImago Journal Rank 2019, 2023, 2025 | `sjr2019.csv`, `sjr2023.csv`, `sjr2025.csv` | manual export from https://www.scimagojr.com/journalrank.php (all subject areas, journals), accessed October 2026 |
| OpenAlex extraction | `openalex_country_journal_year.csv`, `openalex_journal_year_totals.csv`, `openalex_log.csv` | `02_extract_openalex.py` (extracted October 2026); archived at https://doi.org/10.5281/zenodo.23935789 |

OpenAlex is updated continuously; to reproduce the published results, use the archived extraction and start at step 3.

## Pipeline

| Step | Script | Output |
|---|---|---|
| 0 | `00_prepare_gdp.py` | `gdp_by_year.csv` |
| 0 | `00_build_eligible.py` | `journals_eligible.csv` |
| 1 | `01_build_samples.py` | `sample_top50_by_area_sjr{2019,2023,2025}.csv`, `issns_extract.txt` |
| 2 | `02_extract_openalex.py --issns issns_extract.txt` | `openalex_*.csv` (requires `OPENALEX_API_KEY`; resumable) |
| 3 | `03_build_panel.py` | `panel_jcy.csv` |
| 4 | `04_add_agreements.py` | `panel_jcy_ta.csv`, `agreement_journal_country_year.csv` |
| 5 | `05_firstauthor_agreements.py` | `hoad_jcy.csv`, `uptake_firstauthor_*.csv`, `gap_vs_high_income.csv`, `gap_share_agreement*.csv` |
| 6 | `06_firstauthor_all_hoaddata.py` | `hoad_all_jcy.csv`, `*_all_hoad.csv` |
| 7 | `07_models.R` | `model_results.csv`, `model_info.csv`, `m4_fitted_rate_diagnostic.csv`, `uptake_by_year_income.csv`, `decomposition_2019_2024*.csv` |
| 8 | `08_models_sensitivity.R` | `model_results_sensitivity.csv` |
| 9 | `09_sensitivity_descriptives.py` | `sensitivity_samples.csv` |
| 10 | `10_figures.R` | `data/figures/fig1`–`fig4`, `fig6_models` |
| 11 | `11_figure_countries.R` | `country_oa_2024.csv`, `data/figures/fig5_country_oa` |
| 12 | `12_eligibility_list_coverage.py` | `esac_list_coverage.csv`, `gap_share_agreement_upper.csv` (broad-eligibility scenario) |
| 13 | `13_data_completeness.py` | `completeness_by_year.csv`, `ror_missing_by_income.csv`, `income_filled.csv` |

## Requirements

Python ≥ 3.10 (`requirements.txt`). R 4.5.3 with `fixest` 0.14.2, `readr`, `dplyr`, `tidyr`, `broom`, `ggplot2`, `scales`, `ggrepel`.

## Derived data

The OpenAlex extraction, analysis panels and result tables are archived at https://doi.org/10.5281/zenodo.23935789 (CC BY 4.0). Copy them into `data/` to run steps 3–13 without re-extracting.

## License

Code: MIT. Derived data: CC BY 4.0.

## Notes

- `hoad_common.py` is imported by scripts 05, 06 and 09. First-author counts use the article x first-author affiliation country as unit in numerator and denominator.
- ISSN-L `1089-5639` is excluded: its ScholCommLab record carries ISSNs of two journals.
- Shares of the gap change are computed for all groups; `share_reported` is False when the baseline gap is not positive, and the component changes are reported instead, including in sensitivity analyses.

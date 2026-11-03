# Models of 07_models.R (m1-m4, m4_pub) in samples based on SJR 2019, 2023 and 2025 ranks.
# Input : panel_jcy_ta.csv
# Output: model_results_sensitivity.csv

library(readr)
library(dplyr)
library(tidyr)
library(fixest)

setwd(Sys.getenv("DATA_DIR", "data"))

panel <- read_csv("panel_jcy_ta.csv", na = "", show_col_types = FALSE) |>
  filter(!is.na(income_group)) |>
  mutate(income_group = factor(income_group,
           levels = c("High income", "Upper-middle income",
                      "Lower-middle income", "Low income")),
         t = year - 2019)

cl <- ~issn_l + iso2
fit_sample <- function(flag) {
  main <- panel |> filter(.data[[flag]])
  hyb  <- main  |> filter(!is.na(n_hybrid), n_all > 0)
  cat("\n====", flag, ":", n_distinct(main$issn_l), "journals ====\n")
  m1 <- fepois(n_all ~ i(income_group, log_apc, ref = "High income") |
                 issn_l^year + issn_l^iso2 + iso2^year, data = main, cluster = cl)
  m2 <- fepois(n_hybrid ~ i(income_group, log_apc, ref = "High income") |
                 issn_l^year + issn_l^iso2 + iso2^year,
               offset = ~log(n_all), data = hyb, cluster = cl)
  m1_gdp <- fepois(n_all ~ log_apc:log(gdp_pc_usd) | issn_l^year + issn_l^iso2 + iso2^year,
                   data = main |> filter(!is.na(gdp_pc_usd)), cluster = cl)
  m3 <- fepois(n_hybrid ~ i(income_group, t, ref = "High income") | issn_l^year + issn_l^iso2,
               offset = ~log(n_all), data = hyb, cluster = cl)
  m4 <- fepois(n_hybrid ~ ta_journal | issn_l^year + issn_l^iso2 + iso2^year,
               offset = ~log(n_all), data = hyb, cluster = cl)
  m4_pub <- fepois(n_hybrid ~ ta_publisher | issn_l^year + issn_l^iso2 + iso2^year,
                   offset = ~log(n_all), data = hyb, cluster = cl)
  ms <- list(m1 = m1, m2 = m2, m1_gdp = m1_gdp, m3 = m3, m4 = m4, m4_pub = m4_pub)
  etable(ms, digits = 3)
  bind_rows(lapply(names(ms), function(k)
    broom::tidy(ms[[k]], conf.int = TRUE) |> mutate(model = k, nobs = nobs(ms[[k]])))) |>
    mutate(sample = flag, journals = n_distinct(main$issn_l))
}

res <- bind_rows(lapply(c("top50_sjr2019", "top50_sjr2023", "top50_sjr2025"), fit_sample))
write_csv(res, "model_results_sensitivity.csv")

cat("\nEstimate (95% CI) by sample:\n")
res |>
  mutate(est = sprintf("%.2f (%.2f to %.2f)", estimate, conf.low, conf.high)) |>
  select(model, term, sample, est) |>
  pivot_wider(names_from = sample, values_from = est) |>
  print(n = Inf, width = Inf)
cat("\nmodel_results_sensitivity.csv saved\n")

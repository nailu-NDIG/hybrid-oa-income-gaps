# Fixed-effects Poisson models (fixest). Unit: journal x country x year.
# Universe: journal-country pairs with >= 1 article in 2019-2024, all APC years
# of the journal (zeros filled). Hybrid OA models: hybrid journal-years, n_all > 0.
# Standard errors clustered by journal and country.
# Primary agreement exposure: ta_journal; ta_publisher is a sensitivity analysis.
# Input : panel_jcy_ta.csv
# Output: model_results.csv, model_info.csv, m4_fitted_rate_diagnostic.csv, uptake_by_year_income.csv,
#         decomposition_2019_2024.csv, decomposition_2019_2024_income2019.csv

library(readr)
library(dplyr)
library(tidyr)
library(fixest)

setwd(Sys.getenv("DATA_DIR", "data"))

lv <- c("High income", "Upper-middle income", "Lower-middle income", "Low income")
panel <- read_csv("panel_jcy_ta.csv", na = "", show_col_types = FALSE) |>
  filter(!is.na(income_group)) |>
  mutate(income_group = factor(income_group, levels = lv),
         income_group_2019 = factor(income_group_2019, levels = lv),
         t = year - 2019,
         nonhic = as.integer(income_group != "High income"),
         hyb_share = n_hybrid / n_all)

main <- panel |> filter(top50_sjr2019)
hyb  <- main  |> filter(!is.na(n_hybrid), n_all > 0)
cl   <- ~issn_l + iso2
fe3  <- "issn_l^year + issn_l^iso2 + iso2^year"
f    <- function(lhs, rhs, fe = fe3) as.formula(paste(lhs, "~", rhs, "|", fe))

mods <- list(
  # APC x income: participation and hybrid OA (differential contrasts vs high income)
  m1      = fepois(f("n_all", "i(income_group, log_apc, ref = 'High income')"), main, cluster = cl),
  m2      = fepois(f("n_hybrid", "i(income_group, log_apc, ref = 'High income')"),
                   hyb, offset = ~log(n_all), cluster = cl),
  m1_gdp  = fepois(f("n_all", "log_apc:log(gdp_pc_usd)"),
                   main |> filter(!is.na(gdp_pc_usd)), cluster = cl),
  # income-specific linear trends; iso2^year would absorb them
  m3      = fepois(f("n_hybrid", "i(income_group, t, ref = 'High income')", "issn_l^year + issn_l^iso2"),
                   hyb, offset = ~log(n_all), cluster = cl),
  # agreement eligibility and hybrid OA
  m4      = fepois(f("n_hybrid", "ta_journal"), hyb, offset = ~log(n_all), cluster = cl),
  m4_pub  = fepois(f("n_hybrid", "ta_publisher"), hyb, offset = ~log(n_all), cluster = cl),
  # placebo: eligibility in the following year
  m4_lead = fepois(f("n_hybrid", "ta_journal + ta_journal_lead"), hyb, offset = ~log(n_all), cluster = cl),
  # years with near-complete journal and institution lists in the registry
  m4_2022 = fepois(f("n_hybrid", "ta_journal"), hyb |> filter(year >= 2022), offset = ~log(n_all), cluster = cl),
  # difference in the eligibility association outside high-income countries
  m4_nonhic = fepois(f("n_hybrid", "ta_journal + ta_journal:nonhic"), hyb, offset = ~log(n_all), cluster = cl),
  # bounded (fractional logit) alternative: share of hybrid OA, weighted by articles
  m4_logit = feglm(f("hyb_share", "ta_journal"), hyb, family = quasibinomial(), weights = ~n_all, cluster = cl),
  m5      = fepois(f("n_hybrid", "i(income_group, t, ref = 'High income') + ta_journal",
                     "issn_l^year + issn_l^iso2"), hyb, offset = ~log(n_all), cluster = cl),
  # agreement eligibility and participation
  m6      = fepois(f("n_all", "ta_journal"), main, cluster = cl),
  m6_pub  = fepois(f("n_all", "ta_publisher"), main, cluster = cl),
  # income group fixed at 2019 classification
  m1_inc19 = fepois(f("n_all", "i(income_group_2019, log_apc, ref = 'High income')"), main, cluster = cl),
  m2_inc19 = fepois(f("n_hybrid", "i(income_group_2019, log_apc, ref = 'High income')"),
                    hyb, offset = ~log(n_all), cluster = cl),
  m3_inc19 = fepois(f("n_hybrid", "i(income_group_2019, t, ref = 'High income')", "issn_l^year + issn_l^iso2"),
                    hyb, offset = ~log(n_all), cluster = cl)
)

etable(mods[c("m1", "m2", "m1_gdp", "m3", "m4", "m4_pub", "m5", "m6", "m6_pub")], digits = 3)
etable(mods[c("m4", "m4_lead", "m4_2022", "m4_nonhic", "m4_logit")], digits = 3)

# m4: fitted hybrid OA rates above 1 (log link does not bound the proportion)
d4 <- hyb[obs(mods$m4), ]
rate4 <- fitted(mods$m4) / d4$n_all
diag4 <- tibble(obs = length(rate4), above1 = sum(rate4 > 1), share_obs = mean(rate4 > 1),
                share_articles = sum(d4$n_all[rate4 > 1]) / sum(d4$n_all), max_rate = max(rate4))
print(diag4)
write_csv(diag4, "m4_fitted_rate_diagnostic.csv")
etable(mods[c("m1_inc19", "m2_inc19", "m3_inc19")], digits = 3)

src <- list(m1 = main, m2 = hyb, m1_gdp = main |> filter(!is.na(gdp_pc_usd)), m3 = hyb,
            m4 = hyb, m4_pub = hyb, m4_lead = hyb, m4_2022 = hyb |> filter(year >= 2022), m4_nonhic = hyb, m4_logit = hyb, m5 = hyb, m6 = main, m6_pub = main,
            m1_inc19 = main, m2_inc19 = hyb, m3_inc19 = hyb)
info <- bind_rows(lapply(names(mods), function(k) {
  m <- mods[[k]]; d <- src[[k]][obs(m), ]
  tibble(model = k, nobs_input = nrow(src[[k]]), nobs = nobs(m),
         removed = nrow(src[[k]]) - nobs(m),
         journals = n_distinct(d$issn_l), countries = n_distinct(d$iso2),
         pairs = n_distinct(paste(d$issn_l, d$iso2)),
         events = if (k == "m4_logit") sum(d$n_hybrid) else sum(d[[as.character(m$fml[[2]])]]))
}))
print(info, n = Inf, width = Inf)
write_csv(info, "model_info.csv")

res <- bind_rows(lapply(mods, broom::tidy, conf.int = TRUE), .id = "model") |>
  mutate(rr = exp(estimate), rr_low = exp(conf.low), rr_high = exp(conf.high))
write_csv(res, "model_results.csv")

# ---- Descriptives -----------------------------------------------------------
uptake <- hyb |> group_by(year, income_group) |>
  summarise(articles = sum(n_all), hybrid_oa = sum(n_hybrid),
            uptake = hybrid_oa / articles,
            ta_journal_cover = sum(ta_journal * n_all) / articles,
            ta_publisher_cover = sum(ta_publisher * n_all) / articles,
            journals = n_distinct(issn_l), .groups = "drop")
write_csv(uptake, "uptake_by_year_income.csv")

# Shift-share decomposition 2019-2024, journals present in both years
decompose <- function(d, grp) {
  d |>
    filter(year %in% c(2019, 2024)) |>
    group_by(g = .data[[grp]], year, issn_l) |>
    summarise(n = sum(n_all), h = sum(n_hybrid), .groups = "drop") |>
    group_by(g, issn_l) |> filter(n_distinct(year) == 2) |>
    group_by(g, year) |> mutate(w = n / sum(n), u = h / n) |> ungroup() |>
    select(g, issn_l, year, w, u) |>
    pivot_wider(names_from = year, values_from = c(w, u)) |>
    group_by(income_group = g) |>
    summarise(journals = n(),
              uptake_2019 = sum(w_2019 * u_2019), uptake_2024 = sum(w_2024 * u_2024),
              within  = sum(w_2019 * (u_2024 - u_2019)),
              between = sum((w_2024 - w_2019) * u_2019),
              interaction = sum((w_2024 - w_2019) * (u_2024 - u_2019)))
}
decomp <- decompose(hyb, "income_group")
print(decomp)
write_csv(decomp, "decomposition_2019_2024.csv")
write_csv(decompose(hyb, "income_group_2019"), "decomposition_2019_2024_income2019.csv")
cat("saved model_results.csv, model_info.csv, uptake_by_year_income.csv, decomposition files\n")

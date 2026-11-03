# Figure 5: first-author hybrid OA in 2024 by country vs agreement coverage.
# Coverage (x) does not depend on OA status: share of the country's first-author
# articles in main-sample hybrid journals that list the journal in an agreement
# active in the country in 2024 (ta_journal), weighted by first-author articles.
# Countries with >= 300 first-author article-country units.
# Inputs: hoad_jcy.csv, panel_jcy_ta.csv, agreement_journal_country_year.csv
# Output: country_oa_2024.csv, figures/fig5_country_oa.(pdf|png)

library(readr)
library(dplyr)
library(ggplot2)
library(scales)
library(ggrepel)

setwd(Sys.getenv("DATA_DIR", "data"))

dir.create("figures", showWarnings = FALSE)
MIN_ARTICLES <- 300
groups <- c("High income", "Upper-middle income", "Lower-middle income", "Low income")
cols   <- c("High income" = "#0072B2", "Upper-middle income" = "#E69F00",
            "Lower-middle income" = "#009E73", "Low income" = "#CC79A7")

p <- read_csv("panel_jcy_ta.csv", na = "", show_col_types = FALSE,
              col_select = c(issn_l, iso2, year, ta_journal, ta_publisher, gdp_pc_usd)) |>
  filter(year == 2024)
jcy <- read_csv("agreement_journal_country_year.csv", na = "", show_col_types = FALSE) |>
  filter(year == 2024) |> select(issn_l, iso2, ta_journal)
pub <- p |> distinct(issn_l, iso2, ta_publisher)
h <- read_csv("hoad_jcy.csv", na = "", show_col_types = FALSE) |>
  filter(top50_sjr2019, year == 2024) |>
  left_join(jcy, by = c("issn_l", "iso2")) |>
  left_join(pub, by = c("issn_l", "iso2")) |>
  mutate(across(c(ta_journal, ta_publisher), ~ coalesce(.x, 0)))
gdp <- p |> filter(!is.na(gdp_pc_usd)) |> distinct(iso2, gdp_pc_usd)

cty <- h |>
  group_by(iso2, income_group) |>
  summarise(coverage_pct = 100 * sum(ta_journal * articles) / sum(articles),
            coverage_pub_pct = 100 * sum(ta_publisher * articles) / sum(articles),
            articles = sum(articles), oa = sum(oa), oa_ta = sum(oa_ta), .groups = "drop") |>
  filter(articles >= MIN_ARTICLES) |>
  mutate(oa_pct = 100 * oa / articles, ta_pct = 100 * oa_ta / articles,
         income_group = factor(income_group, groups)) |>
  left_join(gdp, by = "iso2") |>
  arrange(desc(oa_pct))
write_csv(cty, "country_oa_2024.csv")

cat("\nCountries:", nrow(cty), "\n")
print(cty |> group_by(income_group) |>
        summarise(n = n(), median_cov = median(coverage_pct), median_oa = median(oa_pct),
                  min_oa = min(oa_pct), max_oa = max(oa_pct)))
cat("\nHigh income, coverage < 20% vs >= 50% (median hybrid OA):\n")
print(cty |> filter(income_group == "High income") |>
        mutate(cov = cut(coverage_pct, c(-Inf, 20, 50, Inf), right = FALSE)) |>
        group_by(cov) |> summarise(n = n(), median_oa = median(oa_pct)))
cat("\nSpearman (coverage, hybrid OA), high income:",
    with(filter(cty, income_group == "High income"), cor(coverage_pct, oa_pct, method = "spearman")), "\n")
cat("\nNon-high-income countries:\n")
print(cty |> filter(income_group != "High income") |>
        select(iso2, income_group, articles, coverage_pct, oa_pct, ta_pct) |>
        mutate(across(ends_with("pct"), ~ round(.x, 1))), n = Inf)

label_iso <- c("ZA", "TR", "CO", "MX", "CN", "IN", "BR", "IR", "EG", "ET", "UG",
               "RU", "SG", "CL", "SA", "KR", "US", "NL", "SE", "DE", "GB", "FI", "JP", "AT")
cty <- cty |> mutate(lab = ifelse(iso2 %in% label_iso, iso2, NA))

f5 <- ggplot(cty, aes(coverage_pct, oa_pct)) +
  geom_point(aes(fill = income_group, size = articles), shape = 21, colour = "white",
             stroke = 0.4, alpha = 0.9) +
  geom_text_repel(aes(label = lab), size = 2.6, colour = "grey15", min.segment.length = 0.2,
                  box.padding = 0.35, seed = 1, na.rm = TRUE) +
  scale_x_continuous(labels = function(x) paste0(x, "%"), limits = c(0, 100),
                     expand = expansion(mult = c(0.02, 0.02))) +
  scale_y_continuous(labels = function(x) paste0(x, "%"), limits = c(0, NA),
                     expand = expansion(mult = c(0, 0.05))) +
  scale_fill_manual(values = cols, name = NULL, guide = guide_legend(override.aes = list(size = 3))) +
  scale_size_area(max_size = 9, breaks = c(1000, 10000, 100000), labels = comma,
                  name = "First-author\nunits",
                  guide = guide_legend(override.aes = list(fill = "grey60"))) +
  labs(x = "First-author units in journals listed in an agreement active in the country, 2024",
       y = "First-author units published as hybrid OA, 2024") +
  theme_minimal(base_size = 9) +
  theme(panel.grid.minor = element_blank(),
        axis.line = element_line(colour = "grey40", linewidth = 0.3),
        legend.position = "right")

ggsave("figures/fig5_country_oa.pdf", f5, width = 7, height = 4.6, device = cairo_pdf)
ggsave("figures/fig5_country_oa.png", f5, width = 7, height = 4.6, dpi = 600, bg = "white")
cat("\nsaved figures/fig5_country_oa\n")

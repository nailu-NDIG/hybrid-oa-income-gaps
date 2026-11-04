# Figures 1-4 and 6.
# Inputs: panel_jcy_ta.csv, hoad_jcy.csv, openalex_log.csv, uptake_firstauthor_by_year_income.csv,
#         gap_vs_high_income.csv, gap_share_agreement.csv, model_results.csv,
#         journals_eligible.csv, sample_top50_by_area_sjr2019.csv
# Output: figures/

library(readr)
library(dplyr)
library(tidyr)
library(ggplot2)
library(scales)

setwd(Sys.getenv("DATA_DIR", "data"))

dir.create("figures", showWarnings = FALSE)

groups <- c("High income", "Upper-middle income", "Lower-middle income", "Low income")
short  <- c("High income" = "High", "Upper-middle income" = "Upper-middle",
            "Lower-middle income" = "Lower-middle", "Low income" = "Low")
cols   <- c("High income" = "#0072B2", "Upper-middle income" = "#E69F00",
            "Lower-middle income" = "#009E73", "Low income" = "#CC79A7")
ta_col <- "#0072B2"; other_col <- "#9ECAE1"

theme_set(theme_minimal(base_size = 9) +
            theme(panel.grid.minor = element_blank(),
                  panel.grid.major.x = element_blank(),
                  axis.line = element_line(colour = "grey40", linewidth = 0.3),
                  legend.position = "bottom",
                  plot.title.position = "plot"))

save_fig <- function(p, name, w, h) {
  ggsave(file.path("figures", paste0(name, ".pdf")), p, width = w, height = h, device = cairo_pdf)
  ggsave(file.path("figures", paste0(name, ".png")), p, width = w, height = h, dpi = 600, bg = "white")
  cat("saved", name, "\n")
}

panel <- read_csv("panel_jcy_ta.csv", na = "", show_col_types = FALSE) |>
  filter(top50_sjr2019)

# ---- Figure 1: flow (counts) -------------------------------------------------
n_elig   <- nrow(read_csv("journals_eligible.csv", col_types = cols(.default = "c"), show_col_types = FALSE))  # one row per journal
n_sample <- n_distinct(read_csv("sample_top50_by_area_sjr2019.csv", show_col_types = FALSE)$issn_l)
n_j      <- n_distinct(panel$issn_l)
n_c      <- panel |> filter(n_all > 0, !is.na(income_group)) |> distinct(iso2) |> nrow()
n_h      <- panel |> filter(oa_status_year == "Hybrid OA") |> distinct(issn_l) |> nrow()
n_oa     <- read_csv("openalex_log.csv", show_col_types = FALSE) |>
  filter(status == "ok", issn_l %in% read_csv("sample_top50_by_area_sjr2019.csv", show_col_types = FALSE)$issn_l) |>
  nrow()
n_fa     <- read_csv("hoad_jcy.csv", na = "", show_col_types = FALSE) |>
  filter(top50_sjr2019) |> distinct(issn_l) |> nrow()
cat("\nFigure 1 counts:", n_elig, n_sample, n_oa, n_j, n_c, n_h, n_fa, "\n")

boxes <- tibble(
  x = 1, y = 4:1,
  label = c(sprintf("ScholCommLab APC dataset v2\nAPC in ≥2 years, 2019–2024\nn = %s", comma(n_elig)),
            sprintf("Top 50 by SCImago Journal Rank 2019\namong journals with APC data\nin each of 27 subject areas\nn = %s", comma(n_sample)),
            sprintf("With research articles in OpenAlex: n = %s\nAnalysed: n = %s journals, %s countries\n(excluded: 1 ISSN shared by two journals,\n1 without author country)", comma(n_oa), comma(n_j), n_c),
            sprintf("Hybrid in ≥1 year: n = %s\nwith first-author data (hoaddata): n = %s", comma(n_h), comma(n_fa))))
srcs <- tibble(
  x = 1.95, y = seq(4.2, 0.8, length.out = 5),
  label = c("OpenAlex\narticles by author country, journal, year; OA status",
            "ScholCommLab\nlist APC per journal-year",
            "hoaddata\nfirst-author institution (ROR) for CC-licensed articles",
            "ESAC registry (JCT archive)\nagreements: publisher, journals, institutions, years",
            "World Bank\nGDP per capita; historical income group (OGHIST)"))
f1 <- ggplot() +
  geom_segment(aes(x = 1, xend = 1, y = 3.66, yend = 3.42), data = NULL,
               arrow = arrow(length = unit(2, "mm")), colour = "grey40") +
  geom_segment(aes(x = 1, xend = 1, y = 2.60, yend = 2.42),
               arrow = arrow(length = unit(2, "mm")), colour = "grey40") +
  geom_segment(aes(x = 1, xend = 1, y = 1.58, yend = 1.30),
               arrow = arrow(length = unit(2, "mm")), colour = "grey40") +
  geom_segment(data = srcs, aes(x = x - 0.05, xend = 1.4, y = y, yend = 2),
               arrow = arrow(length = unit(2, "mm")), colour = "grey40") +
  geom_label(data = boxes, aes(x, y, label = label), size = 2.7, label.padding = unit(3, "mm"),
             fontface = c("plain", "plain", "bold", "plain"), fill = "white") +
  geom_label(data = srcs, aes(x, y, label = label), size = 2.5, label.padding = unit(2.5, "mm"), hjust = 0,
             fill = "#f4f7fb", colour = "grey15") +
  annotate("text", x = c(1, 2.5), y = 4.75, label = c("Journal selection", "Data sources"),
           fontface = "bold", size = 3.2) +
  xlim(0.3, 3.1) + ylim(0.4, 4.9) + theme_void()
save_fig(f1, "fig1_flow", 7.2, 4.8)

# ---- Figure 2: APC burden, 2019 vs 2024 ---------------------------------------
burden <- panel |>
  filter(n_all > 0, !is.na(gdp_pc_usd), !is.na(income_group), year %in% c(2019, 2024)) |>
  mutate(b = 100 * apc_usd / gdp_pc_usd) |>
  group_by(income_group, year) |>
  summarise(lo = quantile(b, .25), md = median(b), hi = quantile(b, .75), .groups = "drop") |>
  mutate(income_group = factor(income_group, groups), year = factor(year))
cat("\nFigure 2 (median, IQR, % of GDP per capita):\n"); print(burden, n = Inf)

f2 <- ggplot(burden, aes(income_group, md, colour = income_group, shape = year)) +
  geom_hline(yintercept = 100, linetype = "dashed", colour = "grey40") +
  annotate("text", x = 0.55, y = 88, label = "100% = one year of GDP per capita",
           hjust = 0, size = 2.6, colour = "grey35") +
  geom_linerange(aes(ymin = lo, ymax = hi), position = position_dodge(width = 0.45), linewidth = 0.9) +
  geom_point(position = position_dodge(width = 0.45), size = 2.6, fill = "white", stroke = 1.1) +
  geom_text(aes(label = ifelse(md < 10, sprintf("%.1f%%", md), sprintf("%.0f%%", md)),
                hjust = ifelse(year == "2019", 1.5, -0.5)),
            position = position_dodge(width = 0.45), size = 2.6, colour = "grey10", show.legend = FALSE) +
  scale_shape_manual(values = c("2019" = 21, "2024" = 15), name = "Median and IQR") +
  scale_colour_manual(values = cols, guide = "none") +
  scale_x_discrete(labels = short) +
  scale_y_log10(breaks = c(3, 10, 30, 100, 300, 1000), labels = function(x) paste0(x, "%")) +
  labs(x = NULL, y = "List APC as % of GDP per capita (log scale)") +
  theme(legend.position = c(0.12, 0.88))
save_fig(f2, "fig2_apc_burden", 6, 3.8)

# ---- Figure 3: first-author hybrid OA, agreement eligibility vs other -----------------------
up <- read_csv("uptake_firstauthor_by_year_income.csv", show_col_types = FALSE) |>
  mutate(income_group = factor(income_group, groups))
cat("\nFigure 3 (first-author hybrid OA, %):\n")
print(up |> transmute(year, income_group, articles, oa = round(100 * oa_rate, 1),
                      agreement_eligible = round(100 * ta_oa_rate, 1)) |> arrange(income_group, year), n = Inf)

nlab <- up |> group_by(income_group) |>
  summarise(lab = sprintf("n = %s–%s per year", comma(min(articles)), comma(max(articles))))
long3 <- up |>
  transmute(year, income_group,
            `With identified eligibility` = 100 * ta_oa_rate,
            `Without identified eligibility` = 100 * other_oa_rate) |>
  pivot_longer(-c(year, income_group), names_to = "route", values_to = "pct") |>
  mutate(route = factor(route, c("Without identified eligibility", "With identified eligibility")))
ends <- up |> filter(year == 2024) |> mutate(lab = sprintf("%.1f%%", 100 * oa_rate))

f3 <- ggplot(long3, aes(year, pct)) +
  geom_area(aes(fill = route)) +
  geom_line(data = up, aes(year, 100 * oa_rate), colour = "grey10", linewidth = 0.5) +
  geom_text(data = ends, aes(2024, 100 * oa_rate, label = lab), vjust = -0.6, hjust = 1, size = 2.6) +
  geom_text(data = nlab, aes(2019, 49, label = lab), hjust = 0, size = 2.2, colour = "grey35") +
  facet_wrap(~income_group, nrow = 1) +
  scale_fill_manual(values = c("With identified eligibility" = ta_col, "Without identified eligibility" = other_col),
                    breaks = c("With identified eligibility", "Without identified eligibility"), name = NULL) +
  scale_x_continuous(breaks = c(2019, 2021, 2024), expand = expansion(add = c(0.35, 0.35))) +
  scale_y_continuous(limits = c(0, 50), breaks = seq(0, 40, 10), labels = function(x) paste0(x, "%"), expand = c(0, 0)) +
  labs(x = NULL, y = "First-author article-country units\npublished as hybrid OA (%)") +
  theme(panel.spacing = unit(6, "mm"), strip.text = element_text(hjust = 0, size = 9))
save_fig(f3, "fig3_uptake_firstauthor", 7.4, 3)

# ---- Figure 4: gap vs high income, by route ---------------------------------
gap <- read_csv("gap_vs_high_income.csv", show_col_types = FALSE) |>
  mutate(group = factor(group, groups[-1]))
share <- read_csv("gap_share_agreement.csv", show_col_types = FALSE) |>
  mutate(group = factor(group, groups[-1]))
cat("\nFigure 4 (gap, percentage points; share of widening via agreements):\n")
print(gap |> mutate(across(starts_with("gap"), ~ round(100 * .x, 1))))
print(share |> mutate(share = percent(share_agreement, 1)))

long4 <- gap |>
  transmute(group, year = factor(year),
            `With identified eligibility` = 100 * gap_agreement, `Without identified eligibility` = 100 * gap_other) |>
  pivot_longer(-c(group, year), names_to = "route", values_to = "pp") |>
  mutate(route = factor(route, c("Without identified eligibility", "With identified eligibility")))
# net gap: black point at its value
tot4 <- gap |> mutate(year = factor(year), lab = sub("-", "\u2212", sprintf("%.1f", 100 * gap_total)))
strip4 <- setNames(ifelse(share$share_reported,
                          sprintf("%s\nidentified eligibility: %s of change",
                                  short[as.character(share$group)], percent(share$share_agreement, 1)),
                          sprintf("%s\nwith identified eligibility %s pp,\nwithout %s pp",
                                  short[as.character(share$group)], sub("-", "\u2212", sprintf("%+.1f", 100 * share$d_gap_agreement)),
                                  sub("-", "\u2212", sprintf("%+.1f", 100 * share$d_gap_other)))),
                   share$group)

f4 <- ggplot(long4, aes(year, pp, fill = route)) +
  geom_hline(yintercept = 0, colour = "grey40", linewidth = 0.3) +
  geom_col(width = 0.7, colour = "white", linewidth = 0.4) +
  geom_point(data = tot4, aes(year, 100 * gap_total), inherit.aes = FALSE,
             shape = 23, size = 2.2, fill = "black", colour = "white", stroke = 0.4) +
  geom_label(data = tot4, aes(year, 100 * gap_total, label = lab), inherit.aes = FALSE,
             vjust = -0.45, size = 2.4, label.size = 0, fill = "white", alpha = 0.85,
             label.padding = unit(0.6, "mm")) +
  facet_wrap(~group, nrow = 1, strip.position = "bottom", labeller = as_labeller(strip4)) +
  scale_fill_manual(values = c("With identified eligibility" = ta_col, "Without identified eligibility" = other_col),
                    breaks = c("With identified eligibility", "Without identified eligibility"), name = NULL) +
  scale_y_continuous(expand = expansion(mult = c(0.05, 0.1))) +
  labs(x = NULL, y = "Gap in first-author hybrid OA\nvs high income (percentage points)",
       caption = "Diamonds: net gap (sum of the two components).") +
  theme(strip.placement = "outside", legend.position = "top",
        plot.caption = element_text(size = 7, colour = "grey30", hjust = 0))
save_fig(f4, "fig4_gap_decomposition", 6, 3.8)

# ---- Figure 6 --------------------------------------------------------------
res <- read_csv("model_results.csv", show_col_types = FALSE)
pick <- function(model, pattern, panel_lab) {
  res |> filter(model == !!model, grepl(pattern, term)) |>
    mutate(panel = panel_lab,
           label = case_when(grepl("Upper-middle", term) ~ "Upper-middle",
                             grepl("Lower-middle", term) ~ "Lower-middle",
                             grepl("Low income", term) ~ "Low",
                             model == "m4" ~ "Journal listed (main)",
                             model == "m4_pub" ~ "Publisher covered",
                             model == "m4_2022" ~ "Journal listed, 2022\u20132024",
                             term == "ta_journal_lead" ~ "Next-year eligibility (lead)",
                             TRUE ~ term))
}
f6 <- bind_rows(pick("m1", "log_apc", "A. Participation: log APC × income group"),
                pick("m2", "log_apc", "B. Hybrid OA: log APC × income group"),
                pick("m4", "ta_journal", "C. Hybrid OA: agreement coverage (journal\u2013country\u2013year)"),
                pick("m4_pub", "ta_publisher", "C. Hybrid OA: agreement coverage (journal\u2013country\u2013year)"),
                pick("m4_2022", "ta_journal", "C. Hybrid OA: agreement coverage (journal\u2013country\u2013year)"),
                pick("m4_lead", "ta_journal_lead", "C. Hybrid OA: agreement coverage (journal\u2013country\u2013year)")) |>
  mutate(label = factor(label, rev(c("Upper-middle", "Lower-middle", "Low", "Journal listed (main)",
                                     "Publisher covered", "Journal listed, 2022\u20132024",
                                     "Next-year eligibility (lead)"))),
         ci = sprintf("%.2f (%.2f to %.2f)", estimate, conf.low, conf.high))
cat("\nFigure 6 (coefficients, 95% CI):\n"); print(f6 |> select(panel, label, ci))

f_6 <- ggplot(f6, aes(estimate, label, colour = label)) +
  geom_vline(xintercept = 0, colour = "grey40") +
  geom_linerange(aes(xmin = conf.low, xmax = conf.high), linewidth = 0.9) +
  geom_point(size = 2.2) +
  geom_text(aes(x = 1.15, label = sprintf("%.2f (%.2f\u2013%.2f)", exp(estimate), exp(conf.low), exp(conf.high))),
            hjust = 0, size = 2.5, colour = "grey10") +
  facet_wrap(~panel, ncol = 1, scales = "free_y") +
  scale_colour_manual(values = c("Upper-middle" = cols[[2]], "Lower-middle" = cols[[3]], "Low" = cols[[4]]),
                      na.value = ta_col, guide = "none") +
  coord_cartesian(xlim = c(-1, 1.15), clip = "off") +
  labs(x = "Coefficient (log scale; 95% CI, two-way clustered); right: exponentiated\nA–B: difference in APC slope vs high income (ratio of rate ratios); C: rate ratio", y = NULL) +
  theme(strip.text = element_text(hjust = 0, face = "bold"), panel.grid.major.y = element_blank(),
        plot.margin = margin(5.5, 95, 5.5, 5.5))
save_fig(f_6, "fig6_models", 6.4, 5)

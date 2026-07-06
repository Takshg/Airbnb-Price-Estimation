# Data analysis guide (DATA 407 project report — Section 3)

This README maps the **Data Analysis** section of the project report to **where the numbers, tables, and figures live** in this repository: which files to open, which cells produce which outputs, and how figures relate to **Figure 1–7** in the report.

---

## Quick reference: main artifacts

| Role | File |
|------|------|
| **Analysis population** (N = 4,702 listings, `price`, `neighbourhood`, etc.) | [`analysis_dataset.csv`](analysis_dataset.csv) |
| **Exploratory analysis, skewness, outliers, stratum context, Figures 1–3** | [`EDA.ipynb`](EDA.ipynb) |
| **Sampling formulas, allocations, single run, Monte Carlo, bootstrap, sensitivity, Tables 4–8** | [`sampling_simulation.ipynb`](sampling_simulation.ipynb) |
| **Shared estimators / simulation code** | [`sampling_core.py`](sampling_core.py) |
| **Report-style plots: sampling distributions, boxplots, coverage, sensitivity (Figures 4–7 + extras)** | [`sampling_results_analysis.ipynb`](sampling_results_analysis.ipynb) |
| **Workflow and DEFF / coverage narrative** | [`SAMPLING_WORKFLOW_AND_CHANGELOG.md`](SAMPLING_WORKFLOW_AND_CHANGELOG.md) |

---

## Section 3.1 — Population definition and cleaning (Table 1)

**What the report describes:** Final finite population N = 4,702, 23 strata, n = 300, outcome `price`, stratification `neighbourhood`, negligible missing prices at the end of cleaning.

**Where to find it**

- **Underlying table:** [`analysis_dataset.csv`](analysis_dataset.csv) — one row per listing used as the population.
- **How cleaning and missingness are documented:** [`EDA.ipynb`](EDA.ipynb) (data construction, missing price handling, and transition to the analysis file).
- **Same N and column checks in code:** [`sampling_simulation.ipynb`](sampling_simulation.ipynb) — **§1 Setup** (load CSV, print row count and columns) and **§2 Population definitions** (N, number of strata, ∑N_h).

**Table 1** is a summary you can reproduce from those cells plus the EDA narrative.

---

## Section 3.2 — Exploratory results on nightly price (Table 2, Figures 1–2)

**What the report describes:** Strong right skew; mean ≈ 219.76, median 158, SD ≈ 650, range and quartiles; **Figure 1** distribution; **Figure 2** boxplot.

**Where to find it**

- **Primary:** [`EDA.ipynb`](EDA.ipynb) — sections that summarize `price` on the cleaned/analysis population and plot **histogram / KDE** and **boxplot** of nightly price. Search the notebook for plots titled along the lines of distribution and boxplot of nightly prices (and any zoomed or capped variants the report used).
- **Exact population mean for simulation:** Printed in [`sampling_simulation.ipynb`](sampling_simulation.ipynb) Monte Carlo section as the **true finite-population mean** (should match 219.7561 up to rounding).

**Table 2** = descriptive statistics from the same population as `analysis_dataset.csv` (computed in EDA or a short `pandas` summary on that CSV).

---

## Section 3.3 — Outliers and auxiliary-variable check (Table 3, Figure 3)

**What the report describes:** IQR fence, count/percent flagged; correlation price vs `number_of_reviews` ≈ −0.016; **Figure 3** scatter of price vs reviews.

**Where to find it**

- **Primary:** [`EDA.ipynb`](EDA.ipynb) — IQR outlier logic, summary table, and **price vs number of reviews** scatter (report cites r = −0.016).
- **Column used later:** `price_outlier_iqr` appears in [`analysis_dataset.csv`](analysis_dataset.csv) and is used in sensitivity in [`sampling_simulation.ipynb`](sampling_simulation.ipynb) **§6** / [`sampling_core.py`](sampling_core.py) (`run_all_sensitivity_scenarios`).

---

## Section 3.4 — Neighbourhood structure and allocation (Table 4, Table 5)

**What the report describes:** Example stratum rows (Downtown, Kitsilano, …) with N_h, means, S_h, W_h; **Table 5** proportional vs Neyman n_h for selected neighbourhoods; ∑n_h = 300, min n_h per rule.

**Where to find it**

- **Stratum table (full population by neighbourhood):** Built in [`sampling_simulation.ipynb`](sampling_simulation.ipynb) **§2** as `stratum_stats` (same structure as Table 4-style summaries). [`EDA.ipynb`](EDA.ipynb) also has **stratum summary** tables and barplots (**stratum sizes** and **within-stratum variability**) that support the narrative but are **population** N_h and S_h, not sample allocations.
- **Allocation numbers (Table 5):** [`sampling_simulation.ipynb`](sampling_simulation.ipynb) **§4 — Allocation and one real sample run** — code builds `alloc_df` with `n_prop` and `n_neyman` per `neighbourhood` and prints **Allocation checks** and the top rows of `alloc_df`. That output matches the report’s “selected allocation results.”
- **Implementation:** [`sampling_core.py`](sampling_core.py) — `proportional_allocation`, `neyman_allocation`, `build_stratum_stats`.

**Note:** The report’s **“Comparison of neighbourhood sample allocations under proportional and Neyman designs”** is reflected as this **§4 printed table** (and any figure you exported from it). [`sampling_results_analysis.ipynb`](sampling_results_analysis.ipynb) does **not** currently plot side-by-side n_h by neighbourhood; it only **computes** allocations for the simulation.

---

## Section 3.5 — Single-sample comparison (Table 6)

**What the report describes:** One draw each for SRS, proportional stratified, Neyman stratified: estimate, SE, 95% CI, single-run DEFF.

**Where to find it**

- **Primary:** [`sampling_simulation.ipynb`](sampling_simulation.ipynb) **§4** — after allocations, the cell that draws `sample_srs`, `sample_prop`, `sample_neyman` and prints **`one_run`** (DataFrame with `estimate`, `var_hat`, `se`, `df`, `ci_low`, `ci_high`, `DEFF`).

**Reproducibility:** Values match a **specific RNG state** after earlier cells (setup, allocations, one-shot draws). Re-running the whole notebook from the top reproduces a coherent draw; numbers may differ from an old PDF if the seed or code path changed.

---

## Section 3.6 — Monte Carlo results (Table 7, Figures 4–6)

**What the report describes:** B = 1,000; true mean; coverage, DEFF_emp, n_eff by design; **Figure 4** sampling distributions of the estimated mean; **Figure 5** spread (boxplot); **Figure 6** empirical coverage vs nominal 95%.

**Where to find it**

- **Tables and printed summaries (Table 7 style):** [`sampling_simulation.ipynb`](sampling_simulation.ipynb) **§5 Monte Carlo** — uses `run_monte_carlo` from [`sampling_core.py`](sampling_core.py) and `print_monte_carlo_summary` (outputs `mc_summary`, `deff_rep`, etc.).
- **Figures 4–6:** [`sampling_results_analysis.ipynb`](sampling_results_analysis.ipynb):
  - **Figure 4** → overlapping **histograms** of `mc["estimate"]` by method, with vertical line at true mean (*Monte Carlo distribution of estimates by design*).
  - **Figure 5** → **boxplot** by method (*Spread of estimates across replications*).
  - **Figure 6** → **bar chart** of `coverage_95` with horizontal line at 0.95.

**Extra plots in the same notebook (useful for the report narrative but not always numbered in the PDF):**

- Grouped bars: **empirical variance vs mean plug-in variance** (`empirical_var` vs `avg_theoretical_var`).
- **DEFF_emp** bar chart by method.
- **log₁₀** histograms of per-replication **DEFF_hat** (stratified designs).

**Important:** [`sampling_results_analysis.ipynb`](sampling_results_analysis.ipynb) uses a **fresh** RNG from the documented seed for its Monte Carlo block (it does **not** replay the single-sample and bootstrap draws from `sampling_simulation.ipynb`). So **Table 7 numbers in a saved PDF may not exactly match** a fresh run of the analysis notebook, even though **qualitative conclusions** (Neyman efficiency, undercoverage) should align. For numbers that match **one full run** of the main pipeline, use **`sampling_simulation.ipynb` §5** outputs.

---

## Section 3.7 — Bootstrap diagnostic

**What the report describes:** Percentile bootstrap for SRS mean; e.g. 300 outer samples × 400 bootstrap resamples; coverage below 0.95.

**Where to find it**

- **Only in:** [`sampling_simulation.ipynb`](sampling_simulation.ipynb) **optional SRS bootstrap** cell (function `bootstrap_srs_mean_ci` and the loop printing coverage). Not exported to `sampling_core.py` by design.

---

## Section 3.8 — Sensitivity analysis (Table 8, Figure 7)

**What the report describes:** Three scenarios — main, cap at $5,000, exclude IQR-flagged outliers; estimates and CIs by design; **Figure 7** comparison of point estimates across scenarios.

**Where to find it**

- **Table 8 (values):** [`sampling_simulation.ipynb`](sampling_simulation.ipynb) **§6 Sensitivity** — `run_all_sensitivity_scenarios` → printed **`sens`** DataFrame (`scenario`, `method`, `estimate`, `se`, `ci_low`, `ci_high`).
- **Figure 7:** [`sampling_results_analysis.ipynb`](sampling_results_analysis.ipynb) — **grouped bar chart** *Single-sample estimates by scenario and design* (after the same sensitivity function, using the RNG **after** the analysis notebook’s Monte Carlo block).

Again, **exact point estimates** for sensitivity depend on RNG position; align notebooks and run order if you need strict reproducibility with the PDF.

---

## Section 3.9 — Summary of findings

**Where to find the supporting material:** Same as above — EDA for skewness and tails; `sampling_simulation.ipynb` for design comparison and sensitivity; `sampling_results_analysis.ipynb` for visualization; [`SAMPLING_WORKFLOW_AND_CHANGELOG.md`](SAMPLING_WORKFLOW_AND_CHANGELOG.md) for DEFF definitions and coverage discussion.

---

## How to regenerate outputs

From the project root (with dependencies installed: `pandas`, `numpy`, `matplotlib`, `scipy`, `jupyter`):

```bash
jupyter nbconvert --to notebook --execute EDA.ipynb --inplace
jupyter nbconvert --to notebook --execute sampling_simulation.ipynb --inplace
jupyter nbconvert --to notebook --execute sampling_results_analysis.ipynb --inplace
```

Or run all cells in order in Jupyter / VS Code.

---

## Figure index (report ↔ repository)

| Report | Topic | Repository location |
|--------|--------|---------------------|
| **Figure 1** | Price distribution | [`EDA.ipynb`](EDA.ipynb) |
| **Figure 2** | Price boxplot | [`EDA.ipynb`](EDA.ipynb) |
| **Figure 3** | Price vs reviews | [`EDA.ipynb`](EDA.ipynb) |
| **Figure 4** | Sampling distributions of mean | [`sampling_results_analysis.ipynb`](sampling_results_analysis.ipynb) (histograms) |
| **Figure 5** | Spread of estimates | [`sampling_results_analysis.ipynb`](sampling_results_analysis.ipynb) (boxplot) |
| **Figure 6** | CI coverage by design | [`sampling_results_analysis.ipynb`](sampling_results_analysis.ipynb) (coverage bars) |
| **Figure 7** | Sensitivity scenario comparison | [`sampling_results_analysis.ipynb`](sampling_results_analysis.ipynb) (grouped bars) |

---

# Sampling & simulation work — full flow and changelog

This document records the **end-to-end workflow** for the DATA 407–style sampling analysis on Vancouver Airbnb listing prices, the **consolidated deliverable** (`sampling_simulation.ipynb`), and the **main changes and decisions** made from initial goals through the current state.

---

## 1. Starting point

### 1.1 Project goal (proposal-aligned)

- Estimate the **finite-population mean nightly listing price** using:
  - **Simple random sampling (SRS)** without replacement,
  - **Stratified random sampling** with **proportional** and **Neyman** allocation,
  - **Monte Carlo simulation** to study variance, **design effect (DEFF)**, **confidence interval coverage**, and related diagnostics,
  - **Sensitivity analyses** (price cap, outlier handling).

### 1.2 What we deliberately did *not* code

- **Ratio estimation** (e.g. price vs reviews as auxiliary) is **omitted**. Exploratory data analysis showed a **weak** relationship between price and `number_of_reviews`, so ratio estimation was not pursued in code; any report should **state this omission** briefly.

### 1.3 Consolidated plan (reference only)

A consolidated execution plan was written under `.cursor/plans/sampling_and_simulation_execution.plan.md` (single notebook, formulas aligned with course notes, **t**-based CIs where appropriate, math audit, sensitivity). The **implementation source of truth** is the notebook, not the plan file.

---

## 2. Data and alignment with EDA

| Item | Locked-in choice |
|------|------------------|
| **Analysis file** | `analysis_dataset.csv` at the project root |
| **Population size** | **N = 4,702** listings with observed price (missing prices excluded in EDA) |
| **Outcome** | `price` |
| **Stratification** | **`neighbourhood`** — **23** strata |
| **Outliers** | **Main analysis:** full prices. **Sensitivity:** cap at **$5,000**; optional exclusion using **`price_outlier_iqr`** |
| **Sample size** | **n = 300** for the primary single-run and Monte Carlo designs |

The notebook asserts basic consistency checks (e.g. \(\sum_h N_h = N\)).

---

## 3. Deliverable: notebook structure (`sampling_simulation.ipynb`)

All sampling and simulation logic lives in **one notebook**, in order:

1. **Setup** — Imports (`numpy`, `pandas`; `scipy.stats.t` if available for **t** critical values), fixed RNG seed, load CSV, column names (`STRATA_COL`, `Y_COL`, etc.).
2. **Population definitions** — Build `population`, `stratum_stats` with \(N_h\), stratum means, stratum SDs \(S_h\), weights \(W_h\).
3. **Estimators and allocation helpers** — Pure functions + markdown with formulas:
   - **SRS:** \(\hat{\bar{Y}} = \bar{y}\); \(\widehat{\mathrm{Var}}(\bar{y}) = (1-f)s^2/n\), \(f=n/N\); **95% CI** using **t** on **df = n − 1** when SciPy is available.
   - **Stratified:** combined mean \(\sum_h W_h \bar{y}_h\); variance \(\sum_h W_h^2(1-f_h)s_h^2/n_h\); **t** critical value using a **Satterthwaite-style effective df**, **capped** so df does not behave like a **z**-interval (details implemented in `stratified_estimate`).
4. **Allocation and one real sample (n = 300)** — Proportional (\(n_h \propto N_h\)) and Neyman (\(n_h \propto N_h S_h\)) with **explicit rounding** so \(\sum_h n_h = n\), plus a **minimum per stratum** (e.g. 2) so tiny strata still receive units. One draw per design; table of estimates, SEs, CIs, and a **single-sample DEFF** (variance ratio vs SRS for that draw).
5. **Monte Carlo (B = 1,000)** — Same **n**; for each replication, SRS + stratified proportional + stratified Neyman; summarize empirical variance, average theoretical variance, **95% CI coverage** of the **true finite-population mean**, and **DEFF** (see **§4.0** for how this grew from one-shot DEFF to \(\mathrm{DEFF}_{\mathrm{emp}}\) plus per-rep distributions).
6. **Optional diagnostic** — **Percentile bootstrap** on the SRS mean (nested simulation) to illustrate coverage under skew; labeled as **diagnostic**, not a replacement for theory-based CIs.
7. **Sensitivity** — Scenarios: main, **price cap $5,000**, **exclude IQR-flagged outliers**; one comparison table per scenario.
8. **Math-to-code audit** — Small table mapping **formula → function → assumption**, plus **sanity checks** (sums, \(f \in [0,1]\), etc.).

---

## 4. Design effect (DEFF) and effective sample size

### 4.0 Development: from one-shot DEFF to multiple summaries

This section records **how DEFF reporting evolved** in the project (conceptual order; all stages are reflected in the current notebook unless noted).

| Stage | What we did | Role in the final notebook |
|--------|-------------|----------------------------|
| **A. Definition aligned with course notes** | Set **\(\mathrm{DEFF}(\hat{\theta}) = V_{\text{complex}}(\hat{\theta}) / V_{\text{SRS}}(\hat{\theta})\)** (ratio of variances of the estimators under the two designs). Earlier confusion with **inverse** ratios was corrected so DEFF **above 1** means **worse** precision than SRS for that comparison, and **below 1** means **better**. | All DEFF quantities use this **numerator/denominator** convention. |
| **B. One-shot (single-sample) DEFF** | In **§4 “one real sample run”**, compute **plug-in** \(\widehat{\mathrm{DEFF}} = \widehat{V}_{\text{strat}} / \widehat{V}_{\text{SRS}}\) from **one** SRS draw and **one** stratified draw (same simulation seed path as the rest of the notebook). | **Kept** as an **illustration** of what a **single survey** might show. A single ratio can **differ sharply** from long-run behaviour (e.g. proportional stratification can look much worse or better in one draw than on average). |
| **C. Monte Carlo DEFF (primary)** | With **B = 1,000** replications, compute **\(\mathrm{DEFF}_{\mathrm{emp}} = \mathrm{Var}_{\text{sim}}(\hat{\bar{Y}}_{\text{complex}}) / \mathrm{Var}_{\text{sim}}(\hat{\bar{Y}}_{\text{SRS}})\)**, where each variance is the **empirical variance of the simulated estimates** across reps (same **n** each time). | **Main** reported design effect for comparing stratified designs to SRS. This answers: *“Over repeated samples, how much larger or smaller is the sampling variance than SRS?”* |
| **D. Multiple DEFF values per design (per replication)** | Inside the same Monte Carlo loop, for each **b**, store **\(\widehat{\mathrm{DEFF}}_b = \widehat{V}_{\text{strat},b}/\widehat{V}_{\text{SRS},b}\)** using the **usual variance estimators** from that replication. Summarise with **count, mean, std, min/max, quantiles** (e.g. `describe` with 2.5%–97.5%). | Shows the **distribution** of plug-in variance ratios—not a **single** number. Explains why **mean**\((\widehat{\mathrm{DEFF}}_b)\) **≠** \(\mathrm{DEFF}_{\mathrm{emp}}\) in general (ratio of random quantities vs ratio of long-run variances; **heavy right skew** when \(\widehat{V}_{\text{SRS}}\) is occasionally tiny). |
| **E. Effective sample size** | Report **\(n_{\mathrm{eff}} = n / \mathrm{DEFF}\)**. **Primary:** **\(n_{\mathrm{eff}} = n / \mathrm{DEFF}_{\mathrm{emp}}\)**. **Secondary:** **\(n / \mathrm{median}(\widehat{\mathrm{DEFF}}_b)\)** as a robust summary of per-rep ratios; **mean** of \(\widehat{\mathrm{DEFF}}_b\) is printed but flagged as **easy to distort** under skew. | Aligns with the course identity \(n_{\mathrm{eff}} = n/\mathrm{DEFF}(\hat{\theta})\) while being honest about **which** DEFF enters the formula. |

**Decision we did *not* take:** We did **not** “revert” to reporting **only** one-shot DEFF. **One-shot** remains **pedagogical**; **\(\mathrm{DEFF}_{\mathrm{emp}}\)** remains the **headline** for the design.

### 4.1 Definition used

- **DEFF** for comparing a complex design to SRS (same overall **n**) is implemented as a **variance ratio**:
  - **Single run:** \(\widehat{\mathrm{DEFF}} = \widehat{V}_{\text{complex}} / \widehat{V}_{\text{SRS}}\) from the **estimated** variances in that draw.
  - **Monte Carlo (primary):** \(\mathrm{DEFF}_{\mathrm{emp}} = V_{\text{complex}}^{\text{sim}} / V_{\text{SRS}}^{\text{sim}}\), where the **V** terms are **empirical variances of the simulated point estimates** across replications.

This matches the usual **“complex vs SRS”** design-effect interpretation for the mean estimator.

### 4.2 Why Monte Carlo DEFF is the headline (not one-shot only)

- A **one-shot** DEFF is **valid for that sample** but **very variable** across random draws. The notebook therefore treats **\(\mathrm{DEFF}_{\mathrm{emp}}\)** from **B = 1,000** replications as the **main** summary of the design.
- The **single-sample** table in section 4 remains useful as an **illustration** of what one survey might produce; it is **not** substituted for the long-run DEFF.

### 4.3 Per-replication DEFF distribution (optional detail)

- For each Monte Carlo replication **b**, the notebook also computes **\(\widehat{\mathrm{DEFF}}_b = \widehat{V}_{\text{strat},b}/\widehat{V}_{\text{SRS},b}\)** using the **usual variance estimators** in that rep.
- Summaries (**describe**, quantiles) show that these ratios can be **heavily right-skewed** (occasionally very large when the denominator is small or the stratum split is unlucky). Therefore:
  - The **mean** of \(\widehat{\mathrm{DEFF}}_b\) is **not** the same as \(\mathrm{DEFF}_{\mathrm{emp}}\) and can be **misleading** as a single number.
  - The **median** of \(\widehat{\mathrm{DEFF}}_b\) is often more interpretable than the mean for summarising that skewed distribution.

### 4.4 Effective sample size

- Course-style definition: **\(n_{\mathrm{eff}} = n / \mathrm{DEFF}(\hat{\theta})\)**.
- The notebook reports **\(n_{\mathrm{eff}}\)** using **\(n / \mathrm{DEFF}_{\mathrm{emp}}\)** as the **primary** effective sample size, and supplements with **median**-based summaries from per-rep ratios where relevant.

---

## 5. Confidence interval coverage

- **Nominal 95%** **t**-intervals **undercover** the true finite-population mean in simulation (on the order of **~0.74–0.85** depending on design in a typical run), because **price** is **skewed / heavy-tailed**: the **normal** sampling approximation behind standard **t** intervals is imperfect.
- The notebook **documents** this as a **limitation / diagnostic**, not a bug in the FPC or stratified variance formulas.
- The **bootstrap** diagnostic also often sits **below 0.95**, reinforcing that **tail behavior** drives coverage more than a single formula tweak.

---

## 6. Engineering / notebook hygiene changes

These are **repository maintenance** items that kept the notebook valid and reproducible:

- **Notebook JSON validity:** Stream outputs must include **`"name": "stdout"`** (or `"stderr"`) for **nbformat** / `nbconvert` validation; missing fields were fixed when they appeared.
- **Execution:** The notebook was executed with **`jupyter nbconvert --execute --inplace`** so **saved outputs** match **current code** (run in an environment where the Jupyter kernel starts successfully).
- **Script export:** A generated **`.py`** export was **not** kept as a duplicate source of truth; the **`.ipynb`** remains canonical unless you choose otherwise.

---

## 7. Optional direction discussed (not required in the notebook)

- **Geometric stratification** (Gunning & Horgan–style boundaries on a **skewed** auxiliary/target scale) was discussed as a **possible extension** for **price-skewed** data. It would be a **different** stratification than **neighbourhood** (interpretability vs precision trade-off). If implemented later, it would sit best as an **additional** Monte Carlo block alongside the current design, with clear handling of **positive lower bounds** (or **log-price**) so **m** is not near zero.

---

## 8. How to run

From the project root, with dependencies installed (`pandas`, `numpy`, `jupyter`, `scipy` recommended):

```bash
jupyter nbconvert --to notebook --execute sampling_simulation.ipynb --inplace
```

Or open `sampling_simulation.ipynb` in Jupyter / VS Code and **Run All**.

---

## 9. File map

| Path | Role |
|------|------|
| `analysis_dataset.csv` | Analysis population |
| `sampling_simulation.ipynb` | **Main** sampling & simulation implementation and outputs |
| `EDA.ipynb` | Exploratory analysis and dataset construction narrative |
| `.cursor/plans/sampling_and_simulation_execution.plan.md` | Original consolidated plan (reference) |
| `SAMPLING_WORKFLOW_AND_CHANGELOG.md` | **This document** |

---

*Last updated to include §4.0 (evolution from one-shot DEFF → Monte Carlo \(\mathrm{DEFF}_{\mathrm{emp}}\) → per-replication \(\widehat{\mathrm{DEFF}}_b\) summaries), plus neighbourhood-based stratified SRS workflow, \(n_{\mathrm{eff}}\), sensitivity analyses, and maintenance notes above.*

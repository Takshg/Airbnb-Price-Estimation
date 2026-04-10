"""
Shared sampling estimators, allocation, Monte Carlo simulation, and sensitivity helpers.

Used by sampling_simulation.ipynb and sampling_results_analysis.ipynb.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

try:
    from scipy.stats import t as student_t

    HAVE_SCIPY = True
except Exception:
    HAVE_SCIPY = False


def critical_t(alpha: float, df: float) -> float:
    if not HAVE_SCIPY:
        return 1.96
    if df <= 0 or np.isnan(df):
        return 1.96
    return float(student_t.ppf(1 - alpha / 2, df))


def srs_estimate(
    sample: pd.DataFrame,
    N: int,
    y_col: str = "price",
    alpha: float = 0.05,
):
    n = len(sample)
    y = sample[y_col].to_numpy(dtype=float)
    ybar = float(np.mean(y))
    s2 = float(np.var(y, ddof=1)) if n > 1 else 0.0
    f = n / N
    var_hat = (1 - f) * s2 / n if n > 0 else np.nan
    se = float(np.sqrt(var_hat)) if var_hat >= 0 else np.nan
    tcrit = critical_t(alpha, n - 1)
    ci = (ybar - tcrit * se, ybar + tcrit * se)
    return {
        "method": "SRS",
        "n": n,
        "estimate": ybar,
        "var_hat": var_hat,
        "se": se,
        "f": f,
        "df": n - 1,
        "tcrit": tcrit,
        "ci_low": ci[0],
        "ci_high": ci[1],
    }


def _round_alloc(weights: pd.Series, n_total: int, min_per_stratum: int = 1):
    H = len(weights)
    if n_total < H * min_per_stratum:
        raise ValueError("n_total too small for chosen minimum per stratum")

    base = pd.Series(min_per_stratum, index=weights.index, dtype=int)
    remaining = n_total - int(base.sum())

    target = remaining * (weights / weights.sum())
    floors = np.floor(target).astype(int)
    alloc = base + floors
    leftover = n_total - int(alloc.sum())

    if leftover > 0:
        remainders = (target - floors).sort_values(ascending=False)
        for idx in remainders.index[:leftover]:
            alloc.loc[idx] += 1
    elif leftover < 0:
        remainders = (target - floors).sort_values(ascending=True)
        for idx in remainders.index[:abs(leftover)]:
            if alloc.loc[idx] > min_per_stratum:
                alloc.loc[idx] -= 1

    assert int(alloc.sum()) == n_total
    return alloc.astype(int)


def proportional_allocation(
    stratum_stats: pd.DataFrame,
    n_total: int,
    strata_col: str = "neighbourhood",
    min_per_stratum: int = 2,
):
    w = stratum_stats.set_index(strata_col)["N_h"].astype(float)
    return _round_alloc(w, n_total=n_total, min_per_stratum=min_per_stratum)


def neyman_allocation(
    stratum_stats: pd.DataFrame,
    n_total: int,
    strata_col: str = "neighbourhood",
    min_per_stratum: int = 2,
):
    ss = stratum_stats.set_index(strata_col)
    metric = (ss["N_h"] * ss["S_h"].fillna(0)).astype(float)
    metric = metric.replace(0, metric[metric > 0].min() if (metric > 0).any() else 1.0)
    return _round_alloc(metric, n_total=n_total, min_per_stratum=min_per_stratum)


def draw_stratified_sample(
    population: pd.DataFrame,
    alloc: pd.Series,
    rng,
    strata_col: str = "neighbourhood",
):
    parts = []
    for h, n_h in alloc.items():
        stratum = population.loc[population[strata_col] == h]
        if n_h > len(stratum):
            raise ValueError(f"Allocation n_h={n_h} exceeds N_h={len(stratum)} for stratum {h}")
        pick = rng.choice(stratum.index.to_numpy(), size=int(n_h), replace=False)
        parts.append(population.loc[pick])
    return pd.concat(parts, axis=0)


def stratified_estimate(
    sample: pd.DataFrame,
    pop_strata: pd.DataFrame,
    N: int,
    strata_col: str = "neighbourhood",
    y_col: str = "price",
    alpha: float = 0.05,
):
    ss = pop_strata.set_index(strata_col).copy()
    sm = (
        sample.groupby(strata_col)[y_col]
        .agg(n_h="size", ybar_h="mean", s2_h=lambda x: np.var(x, ddof=1) if len(x) > 1 else 0.0)
    )
    joined = ss.join(sm, how="left").fillna({"n_h": 0, "ybar_h": 0.0, "s2_h": 0.0})

    joined["f_h"] = joined["n_h"] / joined["N_h"]
    joined["W_h"] = joined["N_h"] / N

    yhat = float((joined["W_h"] * joined["ybar_h"]).sum())
    comp = (joined["W_h"] ** 2) * (1 - joined["f_h"]) * joined["s2_h"] / joined["n_h"].replace(0, np.nan)
    comp = comp.fillna(0.0)
    var_hat = float(comp.sum())
    se = float(np.sqrt(var_hat)) if var_hat >= 0 else np.nan

    numer = var_hat**2
    denom_terms = []
    for _, row in joined.iterrows():
        n_h = int(row["n_h"])
        if n_h > 1:
            a_h = (row["W_h"] ** 2) * (1 - row["f_h"]) * row["s2_h"] / n_h
            denom_terms.append((a_h**2) / (n_h - 1))
    denom = float(np.sum(denom_terms)) if denom_terms else np.nan
    df_eff = numer / denom if denom and denom > 0 else np.nan

    nh = joined["n_h"].astype(int)
    n_samp = int(nh.sum())
    H_samp = int((nh > 0).sum())
    df_cap = max(1, n_samp - H_samp)

    if np.isnan(df_eff) or np.isinf(df_eff):
        df_for_t = float(df_cap)
    else:
        df_for_t = float(min(df_eff, df_cap))

    tcrit = critical_t(alpha, df_for_t)
    ci = (yhat - tcrit * se, yhat + tcrit * se)

    return {
        "estimate": yhat,
        "var_hat": var_hat,
        "se": se,
        "df": df_eff,
        "df_for_t": df_for_t,
        "tcrit": tcrit,
        "ci_low": ci[0],
        "ci_high": ci[1],
        "joined": joined.reset_index(),
    }


def build_stratum_stats(
    pop_df: pd.DataFrame,
    strata_col: str = "neighbourhood",
    y_col: str = "price",
) -> pd.DataFrame:
    N = len(pop_df)
    out = (
        pop_df.groupby(strata_col)[y_col]
        .agg(N_h="size", mean_h="mean", S_h="std")
        .reset_index()
        .sort_values("N_h", ascending=False)
    )
    out["W_h"] = out["N_h"] / N
    return out


@dataclass
class MonteCarloResult:
    true_mean: float
    mc: pd.DataFrame
    mc_summary: pd.DataFrame
    deff_rep: pd.DataFrame


def run_monte_carlo(
    population: pd.DataFrame,
    stratum_stats: pd.DataFrame,
    alloc_prop: pd.Series,
    alloc_neyman: pd.Series,
    *,
    n_total: int,
    B: int,
    rng: np.random.Generator,
    strata_col: str = "neighbourhood",
    y_col: str = "price",
) -> MonteCarloResult:
    N = len(population)
    true_mean = float(population[y_col].mean())

    records = []
    deff_prop_rep = []
    deff_neyman_rep = []

    for b in range(B):
        srs_idx = rng.choice(population.index.to_numpy(), size=n_total, replace=False)
        srs_sample = population.loc[srs_idx]
        prop_sample = draw_stratified_sample(population, alloc_prop, rng, strata_col=strata_col)
        neyman_sample = draw_stratified_sample(population, alloc_neyman, rng, strata_col=strata_col)

        out = {
            "SRS": srs_estimate(srs_sample, N, y_col=y_col),
            "Stratified-Proportional": stratified_estimate(
                prop_sample, stratum_stats, N, strata_col=strata_col, y_col=y_col
            ),
            "Stratified-Neyman": stratified_estimate(
                neyman_sample, stratum_stats, N, strata_col=strata_col, y_col=y_col
            ),
        }

        v_srs = out["SRS"]["var_hat"]
        v_prop = out["Stratified-Proportional"]["var_hat"]
        v_neyman = out["Stratified-Neyman"]["var_hat"]
        if v_srs > 0 and not (np.isnan(v_srs) or np.isnan(v_prop) or np.isnan(v_neyman)):
            deff_prop_rep.append(float(v_prop / v_srs))
            deff_neyman_rep.append(float(v_neyman / v_srs))
        else:
            deff_prop_rep.append(np.nan)
            deff_neyman_rep.append(np.nan)

        for method, res in out.items():
            covered = (res["ci_low"] <= true_mean) and (true_mean <= res["ci_high"])
            records.append(
                {
                    "rep": b,
                    "method": method,
                    "estimate": res["estimate"],
                    "var_hat": res["var_hat"],
                    "covered": int(covered),
                }
            )

    mc = pd.DataFrame(records)

    mc_summary = (
        mc.groupby("method")
        .agg(
            empirical_var=("estimate", "var"),
            avg_theoretical_var=("var_hat", "mean"),
            coverage_95=("covered", "mean"),
            mean_estimate=("estimate", "mean"),
        )
        .reset_index()
    )

    emp_srs_var = float(mc_summary.loc[mc_summary["method"] == "SRS", "empirical_var"].iloc[0])
    mc_summary["DEFF_emp"] = mc_summary["empirical_var"] / emp_srs_var
    mc_summary["n_eff_DEFF_emp"] = n_total / mc_summary["DEFF_emp"]

    deff_rep = pd.DataFrame(
        {"Stratified-Proportional": deff_prop_rep, "Stratified-Neyman": deff_neyman_rep}
    )

    return MonteCarloResult(
        true_mean=true_mean,
        mc=mc,
        mc_summary=mc_summary,
        deff_rep=deff_rep,
    )


def run_one_scenario(
    pop_df: pd.DataFrame,
    label: str,
    rng: np.random.Generator,
    *,
    n_total: int,
    strata_col: str = "neighbourhood",
    y_col: str = "price",
) -> pd.DataFrame:
    N_local = len(pop_df)
    strata_local = build_stratum_stats(pop_df, strata_col=strata_col, y_col=y_col)

    alloc_p = proportional_allocation(
        strata_local, n_total=n_total, strata_col=strata_col, min_per_stratum=2
    )
    alloc_n = neyman_allocation(
        strata_local, n_total=n_total, strata_col=strata_col, min_per_stratum=2
    )

    srs_idx = rng.choice(pop_df.index.to_numpy(), size=n_total, replace=False)
    samp_srs = pop_df.loc[srs_idx]
    samp_p = draw_stratified_sample(pop_df, alloc_p, rng, strata_col=strata_col)
    samp_n = draw_stratified_sample(pop_df, alloc_n, rng, strata_col=strata_col)

    r_srs = srs_estimate(samp_srs, N_local, y_col=y_col)
    r_p = stratified_estimate(samp_p, strata_local, N_local, strata_col=strata_col, y_col=y_col)
    r_n = stratified_estimate(samp_n, strata_local, N_local, strata_col=strata_col, y_col=y_col)

    return pd.DataFrame(
        [
            {
                "scenario": label,
                "method": "SRS",
                "estimate": r_srs["estimate"],
                "se": r_srs["se"],
                "ci_low": r_srs["ci_low"],
                "ci_high": r_srs["ci_high"],
            },
            {
                "scenario": label,
                "method": "Stratified-Proportional",
                "estimate": r_p["estimate"],
                "se": r_p["se"],
                "ci_low": r_p["ci_low"],
                "ci_high": r_p["ci_high"],
            },
            {
                "scenario": label,
                "method": "Stratified-Neyman",
                "estimate": r_n["estimate"],
                "se": r_n["se"],
                "ci_low": r_n["ci_low"],
                "ci_high": r_n["ci_high"],
            },
        ]
    )


def run_all_sensitivity_scenarios(
    population: pd.DataFrame,
    rng: np.random.Generator,
    *,
    n_total: int,
    y_col: str = "price",
    strata_col: str = "neighbourhood",
    outlier_flag_col: str = "price_outlier_iqr",
    price_cap: float = 5000.0,
) -> pd.DataFrame:
    main_pop = population.copy()
    cap_pop = population.copy()
    cap_pop[y_col] = cap_pop[y_col].clip(upper=price_cap)
    trim_pop = population.loc[~population[outlier_flag_col].astype(bool)].copy()

    return pd.concat(
        [
            run_one_scenario(main_pop, "main", rng, n_total=n_total, strata_col=strata_col, y_col=y_col),
            run_one_scenario(cap_pop, "cap_5000", rng, n_total=n_total, strata_col=strata_col, y_col=y_col),
            run_one_scenario(
                trim_pop, "exclude_iqr_flagged", rng, n_total=n_total, strata_col=strata_col, y_col=y_col
            ),
        ],
        ignore_index=True,
    )


def print_monte_carlo_summary(
    result: MonteCarloResult,
    n_total: int,
) -> None:
    true_mean = result.true_mean
    mc_summary = result.mc_summary
    deff_rep = result.deff_rep

    print(f"True population mean: {true_mean:.4f}")
    print(mc_summary)
    print(
        "\nPer-replication DEFF_hat = Vhat_strat / Vhat_SRS (B values per design; "
        "summary via describe):"
    )
    print(deff_rep.describe(percentiles=[0.025, 0.25, 0.5, 0.75, 0.975]))

    n_eff_from_mean_deff_rep = n_total / deff_rep.mean()
    n_eff_from_median_deff_rep = n_total / deff_rep.median()
    print(f"\nEffective sample size n_eff = n / DEFF, n = {n_total}")
    print("  Primary: DEFF_emp = Var_complex / Var_SRS from simulation (matches course DEFF on variances):")
    print(mc_summary.set_index("method")["n_eff_DEFF_emp"])
    print("  From per-rep DEFF_hat: median is more interpretable than mean when ratios are skewed:")
    print(n_eff_from_median_deff_rep)
    print("  Mean of per-rep DEFF_hat:")
    print(n_eff_from_mean_deff_rep)

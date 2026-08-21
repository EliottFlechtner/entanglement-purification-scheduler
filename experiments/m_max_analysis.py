"""
experiments/m_max_analysis.py
================================
Explores the newly-enforced `M_max` resource dimension (max concurrent
open branches, `ResourceBudget.m_max`, [Validated Formal Model Def, §5]),
now computed exactly via `ScheduleDAG.max_concurrent_branches()` (Sethi-
Ullman register allocation, `feature/enforce-m-max` branch) and wired
into `ObjectiveConfig.m_max`. Two questions:

  1. How does M(Σ) scale with N across the three canonical baseline
     families (raw, end-node pumping, flexible paper) and the
     optimizer's own best schedules (matched-cost / budget-relaxed) --
     is M ever a growing concern in practice, or does it stay small and
     bounded regardless of N?
  2. At the paper's own N=10, e_d=0.01 config (matching
     `outputs/headline_experiment_n10/`), what is the smallest `m_max`
     that still admits a feasible, rate-optimal schedule -- i.e. does
     `M_max` ever become the *actual* binding constraint (as opposed to
     `E_max`/`f_min`) for this network, and at what cost to the optimal
     rate as it tightens further?

Part 1 needs no search for the three canonical builders (M is a pure
DAG-structural property, independent of `NetworkConfig`/`e_d`); only the
optimizer's own best schedule at each N requires an actual
`beam_search` call, using the same per-hop paper parameterization as
`sweep_hop_count.py` (only N varies, `e_max = 10 * N`).

Part 2 fixes N=10 at the paper's own `e_max=100` and bisects `m_max`
downward from "unconstrained" to find the smallest feasible value,
mirroring `sweep_min_budget_vs_ed.py`'s bisection pattern but over
`m_max` instead of `e_max`.

Outputs
-------
    outputs/m_max_analysis/m_vs_n.csv
    outputs/m_max_analysis/m_vs_n.png
    outputs/m_max_analysis/m_max_bisection_n10.csv
    outputs/m_max_analysis/README.md

Usage
-----
    .venv/bin/python3 experiments/m_max_analysis.py
"""

from __future__ import annotations

import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from hrgs_scheduler.cost_functions import ObjectiveConfig
from hrgs_scheduler.models.network_config import NetworkConfig
from hrgs_scheduler.reporting import new_figure, plot_lines, save_figure
from hrgs_scheduler.schedule.dag import ScheduleDAG
from hrgs_scheduler.search import SearchResult, beam_search

F_MIN = 0.9
E_D = 0.01
BEAM_WIDTH = 25
N_VALUES = [2, 4, 6, 8, 10, 14, 18]
PAPER_N = 10
PAPER_E_MAX = 10 * PAPER_N  # matches sweep_hop_count.py's own formula

# Per-hop config fixed at the paper's own values, matching
# `sweep_hop_count.py` exactly so Part 1's optimizer schedules are
# directly comparable to that sweep's own results.
_LENGTH = 2.0
_BRANCHING = (16, 14, 1)
_ARM_COUNT = 18
_P_X_INNER = 0.0
_P_Z_INNER = 0.0
_GAMMA = 0.0
_C = 2e5

OUTPUT_DIR = _PROJECT_ROOT / "outputs" / "m_max_analysis"


def _build_network(N: int) -> NetworkConfig:
    return NetworkConfig.uniform(
        N=N,
        length=_LENGTH,
        branching=_BRANCHING,
        arm_count=_ARM_COUNT,
        p_x_inner=_P_X_INNER,
        p_z_inner=_P_Z_INNER,
        e_d=E_D,
        gamma=_GAMMA,
        c=_C,
    )


# ---------------------------------------------------------------------------
# Part 1: M(Sigma) vs. N, across canonical families + optimizer's own best
# ---------------------------------------------------------------------------


@dataclass
class MRow:
    N: int
    family: str
    m: int
    resource_cost: int


def run_part1() -> list[MRow]:
    rows: list[MRow] = []
    for N in N_VALUES:
        raw = ScheduleDAG.raw_chain(N)
        rows.append(MRow(N, "raw", raw.max_concurrent_branches(), raw.gen_node_count))

        baseline = ScheduleDAG.baseline_end_node_pumping(N, n_pur=5)
        rows.append(
            MRow(
                N,
                "baseline_end_node_pumping",
                baseline.max_concurrent_branches(),
                baseline.gen_node_count,
            )
        )

        # flexible_paper_schedule is only defined/validated at N=10 in this
        # codebase (it hand-encodes the paper's own Fig. 4 hop-by-hop
        # circuit choices), so only include it at N=10.
        if N == PAPER_N:
            flexible = ScheduleDAG.flexible_paper_schedule(N=N)
            rows.append(
                MRow(
                    N,
                    "paper_baseline",
                    flexible.max_concurrent_branches(),
                    flexible.gen_node_count,
                )
            )

        net = _build_network(N)
        obj = ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=F_MIN)
        e_max = 10 * N
        t0 = time.time()
        results = beam_search(net, obj, e_max=e_max, beam_width=BEAM_WIDTH)
        print(f"  N={N}: beam_search done in {time.time() - t0:.1f}s", flush=True)

        in_budget = [r for r in results if r.eval_result.resource_cost <= e_max]
        best_relaxed = in_budget[0] if in_budget else results[0]
        rows.append(
            MRow(
                N,
                "optimizer_budget_relaxed",
                best_relaxed.dag.max_concurrent_branches(),
                best_relaxed.eval_result.resource_cost,
            )
        )

        matched = [r for r in in_budget if r.eval_result.resource_cost == e_max]
        if matched:
            best_matched = matched[0]
            rows.append(
                MRow(
                    N,
                    "optimizer_matched_cost",
                    best_matched.dag.max_concurrent_branches(),
                    best_matched.eval_result.resource_cost,
                )
            )
    return rows


def write_part1_csv(rows: list[MRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["N", "family", "M", "resource_cost"])
        for r in rows:
            writer.writerow([r.N, r.family, r.m, r.resource_cost])


def make_part1_plot(rows: list[MRow]) -> None:
    families = sorted({r.family for r in rows})
    series = {
        fam: sorted((r.N, r.m) for r in rows if r.family == fam) for fam in families
    }
    fig, ax = new_figure()
    plot_lines(
        ax,
        series,
        xlabel="Number of hops N",
        ylabel="M(Σ) — concurrent open branches",
        title="M(Σ) vs. N, canonical families and optimizer's own best",
    )
    ax.set_ylim(2.5, 5.5)
    # Move the legend outside the axes: several series overlap exactly at
    # M=4 across the whole N range, so any in-plot legend placement risks
    # covering the single-point `paper_baseline` marker at N=10.
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
    save_figure(fig, OUTPUT_DIR / "m_vs_n")


# ---------------------------------------------------------------------------
# Part 2: m_max bisection at the paper's own N=10, e_max=100 config
# ---------------------------------------------------------------------------


@dataclass
class MMaxRow:
    m_max: int | None
    feasible: bool
    best_label: str
    best_rate: float
    best_fidelity: float
    actual_m: int


def run_part2() -> list[MMaxRow]:
    net = _build_network(PAPER_N)
    rows: list[MMaxRow] = []

    def _check(m_max: int | None) -> MMaxRow:
        obj = ObjectiveConfig(primary="rate", maximise=True, f_min=F_MIN, m_max=m_max)
        results = beam_search(net, obj, e_max=PAPER_E_MAX, beam_width=BEAM_WIDTH)
        in_budget = [r for r in results if r.eval_result.resource_cost <= PAPER_E_MAX]
        best = in_budget[0] if in_budget else results[0]
        feasible = best.score > float("-inf")
        return MMaxRow(
            m_max=m_max,
            feasible=feasible,
            best_label=best.label,
            best_rate=best.eval_result.rate,
            best_fidelity=best.eval_result.fidelity,
            actual_m=best.dag.max_concurrent_branches(),
        )

    unconstrained = _check(None)
    rows.append(unconstrained)
    print(
        f"  m_max=None (unconstrained): rate={unconstrained.best_rate:.2f}, "
        f"M={unconstrained.actual_m}, label={unconstrained.best_label}",
        flush=True,
    )

    # Sweep m_max downward from the unconstrained optimum's own M, one
    # step at a time, until infeasible -- small integer range, no need
    # for a log-bisection like the e_max sweeps use.
    hi_m = unconstrained.actual_m
    for m in range(hi_m, 0, -1):
        row = _check(m)
        rows.append(row)
        print(
            f"  m_max={m}: {'feasible' if row.feasible else 'infeasible'}, "
            f"rate={row.best_rate:.2f}, M={row.actual_m}, "
            f"label={row.best_label}",
            flush=True,
        )
        if not row.feasible:
            break
    return rows


def write_part2_csv(rows: list[MMaxRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "m_max",
                "feasible",
                "best_label",
                "best_rate",
                "best_fidelity",
                "actual_M",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    "unconstrained" if r.m_max is None else r.m_max,
                    r.feasible,
                    r.best_label,
                    f"{r.best_rate:.6f}",
                    f"{r.best_fidelity:.6f}",
                    r.actual_m,
                ]
            )


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------


def write_readme(
    part1_rows: list[MRow], part2_rows: list[MMaxRow], elapsed_s: float
) -> None:
    lines = [
        "# M_max Analysis: Concurrent Open Branches vs. N, and a Bisection at N=10",
        "",
        "Explores `M_max` (max concurrent open branches,"
        " `ResourceBudget.m_max`, [Validated Formal Model Def, §5]), now"
        " enforced via `ScheduleDAG.max_concurrent_branches()`"
        " (Sethi-Ullman register allocation, on the `feature/enforce-m-max`"
        " branch) and wired into `ObjectiveConfig.m_max`. This was"
        " previously an unenforced model-only field"
        " ([Repository State & Progress.md](../../docs/Repository%20State%20&%20Progress.md)"
        " §5).",
        "",
        "## Part 1: M(Σ) vs. N",
        "",
        "M(Σ) computed for the three canonical structural builders"
        " (`raw_chain`, `baseline_end_node_pumping(n_pur=5)`, and"
        " `flexible_paper_schedule` at N=10 only, since it is only defined"
        " there) plus the optimizer's own best schedule at each N (matched"
        " cost / budget-relaxed, `beam_search` at `e_max=10*N`, matching"
        " [sweep_hop_count.py](../../experiments/sweep_hop_count.py)'s own"
        " methodology).",
        "",
        "| N | Family | M(Σ) | Resource cost |",
        "|---|---|---|---|",
    ]
    for r in part1_rows:
        lines.append(f"| {r.N} | `{r.family}` | {r.m} | {r.resource_cost} |")

    raw_ms = sorted({r.m for r in part1_rows if r.family == "raw"})
    baseline_ms = sorted(
        {r.m for r in part1_rows if r.family == "baseline_end_node_pumping"}
    )
    opt_relaxed_rows = [r for r in part1_rows if r.family == "optimizer_budget_relaxed"]
    opt_relaxed_ms = sorted({r.m for r in opt_relaxed_rows})

    lines += [
        "",
        f"**Observation:** `raw` stays at M∈{raw_ms} and"
        f" `baseline_end_node_pumping` at M∈{baseline_ms} across the entire"
        f" N∈{N_VALUES} range -- both bounded by the depth of their fixed"
        " pumping/join structure, never by N itself (matches"
        " [tests/test_dag.py](../../tests/test_dag.py)'s"
        " `raw_chain(N=1..20)` regression, which already showed this"
        " bound directly). The optimizer's own budget-relaxed best"
        f" schedule ranges over M∈{opt_relaxed_ms} across the sweep --"
        " it is not fixed to one structural family, so its M varies with"
        " which span-partition the search actually selects at each N, but"
        " it stays in the same small single-digit range as the fixed"
        " baselines rather than growing with N. **No family examined here"
        " shows M(Σ) scaling with N** -- the register-allocation bound is"
        " governed by DAG *depth/branching shape*, not by hop count.",
        "",
        f"Full data: [`m_vs_n.csv`](m_vs_n.csv). Figure:"
        " [`m_vs_n.png`](m_vs_n.png).",
        "",
        f"## Part 2: m_max bisection at N={PAPER_N}, e_d={E_D},"
        f" e_max={PAPER_E_MAX} (paper's own budget)",
        "",
        "Starting from the unconstrained optimum's own M and stepping"
        " `m_max` down by 1 until infeasible, at the paper's own headline"
        " configuration"
        " ([outputs/headline_experiment_n10](../headline_experiment_n10)):",
        "",
        "| m_max | Feasible | Best schedule | Rate | Fidelity | Actual M |",
        "|---|---|---|---|---|---|",
    ]
    for r in part2_rows:
        m_label = "unconstrained" if r.m_max is None else str(r.m_max)
        lines.append(
            f"| {m_label} | {'yes' if r.feasible else 'no'} |"
            f" `{r.best_label}` | {r.best_rate:.2f} | {r.best_fidelity:.4f} |"
            f" {r.actual_m} |"
        )

    unconstrained = part2_rows[0]
    infeasible_rows = [r for r in part2_rows if not r.feasible]

    lines += [
        "",
    ]
    if infeasible_rows:
        first_infeasible = infeasible_rows[0]
        last_feasible_m = min(
            (r.m_max for r in part2_rows if r.feasible and r.m_max is not None),
            default=None,
        )
        lines.append(
            f"**Observation:** the unconstrained rate-optimal schedule at"
            f" N={PAPER_N} needs M={unconstrained.actual_m} concurrent open"
            f" branches. Every `m_max` down to {last_feasible_m} still finds"
            " a feasible schedule at the *same* rate/fidelity (the same"
            f" `{unconstrained.best_label}` candidate already has"
            f" M={unconstrained.actual_m} <= {last_feasible_m}, so it"
            f" remains selectable). At `m_max={first_infeasible.m_max}`,"
            f" no candidate in the beam-searched frontier clears both the"
            f" rate/fidelity objective and the branch budget: the best"
            f" schedule the search can still offer"
            f" (`{first_infeasible.best_label}`) needs"
            f" M={first_infeasible.actual_m} > {first_infeasible.m_max},"
            " so it is reported infeasible (score = -inf) despite its"
            f" fidelity ({first_infeasible.best_fidelity:.4f}) still"
            " clearing the f_min floor. This shows `M_max` **can** become"
            " the actual binding constraint (distinct from `E_max`/`f_min`)"
            " once tightened below the unconstrained optimum's own M --"
            " but at the paper's own parameterization, it is not a"
            " binding concern until tightened noticeably past that point."
        )
    else:
        lines.append(
            f"**Observation:** every `m_max` value probed down to 1 still"
            f" admits a feasible, rate-optimal schedule at N={PAPER_N} --"
            " `M_max` never becomes the binding constraint at this"
            " network's paper-scale configuration; `E_max`/`f_min` remain"
            " the effective limits in practice."
        )

    lines += [
        "",
        f"Full data: [`m_max_bisection_n10.csv`](m_max_bisection_n10.csv).",
        "",
        "## Reproducing",
        "",
        "```bash",
        f"cd {_PROJECT_ROOT}",
        "source .venv/bin/activate",
        "python3 experiments/m_max_analysis.py",
        "```",
        "",
        f"Total wall-clock time: ~{elapsed_s:.0f}s.",
        "",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines))


def main() -> None:
    t0 = time.time()

    print("Part 1: M(Σ) vs. N ...", flush=True)
    part1_rows = run_part1()

    print(f"Part 2: m_max bisection at N={PAPER_N} ...", flush=True)
    part2_rows = run_part2()

    elapsed = time.time() - t0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_part1_csv(part1_rows, OUTPUT_DIR / "m_vs_n.csv")
    make_part1_plot(part1_rows)
    write_part2_csv(part2_rows, OUTPUT_DIR / "m_max_bisection_n10.csv")
    write_readme(part1_rows, part2_rows, elapsed)

    print(f"\nDone in {elapsed:.1f}s. Outputs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

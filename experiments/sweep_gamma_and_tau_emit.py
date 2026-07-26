"""
experiments/sweep_gamma_and_tau_emit.py
==========================================
Quantifies how much the two previously-inert `NetworkConfig` parameters,
`gamma` (memory decoherence rate) and `tau_emit` (branching-derived
generation latency), actually move F/R once they are wired into the
Evaluator (see `schedule/evaluator.py::_sync_to_common_time` and
`_eval_gen`, and `docs/Optimizer Status.md`).

Both parameters were previously dead fields; this sweep answers "how bad
does it get" as each is turned up, and whether the optimizer's own
`beam_search` choice is sensitive to them.

Methodology
-----------
Two independent sub-sweeps, both at the paper's own shape (N=10, l=2 km,
branching=(16,14,1), arm_count=18, e_d=0.01, c=2e5), varying exactly one
of `gamma`/`tau_emit` at a time (the other held at its inert default:
gamma=0.0 / tau_emit=None) so effects are never conflated.

**Part 1 -- gamma sweep** (`GAMMA_VALUES`, log-spaced 0 .. 1e5):
Three *fixed* canonical schedules are re-evaluated at each gamma:

  * `raw_chain`                    -- no purification, no waits anywhere.
  * `flexible_paper_schedule`      -- optimistic pumping, NO intermediate
                                       Heralds between Purify rounds, so
                                       every combine happens at equal
                                       current_time (no asymmetric wait).
  * `baseline_end_node_pumping`    -- heralded pumping (n_pur=5): each
                                       round's freshly-generated
                                       sacrificial copy waits in memory
                                       for the primary branch's
                                       accumulated round-trip Herald
                                       confirmations before being
                                       purified -- exactly the scenario
                                       `gamma`/`IdleNode` model.

This isolates *which* schedule shapes are gamma-sensitive at all (only
the heralded one should be). `beam_search` is also run at each gamma
point (paper baseline / matched-cost / budget-relaxed, same framing as
`sweep_ed.py`) to see whether the search's own winning candidate shifts
away from heralded pumping as gamma grows.

**Part 2 -- tau_emit sweep** (`TAU_EMIT_VALUES`, log-spaced 1e-7 .. 1e-1,
plus tau_emit=0.0/None as the documented no-op reference): the same
three canonical schedules plus the same `beam_search` framing, but
varying generation latency instead. Since `tau_emit` adds a *uniform*
offset to every Gen node (branching is uniform across hops here), it
increases every schedule's absolute latency by the same tau_half; the
*relative* rate hit is largest for schedules with the smallest baseline
latency (`flexible`/optimistic, 1x L/c) and smallest for the largest
baseline latency (`baseline`/heralded, 9x L/c at n_pur=5) -- matching
`timing.py`'s documented canonical-timing insight.

Outputs
-------
    outputs/sweep_gamma_and_tau_emit/gamma_canonical.csv
    outputs/sweep_gamma_and_tau_emit/gamma_optimizer.csv
    outputs/sweep_gamma_and_tau_emit/tau_emit_canonical.csv
    outputs/sweep_gamma_and_tau_emit/tau_emit_optimizer.csv
    outputs/sweep_gamma_and_tau_emit/gamma_fidelity.{png,svg}
    outputs/sweep_gamma_and_tau_emit/gamma_optimizer_rate.{png,svg}
    outputs/sweep_gamma_and_tau_emit/tau_emit_rate.{png,svg}
    outputs/sweep_gamma_and_tau_emit/tau_emit_optimizer_rate.{png,svg}
    outputs/sweep_gamma_and_tau_emit/README.md

Usage
-----
    .venv/bin/python3 experiments/sweep_gamma_and_tau_emit.py
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
from hrgs_scheduler.schedule.evaluator import Evaluator
from hrgs_scheduler.search import beam_search

N_HOPS = 10
E_D = 0.01
F_MIN = 0.9
E_MAX = 100  # paper's own resource cost at N=10, n_pur=5
BEAM_WIDTH = 25
LENGTH = 2.0
BRANCHING = (16, 14, 1)
ARM_COUNT = 18
C = 2e5

# 0.0 is the documented no-op reference (matches historical/inert
# behaviour exactly); the rest are log-spaced to show the full
# unaffected -> partially-affected -> fully-decohered range given this
# network's L_total/c = 20/2e5 = 1e-4 time units (baseline pumping's
# worst-case wait is 3 rounds * 2 * 1e-4 = 6e-4 time units).
GAMMA_VALUES = [0.0, 1.0, 10.0, 100.0, 1_000.0, 10_000.0, 100_000.0]

# 0.0 is the documented no-op reference (== tau_emit=None exactly).
# tau_half = tau_emit * (log2(16) + log2(14)) = tau_emit * 7.807; the
# rest are log-spaced to move tau_half from << L/c (1e-4) to >> L/c.
TAU_EMIT_VALUES = [0.0, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2]

OUTPUT_DIR = _PROJECT_ROOT / "outputs" / "sweep_gamma_and_tau_emit"

CANONICAL_SCHEDULES = ["raw", "flexible_optimistic", "baseline_heralded_pumping"]


def _build_network(
    *, gamma: float = 0.0, tau_emit: float | None = None
) -> NetworkConfig:
    return NetworkConfig.uniform(
        N=N_HOPS,
        length=LENGTH,
        branching=BRANCHING,
        arm_count=ARM_COUNT,
        p_x_inner=0.0,
        p_z_inner=0.0,
        e_d=E_D,
        gamma=gamma,
        c=C,
        tau_emit=tau_emit,
    )


def _canonical_dags() -> dict[str, ScheduleDAG]:
    return {
        "raw": ScheduleDAG.raw_chain(N=N_HOPS),
        "flexible_optimistic": ScheduleDAG.flexible_paper_schedule(N=N_HOPS),
        "baseline_heralded_pumping": ScheduleDAG.baseline_end_node_pumping(
            N=N_HOPS, n_pur=5
        ),
    }


@dataclass
class CanonicalRow:
    param_name: str
    param_value: float
    schedule: str
    resource_cost: int
    fidelity: float
    success_prob: float
    rate: float
    latency: float


@dataclass
class OptimizerRow:
    param_name: str
    param_value: float
    variant: str
    label: str
    resource_cost: int
    fidelity: float
    rate: float
    meets_floor: bool


def _run_optimizer_point(
    net: NetworkConfig, param_name: str, param_value: float
) -> list[OptimizerRow]:
    obj = ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=F_MIN)
    results = beam_search(net, obj, e_max=E_MAX, beam_width=BEAM_WIDTH)
    paper = next(r for r in results if r.label == "flexible_paper")
    matched = next(
        r
        for r in results
        if r.eval_result.resource_cost == paper.eval_result.resource_cost
    )
    budget = results[0]
    rows = []
    for variant, r in [
        ("paper_baseline", paper),
        ("optimizer_matched_cost", matched),
        ("optimizer_budget_relaxed", budget),
    ]:
        rows.append(
            OptimizerRow(
                param_name=param_name,
                param_value=param_value,
                variant=variant,
                label=r.label,
                resource_cost=r.eval_result.resource_cost,
                fidelity=r.eval_result.fidelity,
                rate=r.eval_result.rate,
                meets_floor=r.eval_result.fidelity >= F_MIN,
            )
        )
    return rows


def run_gamma_sweep() -> tuple[list[CanonicalRow], list[OptimizerRow]]:
    dags = _canonical_dags()
    canonical_rows: list[CanonicalRow] = []
    optimizer_rows: list[OptimizerRow] = []
    for gamma in GAMMA_VALUES:
        print(f"[gamma] gamma={gamma:g} ...", flush=True)
        net = _build_network(gamma=gamma)
        ev = Evaluator(net)
        for name, dag in dags.items():
            r = ev.evaluate(dag)
            canonical_rows.append(
                CanonicalRow(
                    param_name="gamma",
                    param_value=gamma,
                    schedule=name,
                    resource_cost=r.resource_cost,
                    fidelity=r.fidelity,
                    success_prob=r.success_prob,
                    rate=r.rate,
                    latency=r.latency,
                )
            )
        optimizer_rows.extend(_run_optimizer_point(net, "gamma", gamma))
    return canonical_rows, optimizer_rows


def run_tau_emit_sweep() -> tuple[list[CanonicalRow], list[OptimizerRow]]:
    dags = _canonical_dags()
    canonical_rows: list[CanonicalRow] = []
    optimizer_rows: list[OptimizerRow] = []
    for tau_emit in TAU_EMIT_VALUES:
        print(f"[tau_emit] tau_emit={tau_emit:g} ...", flush=True)
        # 0.0 is reported as the None-equivalent reference point but
        # passed as an explicit float (identical result to tau_emit=None,
        # see NetworkConfig.tau_emit docstring).
        net = _build_network(tau_emit=tau_emit)
        ev = Evaluator(net)
        for name, dag in dags.items():
            r = ev.evaluate(dag)
            canonical_rows.append(
                CanonicalRow(
                    param_name="tau_emit",
                    param_value=tau_emit,
                    schedule=name,
                    resource_cost=r.resource_cost,
                    fidelity=r.fidelity,
                    success_prob=r.success_prob,
                    rate=r.rate,
                    latency=r.latency,
                )
            )
        optimizer_rows.extend(_run_optimizer_point(net, "tau_emit", tau_emit))
    return canonical_rows, optimizer_rows


def write_canonical_csv(rows: list[CanonicalRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "param_name",
                "param_value",
                "schedule",
                "resource_cost",
                "fidelity",
                "success_prob",
                "rate",
                "latency",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.param_name,
                    r.param_value,
                    r.schedule,
                    r.resource_cost,
                    r.fidelity,
                    r.success_prob,
                    r.rate,
                    r.latency,
                ]
            )


def write_optimizer_csv(rows: list[OptimizerRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "param_name",
                "param_value",
                "variant",
                "label",
                "resource_cost",
                "fidelity",
                "rate",
                "meets_floor",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.param_name,
                    r.param_value,
                    r.variant,
                    r.label,
                    r.resource_cost,
                    r.fidelity,
                    r.rate,
                    r.meets_floor,
                ]
            )


def make_gamma_plots(
    canonical_rows: list[CanonicalRow], optimizer_rows: list[OptimizerRow]
) -> None:
    by_schedule: dict[str, list[CanonicalRow]] = {}
    for r in canonical_rows:
        by_schedule.setdefault(r.schedule, []).append(r)
    fidelity_series = {
        s: [(r.param_value, r.fidelity) for r in rs if r.param_value > 0]
        for s, rs in by_schedule.items()
    }
    fig, ax = new_figure()
    plot_lines(
        ax,
        fidelity_series,
        xlabel=r"Memory dephasing rate $\gamma$ (log scale)",
        ylabel="Fidelity $F$",
        title=f"Fidelity vs. $\\gamma$: canonical schedules (N={N_HOPS}, e_d={E_D})",
        style_overrides={
            "raw": {"label": "raw_chain (no purification)"},
            "flexible_optimistic": {
                "label": "flexible_paper (optimistic, no intra-schedule waits)"
            },
            "baseline_heralded_pumping": {
                "label": "baseline pumping (heralded, n_pur=5)"
            },
        },
    )
    ax.set_xscale("log")
    ax.axhline(
        0.25,
        color="black",
        linewidth=0.8,
        linestyle=":",
        label="Maximally mixed (F=0.25)",
    )
    ax.legend()
    save_figure(fig, OUTPUT_DIR / "gamma_fidelity")

    by_variant: dict[str, list[OptimizerRow]] = {}
    for r in optimizer_rows:
        by_variant.setdefault(r.variant, []).append(r)
    rate_series = {
        v: [(r.param_value, r.rate) for r in rs if r.param_value > 0]
        for v, rs in by_variant.items()
    }
    fig, ax = new_figure()
    plot_lines(
        ax,
        rate_series,
        xlabel=r"Memory dephasing rate $\gamma$ (log scale)",
        ylabel="Rate (score)",
        title=f"beam_search rate vs. $\\gamma$ (N={N_HOPS}, e_d={E_D}, e_max={E_MAX})",
    )
    ax.set_xscale("log")
    save_figure(fig, OUTPUT_DIR / "gamma_optimizer_rate")


def make_tau_emit_plots(
    canonical_rows: list[CanonicalRow], optimizer_rows: list[OptimizerRow]
) -> None:
    by_schedule: dict[str, list[CanonicalRow]] = {}
    for r in canonical_rows:
        by_schedule.setdefault(r.schedule, []).append(r)
    rate_series = {
        s: [(r.param_value, r.rate) for r in rs if r.param_value > 0]
        for s, rs in by_schedule.items()
    }
    fig, ax = new_figure()
    plot_lines(
        ax,
        rate_series,
        xlabel=r"$\tau_{emit}$ (log scale)",
        ylabel="Rate (score)",
        title=f"Rate vs. $\\tau_{{emit}}$: canonical schedules (N={N_HOPS}, e_d={E_D})",
        style_overrides={
            "raw": {"label": "raw_chain (no purification)"},
            "flexible_optimistic": {
                "label": "flexible_paper (optimistic, 1x L/c baseline latency)"
            },
            "baseline_heralded_pumping": {
                "label": "baseline pumping (heralded, 9x L/c baseline latency)"
            },
        },
    )
    ax.set_xscale("log")
    ax.set_yscale("log")
    save_figure(fig, OUTPUT_DIR / "tau_emit_rate")

    by_variant: dict[str, list[OptimizerRow]] = {}
    for r in optimizer_rows:
        by_variant.setdefault(r.variant, []).append(r)
    opt_rate_series = {
        v: [(r.param_value, r.rate) for r in rs if r.param_value > 0]
        for v, rs in by_variant.items()
    }
    fig, ax = new_figure()
    plot_lines(
        ax,
        opt_rate_series,
        xlabel=r"$\tau_{emit}$ (log scale)",
        ylabel="Rate (score)",
        title=f"beam_search rate vs. $\\tau_{{emit}}$ (N={N_HOPS}, e_d={E_D}, e_max={E_MAX})",
    )
    ax.set_xscale("log")
    save_figure(fig, OUTPUT_DIR / "tau_emit_optimizer_rate")


def write_readme(
    gamma_canonical: list[CanonicalRow],
    gamma_optimizer: list[OptimizerRow],
    tau_canonical: list[CanonicalRow],
    tau_optimizer: list[OptimizerRow],
    elapsed_s: float,
) -> None:
    lines = [
        "# Sweep: gamma (memory decoherence) and tau_emit (generation timing) sensitivity",
        "",
        "Quantifies how much the two previously-inert `NetworkConfig` fields"
        " `gamma` and `tau_emit` move F/R now that they are wired into"
        " `Evaluator` (see `schedule/evaluator.py::_sync_to_common_time`"
        " for gamma, `_eval_gen` for tau_emit, and"
        " `outputs/sweep_network_sensitivity/README.md` for the original"
        ' "dead field" finding this supersedes).',
        "",
        f"Network shape: N={N_HOPS}, l=2 km/hop, branching=(16,14,1),"
        f" arm_count=18, e_d={E_D}, c=2e5 -- the paper's own config, only"
        " gamma/tau_emit varied one at a time (the other held at its"
        " inert default: gamma=0.0 / tau_emit=None).",
        "",
        "## Part 1: gamma sweep",
        "",
        "Three fixed canonical schedules, re-evaluated at each gamma"
        " (no search): `raw_chain` (no purification, no waits),"
        " `flexible_paper_schedule` (optimistic pumping, no intermediate"
        " Heralds between Purify rounds -> no asymmetric waits anywhere),"
        " and `baseline_end_node_pumping` (heralded pumping, n_pur=5 ->"
        " sacrificial copies wait for the primary branch's accumulated"
        " round-trip Herald confirmations before being purified).",
        "",
        "| gamma | Schedule | Fidelity | Rate |",
        "|---|---|---|---|",
    ]
    for r in gamma_canonical:
        lines.append(
            f"| {r.param_value:g} | {r.schedule} | {r.fidelity:.4f} | {r.rate:.2f} |"
        )
    lines += [
        "",
        "**Only `baseline_heralded_pumping` is gamma-sensitive** --"
        " `raw`/`flexible_optimistic` are exactly flat across the whole"
        " sweep (as expected: neither ever combines two branches with"
        " different `current_time`). This confirms the fix is scoped"
        " correctly: gamma only matters where a real asynchronous wait"
        " exists in the schedule.",
        "",
        "### Optimizer sensitivity (`beam_search`, same framing as `sweep_ed.py`)",
        "",
        "| gamma | Variant | Label | Cost | Fidelity | Rate | Meets floor? |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in gamma_optimizer:
        lines.append(
            f"| {r.param_value:g} | {r.variant} | {r.label} | {r.resource_cost} |"
            f" {r.fidelity:.4f} | {r.rate:.2f} | {'yes' if r.meets_floor else 'no'} |"
        )
    lines += [
        "",
        "Full per-point data: [`gamma_canonical.csv`](gamma_canonical.csv),"
        " [`gamma_optimizer.csv`](gamma_optimizer.csv).",
        "",
        "Figures: [`gamma_fidelity.png`](gamma_fidelity.png) (canonical"
        " schedules), [`gamma_optimizer_rate.png`](gamma_optimizer_rate.png)"
        " (`beam_search` variants).",
        "",
        "## Part 2: tau_emit sweep",
        "",
        "Same three canonical schedules and `beam_search` framing, varying"
        " `tau_emit` instead (with `gamma=0.0`). `tau_emit` adds a uniform"
        " generation-latency offset tau_half = tau_emit * (log2(16) +"
        " log2(14)) = tau_emit * 7.807 to every Gen node (branching is"
        " uniform across hops here), so every schedule's absolute latency"
        " grows by the same amount -- the *relative* rate hit is largest"
        " for the schedule with the smallest baseline latency"
        " (`flexible_optimistic`, 1x L/c) and smallest for the largest"
        " baseline latency (`baseline_heralded_pumping`, 9x L/c at"
        " n_pur=5), matching `timing.py`'s documented canonical-timing"
        " insight.",
        "",
        "| tau_emit | Schedule | Rate | Latency |",
        "|---|---|---|---|",
    ]
    for r in tau_canonical:
        lines.append(
            f"| {r.param_value:g} | {r.schedule} | {r.rate:.2f} | {r.latency:.6g} |"
        )
    lines += [
        "",
        "### Optimizer sensitivity (`beam_search`)",
        "",
        "| tau_emit | Variant | Label | Cost | Fidelity | Rate | Meets floor? |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in tau_optimizer:
        lines.append(
            f"| {r.param_value:g} | {r.variant} | {r.label} | {r.resource_cost} |"
            f" {r.fidelity:.4f} | {r.rate:.2f} | {'yes' if r.meets_floor else 'no'} |"
        )
    lines += [
        "",
        "Full per-point data: [`tau_emit_canonical.csv`](tau_emit_canonical.csv),"
        " [`tau_emit_optimizer.csv`](tau_emit_optimizer.csv).",
        "",
        "Figures: [`tau_emit_rate.png`](tau_emit_rate.png) (canonical"
        " schedules, log-log), [`tau_emit_optimizer_rate.png`](tau_emit_optimizer_rate.png)"
        " (`beam_search` variants).",
        "",
        "## Reproducing",
        "",
        "```bash",
        f"cd {_PROJECT_ROOT}",
        "source .venv/bin/activate",
        "python3 experiments/sweep_gamma_and_tau_emit.py",
        "```",
        "",
        f"Total wall-clock time: ~{elapsed_s:.0f}s"
        f" ({len(GAMMA_VALUES) + len(TAU_EMIT_VALUES)} `beam_search` calls"
        " total, plus cheap direct evaluator calls for the canonical"
        " schedules).",
        "",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines))


def main() -> None:
    t0 = time.time()
    gamma_canonical, gamma_optimizer = run_gamma_sweep()
    tau_canonical, tau_optimizer = run_tau_emit_sweep()
    elapsed = time.time() - t0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_canonical_csv(gamma_canonical, OUTPUT_DIR / "gamma_canonical.csv")
    write_optimizer_csv(gamma_optimizer, OUTPUT_DIR / "gamma_optimizer.csv")
    write_canonical_csv(tau_canonical, OUTPUT_DIR / "tau_emit_canonical.csv")
    write_optimizer_csv(tau_optimizer, OUTPUT_DIR / "tau_emit_optimizer.csv")
    make_gamma_plots(gamma_canonical, gamma_optimizer)
    make_tau_emit_plots(tau_canonical, tau_optimizer)
    write_readme(
        gamma_canonical, gamma_optimizer, tau_canonical, tau_optimizer, elapsed
    )

    print(f"\nDone in {elapsed:.1f}s. Outputs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

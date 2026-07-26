"""
experiments/alternative_objectives.py
========================================
Roadmap item 9: every other script in this repo exercises exactly one
`ObjectiveConfig` preset (`maximize_rate_with_fidelity_floor`), even
though `cost_functions.py` ships two more
(`maximize_fidelity_with_rate_floor`, `minimize_cost_with_constraints`)
that have never been run against real data. This script exercises all
three at the paper's own headline config (N=10, e_d=0.01), demonstrating
the "objective substitution" framing.

Presets exercised
------------------
  1. `maximize_rate_with_fidelity_floor(f_min=0.9)` -- the standard
     preset used everywhere else; restated here as the reference point.
  2. `maximize_fidelity_with_rate_floor(r_min=<paper's own rate>)` --
     "what is the best fidelity achievable without falling below the
     paper's own throughput?"
  3. `maximize_fidelity_with_rate_floor(r_min=<matched-cost rate>)` --
     same question, with a stricter floor (the optimizer's own
     matched-cost rate rather than the paper's).
  4. `minimize_cost_with_constraints(f_min=0.9)` -- "what is the
     cheapest schedule that clears the fidelity floor, ignoring rate?"
     Doubles as an independent cross-check of
     `outputs/sweep_min_budget_vs_ed/`'s bisection-derived minimum
     budget at e_d=0.01, computed here directly via the objective's own
     scoring instead of an external bisection loop.
  5. `minimize_cost_with_constraints(f_min=0.9, r_min=<paper's own rate>)`
     -- "cheapest schedule meeting *both* bars" [Justification of
     Implementation.md, §6.3].

Each preset is run once via `beam_search(net, obj, e_max=200,
beam_width=25)`; the top result is only trusted if `score > -inf`
(documented gotcha: infeasible candidates still occupy `results[0]` when
nothing clears the objective's constraints).

Outputs
-------
    outputs/alternative_objectives/results.csv
    outputs/alternative_objectives/README.md

Usage
-----
    .venv/bin/python3 experiments/alternative_objectives.py
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
from hrgs_scheduler.search import SearchResult, beam_search

N_HOPS = 10
E_D = 0.01
F_MIN = 0.9
E_MAX = 200  # generous, well above the ~50-100 cost range seen elsewhere
BEAM_WIDTH = 25

OUTPUT_DIR = _PROJECT_ROOT / "outputs" / "alternative_objectives"


@dataclass
class PresetResult:
    name: str
    formula: str
    feasible: bool
    label: str
    resource_cost: int
    fidelity: float
    success_prob: float
    rate: float


def _best(results: list[SearchResult]) -> tuple[bool, SearchResult]:
    feasible = results[0].score > float("-inf")
    return feasible, results[0]


def run_all() -> tuple[list[PresetResult], float, float]:
    net = NetworkConfig.integrating_paper_config(e_d=E_D)

    # Preset 1: the standard objective, used to derive the reference
    # rates for presets 2-5 below (no separate brute-force call needed;
    # beam_search already includes the fixed families).
    obj1 = ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=F_MIN)
    results1 = beam_search(net, obj1, e_max=E_MAX, beam_width=BEAM_WIDTH)
    paper = next(r for r in results1 if r.label == "flexible_paper")
    matched = next(
        r
        for r in results1
        if r.eval_result.resource_cost == paper.eval_result.resource_cost
    )
    paper_rate = paper.eval_result.rate
    matched_rate = matched.eval_result.rate

    presets: list[tuple[str, str, ObjectiveConfig]] = [
        (
            "maximize_rate_with_fidelity_floor",
            f"maximize R s.t. F >= {F_MIN}",
            obj1,
        ),
        (
            "maximize_fidelity_with_rate_floor(paper_rate)",
            f"maximize F s.t. R >= {paper_rate:.2f} (paper baseline's own rate)",
            ObjectiveConfig.maximize_fidelity_with_rate_floor(r_min=paper_rate),
        ),
        (
            "maximize_fidelity_with_rate_floor(matched_rate)",
            f"maximize F s.t. R >= {matched_rate:.2f} (optimizer matched-cost rate)",
            ObjectiveConfig.maximize_fidelity_with_rate_floor(r_min=matched_rate),
        ),
        (
            "minimize_cost_with_constraints(f_min_only)",
            f"minimize C s.t. F >= {F_MIN}",
            ObjectiveConfig.minimize_cost_with_constraints(f_min=F_MIN),
        ),
        (
            "minimize_cost_with_constraints(f_min_and_r_min)",
            f"minimize C s.t. F >= {F_MIN} and R >= {paper_rate:.2f}",
            ObjectiveConfig.minimize_cost_with_constraints(
                f_min=F_MIN, r_min=paper_rate
            ),
        ),
    ]

    out: list[PresetResult] = []
    for name, formula, obj in presets:
        if name == "maximize_rate_with_fidelity_floor":
            results = results1
        else:
            results = beam_search(net, obj, e_max=E_MAX, beam_width=BEAM_WIDTH)
        feasible, best = _best(results)
        out.append(
            PresetResult(
                name=name,
                formula=formula,
                feasible=feasible,
                label=best.label,
                resource_cost=best.eval_result.resource_cost,
                fidelity=best.eval_result.fidelity,
                success_prob=best.eval_result.success_prob,
                rate=best.eval_result.rate,
            )
        )
    return out, paper_rate, matched_rate


def write_results_csv(rows: list[PresetResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "preset",
                "formula",
                "feasible",
                "label",
                "resource_cost",
                "fidelity",
                "success_prob",
                "rate",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r.name,
                    r.formula,
                    r.feasible,
                    r.label,
                    r.resource_cost,
                    r.fidelity,
                    r.success_prob,
                    r.rate,
                ]
            )


def write_readme(
    rows: list[PresetResult], paper_rate: float, matched_rate: float, elapsed_s: float
) -> None:
    lines = [
        "# Alternative Objective Presets",
        "",
        "Roadmap item 9 ([docs/archive/Roadmap Remaining"
        " Work.md](../../docs/archive/Roadmap%20Remaining%20Work.md)):"
        " exercises `ObjectiveConfig.maximize_fidelity_with_rate_floor`"
        " and `ObjectiveConfig.minimize_cost_with_constraints` for the"
        " first time against real data, at the paper's own headline"
        f' config (N={N_HOPS}, e_d={E_D}), demonstrating the "objective'
        ' substitution" framing'
        " ([docs/Justification of Implementation.md, §6.3]"
        "(../../docs/Justification%20of%20Implementation.md)).",
        "",
        f"Reference rates (from the standard preset): paper baseline rate"
        f" = {paper_rate:.2f}, optimizer matched-cost rate = {matched_rate:.2f}."
        f" `e_max={E_MAX}` throughout (generous, above the ~50-100 cost"
        " range seen elsewhere so it never binds unless the objective"
        " itself wants a low cost).",
        "",
        "## Results",
        "",
        "| Preset | Formula | Feasible | Cost | Fidelity | Success prob | Rate |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| `{r.name}` | {r.formula} | {'yes' if r.feasible else 'NO'} |"
            f" {r.resource_cost} | {r.fidelity:.4f} | {r.success_prob:.4f} | {r.rate:.2f} |"
        )

    cost_min_row = next(
        r for r in rows if r.name == "minimize_cost_with_constraints(f_min_only)"
    )
    lines += [
        "",
        "## Cross-check against the bisected minimum budget",
        "",
        f"`minimize_cost_with_constraints(f_min={F_MIN})` finds cost="
        f"{cost_min_row.resource_cost} directly via the objective's own"
        " scoring (no external bisection loop) -- compare against"
        " `outputs/sweep_min_budget_vs_ed/`'s independently bisected"
        f" minimum budget at e_d={E_D}, N={N_HOPS}.",
        "",
        "## Takeaways",
        "",
    ]
    fid_paper_row = next(
        r for r in rows if r.name == "maximize_fidelity_with_rate_floor(paper_rate)"
    )
    fid_matched_row = next(
        r for r in rows if r.name == "maximize_fidelity_with_rate_floor(matched_rate)"
    )
    lines += [
        f"- Swapping the objective's *primary* metric from rate to"
        f" fidelity (while holding a rate floor instead of a fidelity"
        f" floor) is a one-line change"
        f" (`ObjectiveConfig.maximize_fidelity_with_rate_floor(r_min=...)`)"
        f" and yields a genuinely different top schedule: fidelity"
        f" {fid_paper_row.fidelity:.4f} at cost {fid_paper_row.resource_cost}"
        f" when only required to match the paper's own rate, versus"
        f" fidelity {fid_matched_row.fidelity:.4f} at cost"
        f" {fid_matched_row.resource_cost} under the stricter matched-cost"
        f" rate floor.",
        f"- Swapping the primary metric to cost"
        f" (`minimize_cost_with_constraints`) directly answers a"
        f' "cheapest hardware that still works" question the rate-'
        f" maximizing preset cannot answer on its own: cost="
        f"{cost_min_row.resource_cost} suffices to clear F>={F_MIN} alone,"
        f" while meeting both F>={F_MIN} and R>={paper_rate:.2f}"
        f" simultaneously needs"
        f" {next(r for r in rows if r.name == 'minimize_cost_with_constraints(f_min_and_r_min)').resource_cost}.",
        "- None of this required touching the search algorithms"
        " themselves -- `beam_search` and `dp_search` are already"
        " objective-agnostic (they only ever call `objective.score(...)`"
        " and `objective.is_feasible(...)`); every result above came"
        " from swapping the `ObjectiveConfig` argument alone.",
        "",
    ]
    cost_min_r_row = next(
        r for r in rows if r.name == "minimize_cost_with_constraints(f_min_and_r_min)"
    )
    if (
        cost_min_row.resource_cost == cost_min_r_row.resource_cost
        and cost_min_row.rate < paper_rate
    ):
        lines += [
            "- **Gotcha, worth flagging explicitly**: the `f_min`-only"
            f" cost-minimizing preset returns a cost={cost_min_row.resource_cost}"
            f" schedule with rate={cost_min_row.rate:.2f} -- *below* the"
            f" paper's own rate ({paper_rate:.2f}) -- even though a"
            f" *different* cost={cost_min_r_row.resource_cost} schedule"
            f" satisfying both F>={F_MIN} and R>={paper_rate:.2f} exists"
            " (found by the `f_min_and_r_min` preset above)."
            " `minimize_cost_with_constraints` has no secondary"
            " preference over rate once the cost floor is met, so among"
            " tied-cost feasible candidates it returns whichever one"
            " happens first in `beam_search`'s internal ordering -- not"
            " necessarily the best one by any other metric. Anyone using"
            " this preset who also cares about rate should add an"
            " explicit `r_min`, as the last preset does.",
            "",
        ]

    lines += [
        "Full data: [`results.csv`](results.csv).",
        "",
        "## Reproducing",
        "",
        "```bash",
        f"cd {_PROJECT_ROOT}",
        "source .venv/bin/activate",
        "python3 experiments/alternative_objectives.py",
        "```",
        "",
        f"Total wall-clock time: ~{elapsed_s:.0f}s (5 `beam_search` calls).",
        "",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines))


def main() -> None:
    t0 = time.time()
    rows, paper_rate, matched_rate = run_all()
    elapsed = time.time() - t0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_results_csv(rows, OUTPUT_DIR / "results.csv")
    write_readme(rows, paper_rate, matched_rate, elapsed)

    print(f"Done in {elapsed:.1f}s. Outputs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

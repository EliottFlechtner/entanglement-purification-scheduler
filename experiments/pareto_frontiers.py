"""
experiments/pareto_frontiers.py
=================================
Roadmap item 8: expose the optimizer's Pareto frontier directly (F vs. C
and F vs. R), rather than only ever reporting three cherry-picked points
per config (paper baseline / matched-cost / budget-relaxed), so a reader
can see the full cost-quality tradeoff curve the optimizer has access to.

Methodology
------------
`beam_search(net, obj, e_max, beam_width)` already returns *every*
evaluated candidate (not just the best-scoring one), sorted best-first
[search/heuristic.py docstring: "Returns: list[SearchResult]. All
evaluated candidates, sorted best-first."]. Calling it with a permissive
objective (`f_min=0.0`, i.e. no real fidelity floor) means nothing is
excluded from consideration on feasibility grounds, so the returned list
already *is* a (beam-limited, not exhaustive) sample of the schedule
space at that `(N, e_d, e_max)` point. This script:

  1. Runs `beam_search` once per representative config with a permissive
     objective and a generous `e_max` (larger than the paper's own
     resource cost, to see beyond the paper's own budget choice).
  2. Extracts `(resource_cost, fidelity, rate, success_prob, label)` for
     every returned candidate.
  3. Computes the non-dominated (Pareto-optimal) subset under two
     objective pairs: (minimize cost, maximize fidelity) and (maximize
     rate, maximize fidelity).
  4. Plots all candidates (grey) with the frontier highlighted and the
     paper baseline / link-level baseline marked for reference.

Caveat: `beam_search`'s frontier is beam-limited (`beam_width=25` by
default here, matching every other script in this repo), so the plotted
frontier is an *inner bound* on the true Pareto frontier, not a
certified exact one -- consistent with this repo's documented scope
limits for N=10 (see `search/heuristic.py`, `search/dp.py` docstrings).

Outputs
-------
    outputs/pareto_frontiers/points_<config>.csv   every evaluated candidate
    outputs/pareto_frontiers/fidelity_vs_cost_<config>.{png,svg}
    outputs/pareto_frontiers/fidelity_vs_rate_<config>.{png,svg}
    outputs/pareto_frontiers/README.md

Usage
-----
    .venv/bin/python3 experiments/pareto_frontiers.py
"""

from __future__ import annotations

import csv
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from hrgs_scheduler.cost_functions import ObjectiveConfig
from hrgs_scheduler.models.network_config import NetworkConfig
from hrgs_scheduler.reporting import new_figure, save_figure
from hrgs_scheduler.search import beam_search

BEAM_WIDTH = 25

OUTPUT_DIR = _PROJECT_ROOT / "outputs" / "pareto_frontiers"


@dataclass
class Point:
    label: str
    resource_cost: int
    fidelity: float
    success_prob: float
    rate: float
    role: str  # "paper_baseline" | "link_level_baseline" | "other"


@dataclass
class ConfigSpec:
    name: str
    description: str
    network: NetworkConfig
    e_max: int


CONFIGS: list[ConfigSpec] = [
    ConfigSpec(
        name="n10_ed0p01",
        description="Paper's own N=10 config at the headline noise point e_d=0.01",
        network=NetworkConfig.integrating_paper_config(e_d=0.01),
        e_max=150,  # 1.5x paper's own budget (100), to see beyond it
    ),
    ConfigSpec(
        name="n6_ed0p01",
        description="Same physics, shorter chain N=6, e_d=0.01",
        network=NetworkConfig.uniform(
            N=6,
            length=2.0,
            branching=(16, 14, 1),
            arm_count=18,
            p_x_inner=0.0,
            p_z_inner=0.0,
            e_d=0.01,
            gamma=0.0,
            c=2e5,
        ),
        e_max=90,  # 1.5x the N=6 analogue of the paper's cost (60)
    ),
]


def _dominates(
    a: Point, b: Point, specs: Sequence[tuple[Callable[[Point], float], str]]
) -> bool:
    """True if *a* Pareto-dominates *b* under *specs*=[(key_fn, 'max'|'min'), ...]."""
    as_good_everywhere = True
    strictly_better_somewhere = False
    for key_fn, direction in specs:
        va, vb = key_fn(a), key_fn(b)
        if direction == "max":
            if va < vb:
                as_good_everywhere = False
            if va > vb:
                strictly_better_somewhere = True
        else:  # "min"
            if va > vb:
                as_good_everywhere = False
            if va < vb:
                strictly_better_somewhere = True
    return as_good_everywhere and strictly_better_somewhere


def pareto_frontier(
    points: list[Point], specs: Sequence[tuple[Callable[[Point], float], str]]
) -> list[Point]:
    """Return the non-dominated subset of *points* under *specs*."""
    return [
        p
        for p in points
        if not any(_dominates(q, p, specs) for q in points if q is not p)
    ]


def run_one_config(spec: ConfigSpec) -> list[Point]:
    obj = ObjectiveConfig.maximize_rate_with_fidelity_floor(f_min=0.0)
    results = beam_search(spec.network, obj, e_max=spec.e_max, beam_width=BEAM_WIDTH)

    points: list[Point] = []
    for r in results:
        if r.label == "flexible_paper":
            role = "paper_baseline"
        elif r.label.startswith("link."):
            role = "link_level_baseline"
        else:
            role = "other"
        points.append(
            Point(
                label=r.label,
                resource_cost=r.eval_result.resource_cost,
                fidelity=r.eval_result.fidelity,
                success_prob=r.eval_result.success_prob,
                rate=r.eval_result.rate,
                role=role,
            )
        )
    return points


def write_points_csv(
    points: list[Point], frontier_fc: set[str], frontier_fr: set[str], path: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "label",
                "role",
                "resource_cost",
                "fidelity",
                "success_prob",
                "rate",
                "pareto_f_vs_c",
                "pareto_f_vs_r",
            ]
        )
        for p in points:
            key = f"{p.label}|{p.resource_cost}"
            writer.writerow(
                [
                    p.label,
                    p.role,
                    p.resource_cost,
                    p.fidelity,
                    p.success_prob,
                    p.rate,
                    key in frontier_fc,
                    key in frontier_fr,
                ]
            )


def _point_key(p: Point) -> str:
    return f"{p.label}|{p.resource_cost}"


def make_plots(
    spec: ConfigSpec,
    points: list[Point],
    frontier_fc: list[Point],
    frontier_fr: list[Point],
) -> None:
    paper_pts = [p for p in points if p.role == "paper_baseline"]
    link_pts = [p for p in points if p.role == "link_level_baseline"]

    # --- Fidelity vs. Cost ---
    fig, ax = new_figure()
    ax.scatter(
        [p.resource_cost for p in points],
        [p.fidelity for p in points],
        s=14,
        color="#c7c7c7",
        label="All evaluated candidates",
        zorder=1,
    )
    fc_sorted = sorted(frontier_fc, key=lambda p: p.resource_cost)
    ax.plot(
        [p.resource_cost for p in fc_sorted],
        [p.fidelity for p in fc_sorted],
        color="#1f77b4",
        marker="o",
        linestyle="-",
        label="Pareto frontier (min C, max F)",
        zorder=2,
    )
    if paper_pts:
        ax.scatter(
            [p.resource_cost for p in paper_pts],
            [p.fidelity for p in paper_pts],
            s=90,
            marker="*",
            color="#7f7f7f",
            edgecolors="black",
            label="Paper baseline (flexible_paper)",
            zorder=3,
        )
    if link_pts:
        ax.scatter(
            [p.resource_cost for p in link_pts],
            [p.fidelity for p in link_pts],
            s=50,
            marker="P",
            color="#ff7f0e",
            edgecolors="black",
            label="Link-level baseline",
            zorder=3,
        )
    ax.set_xlabel("Resource cost $C$ (Gen node count)")
    ax.set_ylabel("Fidelity $F$")
    ax.set_title(f"Fidelity vs. Cost Pareto frontier ({spec.name})")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    save_figure(fig, OUTPUT_DIR / f"fidelity_vs_cost_{spec.name}")

    # --- Fidelity vs. Rate ---
    fig, ax = new_figure()
    ax.scatter(
        [p.rate for p in points],
        [p.fidelity for p in points],
        s=14,
        color="#c7c7c7",
        label="All evaluated candidates",
        zorder=1,
    )
    fr_sorted = sorted(frontier_fr, key=lambda p: p.rate)
    ax.plot(
        [p.rate for p in fr_sorted],
        [p.fidelity for p in fr_sorted],
        color="#d62728",
        marker="^",
        linestyle="-",
        label="Pareto frontier (max R, max F)",
        zorder=2,
    )
    if paper_pts:
        ax.scatter(
            [p.rate for p in paper_pts],
            [p.fidelity for p in paper_pts],
            s=90,
            marker="*",
            color="#7f7f7f",
            edgecolors="black",
            label="Paper baseline (flexible_paper)",
            zorder=3,
        )
    if link_pts:
        ax.scatter(
            [p.rate for p in link_pts],
            [p.fidelity for p in link_pts],
            s=50,
            marker="P",
            color="#ff7f0e",
            edgecolors="black",
            label="Link-level baseline",
            zorder=3,
        )
    ax.set_xlabel("Rate $R$")
    ax.set_ylabel("Fidelity $F$")
    ax.set_title(f"Fidelity vs. Rate Pareto frontier ({spec.name})")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    save_figure(fig, OUTPUT_DIR / f"fidelity_vs_rate_{spec.name}")


def write_readme(
    per_config: dict[str, tuple[list[Point], list[Point], list[Point]]],
    elapsed_s: float,
) -> None:
    lines = [
        "# Pareto Frontiers: Fidelity vs. Cost, Fidelity vs. Rate",
        "",
        "Roadmap item 8 ([docs/archive/Roadmap Remaining"
        " Work.md](../../docs/archive/Roadmap%20Remaining%20Work.md)):"
        " exposes the optimizer's full cost-quality tradeoff curve"
        " directly, instead of only ever reporting the three"
        " cherry-picked points (paper baseline / matched-cost /"
        " budget-relaxed) used elsewhere in this repo"
        " (`outputs/headline_experiment_n10/`, `outputs/sweep_ed_n10/`).",
        "",
        "Method: `beam_search(net, obj, e_max, beam_width=25)` with a"
        " permissive objective (`f_min=0.0`) returns every evaluated"
        " candidate, sorted best-first; every candidate's"
        " `(resource_cost, fidelity, rate)` is extracted and the"
        " non-dominated subset computed under two objective pairs:"
        " (minimize cost, maximize fidelity) and (maximize rate, maximize"
        " fidelity). Caveat: `beam_search`'s own frontier is beam-limited"
        " (`beam_width=25`), so this is an *inner bound* on the true"
        " Pareto frontier, not a certified-exact one, at N=10 -- the"
        " same documented scope limit as every other N=10 result in this"
        " repo.",
        "",
    ]
    for spec in CONFIGS:
        points, frontier_fc, frontier_fr = per_config[spec.name]
        lines += [
            f"## `{spec.name}`",
            "",
            f"{spec.description}. `e_max={spec.e_max}`.",
            "",
            f"{len(points)} candidates evaluated;"
            f" {len(frontier_fc)} on the F-vs-C frontier,"
            f" {len(frontier_fr)} on the F-vs-R frontier.",
            "",
        ]
        paper_pts = [p for p in points if p.role == "paper_baseline"]
        if paper_pts:
            paper = paper_pts[0]
            on_fc = _point_key(paper) in {_point_key(p) for p in frontier_fc}
            on_fr = _point_key(paper) in {_point_key(p) for p in frontier_fr}
            lines.append(
                f"Paper baseline: cost={paper.resource_cost},"
                f" F={paper.fidelity:.4f}, R={paper.rate:.2f}."
                f" On F-vs-C frontier: {'yes' if on_fc else 'no'}."
                f" On F-vs-R frontier: {'yes' if on_fr else 'no'}."
            )
        lines += [
            "",
            "F-vs-C frontier (sorted by cost):",
            "",
            "| Cost | Fidelity | Label |",
            "|---|---|---|",
        ]
        for p in sorted(frontier_fc, key=lambda p: p.resource_cost):
            lines.append(f"| {p.resource_cost} | {p.fidelity:.4f} | `{p.label}` |")
        lines += [
            "",
            f"Full data: [`points_{spec.name}.csv`](points_{spec.name}.csv).",
            "",
            "Figures: "
            f"[`fidelity_vs_cost_{spec.name}.png`](fidelity_vs_cost_{spec.name}.png),"
            f" [`fidelity_vs_rate_{spec.name}.png`](fidelity_vs_rate_{spec.name}.png).",
            "",
        ]

    lines += [
        "## Reproducing",
        "",
        "```bash",
        f"cd {_PROJECT_ROOT}",
        "source .venv/bin/activate",
        "python3 experiments/pareto_frontiers.py",
        "```",
        "",
        f"Total wall-clock time: ~{elapsed_s:.0f}s.",
        "",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines))


def main() -> None:
    t0 = time.time()
    per_config: dict[str, tuple[list[Point], list[Point], list[Point]]] = {}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for spec in CONFIGS:
        print(f"Running config={spec.name} (e_max={spec.e_max}) ...", flush=True)
        points = run_one_config(spec)
        frontier_fc = pareto_frontier(
            points, [(lambda p: p.resource_cost, "min"), (lambda p: p.fidelity, "max")]
        )
        frontier_fr = pareto_frontier(
            points, [(lambda p: p.rate, "max"), (lambda p: p.fidelity, "max")]
        )
        per_config[spec.name] = (points, frontier_fc, frontier_fr)

        write_points_csv(
            points,
            {_point_key(p) for p in frontier_fc},
            {_point_key(p) for p in frontier_fr},
            OUTPUT_DIR / f"points_{spec.name}.csv",
        )
        make_plots(spec, points, frontier_fc, frontier_fr)

    elapsed = time.time() - t0
    write_readme(per_config, elapsed)

    print(f"\nDone in {elapsed:.1f}s. Outputs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

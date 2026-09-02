"""
experiments/thesis_scripts/_thesis_fig_heterogeneous.py
==========================================================
One-off regeneration of the Chapter 6 per-hop heterogeneous-network
figures (weak-link resource allocation + randomized-sweep scatter).

Does NOT rerun any search: reads the already-computed
`outputs/random_network_adaptation/100 seeds/*.csv`. Labels are
translated to plain English (no DAG-label/snake_case identifiers baked
into the legend), per the same convention as `_thesis_fig_netgen.py`.

Usage
-----
    .venv/bin/python3 experiments/thesis_scripts/_thesis_fig_heterogeneous.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = _PROJECT_ROOT / "thesis" / "figures" / "results"
DATA_DIR = _PROJECT_ROOT / "outputs" / "random_network_adaptation" / "100 seeds"

FIGSIZE = (7.2, 4.2)
DPI = 200


def make_weak_link_figure() -> None:
    rows = list(csv.DictReader((DATA_DIR / "weak_link_gen_allocation.csv").open()))
    hops = [int(r["hop"]) for r in rows]
    noise = [float(r["inner_error_per_hop"]) for r in rows]
    adaptive = [int(r["adaptive_gen_count"]) for r in rows]
    uniform = [int(r["link_gen_count"]) for r in rows]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    width = 0.35
    ax.bar(
        [h - width / 2 for h in hops],
        adaptive,
        width,
        color="#d62728",
        label="Optimizer's schedule",
    )
    ax.bar(
        [h + width / 2 for h in hops],
        uniform,
        width,
        color="#7f7f7f",
        label="Uniform link-level recipe",
    )
    ax.set_xticks(hops)
    ax.set_xticklabels([f"hop {h}" for h in hops])
    ax.set_ylabel("Gen-node count spent at this hop")
    ax.grid(alpha=0.3, axis="y")

    ax2 = ax.twinx()
    ax2.plot(
        hops,
        noise,
        color="black",
        marker="o",
        linestyle=":",
        label="Inner-qubit error rate (this hop)",
    )
    ax2.set_ylabel("Inner-qubit error rate per hop")

    ax.set_ylim(0, 9.5)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(
        h1 + h2,
        l1 + l2,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.22),
        ncol=2,
        fontsize=8.5,
    )
    fig.tight_layout()
    for fmt in ("png", "svg"):
        fig.savefig(
            OUT_DIR / f"weak_link_allocation.{fmt}", dpi=DPI, bbox_inches="tight"
        )


def make_random_sweep_figure() -> None:
    rows = list(csv.DictReader((DATA_DIR / "random_sweep_results.csv").open()))
    comparable = [r for r in rows if r["rate_improvement_pct"] != ""]
    hets = [float(r["heterogeneity_cv"]) for r in comparable]
    imps = [float(r["rate_improvement_pct"]) for r in comparable]

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.scatter(
        hets,
        imps,
        color="#1f77b4",
        alpha=0.8,
        label="Optimizer's rate improvement over the\nbest feasible uniform recipe",
    )
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xlabel("Per-hop noise heterogeneity (coefficient of variation)")
    ax.set_ylabel("Optimizer rate improvement over\nuniform baseline (%)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()
    for fmt in ("png", "svg"):
        fig.savefig(
            OUT_DIR / f"random_sweep_improvement_vs_heterogeneity.{fmt}",
            dpi=DPI,
            bbox_inches="tight",
        )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_weak_link_figure()
    make_random_sweep_figure()
    print(f"Wrote regenerated heterogeneous-network figures to {OUT_DIR}")


if __name__ == "__main__":
    main()

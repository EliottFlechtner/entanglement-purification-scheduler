"""
experiments/_thesis_fig_pareto.py
===================================
One-off regeneration of the Chapter 6 Pareto frontier figures for
thesis placement (two 0.48\\textwidth subfigures side by side).

Does NOT rerun any search or touch underlying data: reads the already-
computed `outputs/pareto_frontiers/points_n10_ed0p01.csv` (see that
experiment's own README) and re-plots with a figure size, font scale,
and legend placement chosen for legibility once shrunk to half the
thesis text width -- the default `hrgs_scheduler.reporting.plots`
figsize (7.0x4.5in, ~10pt fonts) becomes illegible at that scale (see
docs note on this regeneration). Labels are also translated to the
thesis's plain-English convention instead of raw code identifiers.

Usage
-----
    .venv/bin/python3 experiments/_thesis_fig_pareto.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import matplotlib.pyplot as plt

OUT_DIR = _PROJECT_ROOT / "thesis" / "figures" / "results"
CSV_PATH = _PROJECT_ROOT / "outputs" / "pareto_frontiers" / "points_n10_ed0p01.csv"

# Sized to render legibly at 0.48\textwidth (~3.0in printed) with no
# extra downscaling penalty, unlike the shared 7.0x4.5in report figsize.
FIGSIZE = (4.6, 3.9)
DPI = 200


def _read_points() -> list[dict]:
    with CSV_PATH.open() as f:
        return list(csv.DictReader(f))


def _role(row: dict) -> str:
    return row["role"]


def make_fidelity_vs_cost(rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE)

    others = [r for r in rows if _role(r) == "other"]
    frontier = sorted(
        (r for r in rows if r["pareto_f_vs_c"] == "True"),
        key=lambda r: float(r["resource_cost"]),
    )
    paper = [r for r in rows if _role(r) == "paper_baseline"]
    link = [r for r in rows if _role(r) == "link_level_baseline"]

    ax.scatter(
        [float(r["resource_cost"]) for r in others],
        [float(r["fidelity"]) for r in others],
        s=10,
        color="#c7c7c7",
        label="Other candidates",
        zorder=1,
    )
    ax.plot(
        [float(r["resource_cost"]) for r in frontier],
        [float(r["fidelity"]) for r in frontier],
        color="#1f77b4",
        marker="o",
        markersize=4,
        linewidth=1.4,
        label="Pareto frontier",
        zorder=2,
    )
    if paper:
        ax.scatter(
            [float(r["resource_cost"]) for r in paper],
            [float(r["fidelity"]) for r in paper],
            s=70,
            marker="*",
            color="#7f7f7f",
            edgecolors="black",
            label="Paper schedule",
            zorder=3,
        )
    if link:
        ax.scatter(
            [float(r["resource_cost"]) for r in link],
            [float(r["fidelity"]) for r in link],
            s=36,
            marker="P",
            color="#ff7f0e",
            edgecolors="black",
            label="Link-level baseline",
            zorder=3,
        )

    ax.set_xlabel("Resource cost $C$", fontsize=11)
    ax.set_ylabel("Fidelity $F$", fontsize=11)
    ax.tick_params(labelsize=9.5)
    ax.grid(alpha=0.3)
    ax.legend(
        fontsize=8.5,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        frameon=False,
    )
    fig.tight_layout()
    for fmt in ("png", "svg"):
        fig.savefig(
            OUT_DIR / f"fidelity_vs_cost_n10.{fmt}", dpi=DPI, bbox_inches="tight"
        )
    plt.close(fig)


def make_fidelity_vs_rate(rows: list[dict]) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE)

    others = [r for r in rows if _role(r) == "other"]
    frontier = sorted(
        (r for r in rows if r["pareto_f_vs_r"] == "True"),
        key=lambda r: float(r["rate"]),
    )
    paper = [r for r in rows if _role(r) == "paper_baseline"]
    link = [r for r in rows if _role(r) == "link_level_baseline"]

    ax.scatter(
        [float(r["rate"]) for r in others],
        [float(r["fidelity"]) for r in others],
        s=10,
        color="#c7c7c7",
        label="Other candidates",
        zorder=1,
    )
    ax.plot(
        [float(r["rate"]) for r in frontier],
        [float(r["fidelity"]) for r in frontier],
        color="#d62728",
        marker="^",
        markersize=4,
        linewidth=1.4,
        label="Pareto frontier",
        zorder=2,
    )
    if paper:
        ax.scatter(
            [float(r["rate"]) for r in paper],
            [float(r["fidelity"]) for r in paper],
            s=70,
            marker="*",
            color="#7f7f7f",
            edgecolors="black",
            label="Paper schedule",
            zorder=3,
        )
    if link:
        ax.scatter(
            [float(r["rate"]) for r in link],
            [float(r["fidelity"]) for r in link],
            s=36,
            marker="P",
            color="#ff7f0e",
            edgecolors="black",
            label="Link-level baseline",
            zorder=3,
        )

    ax.set_xlabel("Rate $R$", fontsize=11)
    ax.set_ylabel("Fidelity $F$", fontsize=11)
    ax.tick_params(labelsize=9.5)
    ax.grid(alpha=0.3)
    ax.legend(
        fontsize=8.5,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.16),
        frameon=False,
    )
    fig.tight_layout()
    for fmt in ("png", "svg"):
        fig.savefig(
            OUT_DIR / f"fidelity_vs_rate_n10.{fmt}", dpi=DPI, bbox_inches="tight"
        )
    plt.close(fig)


def main() -> None:
    rows = _read_points()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_fidelity_vs_cost(rows)
    make_fidelity_vs_rate(rows)
    print(f"Wrote regenerated Pareto figures to {OUT_DIR}")


if __name__ == "__main__":
    main()

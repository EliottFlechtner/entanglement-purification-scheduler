"""
experiments/_thesis_fig_edsweep.py
====================================
One-off regeneration of the Chapter 6 e_d-sweep figures (Figure 6.1) for
thesis placement (two 0.48\\textwidth subfigures side by side), matching
the sizing/legend conventions used by `_thesis_fig_pareto.py`.

Does NOT rerun any search or touch underlying data: reads the already-
computed `outputs/sweep_ed_n10/results.csv`. The in-plot title is
dropped (redundant with the LaTeX subfigure caption) to free vertical
space, and fonts/figure size are tuned for legibility once shrunk to
half the thesis text width.

Usage
-----
    .venv/bin/python3 experiments/_thesis_fig_edsweep.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import matplotlib.pyplot as plt

OUT_DIR = _PROJECT_ROOT / "thesis" / "figures" / "results"
CSV_PATH = _PROJECT_ROOT / "outputs" / "sweep_ed_n10" / "results.csv"

FIGSIZE = (4.6, 3.9)
DPI = 200

STYLE = {
    "paper_baseline": dict(color="#7f7f7f", marker="s", linestyle="--", label="Paper schedule"),
    "optimizer_matched_cost": dict(color="#1f77b4", marker="o", linestyle="-", label="Optimizer (matched cost)"),
    "optimizer_budget_relaxed": dict(color="#d62728", marker="^", linestyle="-", label="Optimizer (budget-relaxed)"),
}
VARIANT_ORDER = ["paper_baseline", "optimizer_matched_cost", "optimizer_budget_relaxed"]


def _read_series() -> dict[str, list[tuple[float, float, float]]]:
    """variant -> [(e_d, fidelity, rate), ...], sorted by e_d."""
    series: dict[str, list[tuple[float, float, float]]] = defaultdict(list)
    with CSV_PATH.open() as f:
        for row in csv.DictReader(f):
            v = row["variant"]
            if v not in STYLE:
                continue
            series[v].append((float(row["e_d"]), float(row["fidelity"]), float(row["rate"])))
    for v in series:
        series[v].sort(key=lambda t: t[0])
    return series


def make_rate_plot(series: dict[str, list[tuple[float, float, float]]]) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for variant in VARIANT_ORDER:
        pts = series[variant]
        ax.plot(
            [p[0] for p in pts], [p[2] for p in pts],
            markersize=5.5, linewidth=1.6, **STYLE[variant],
        )
    ax.set_xlabel("Depolarizing error $e_d$", fontsize=11)
    ax.set_ylabel("Rate $R$", fontsize=11)
    ax.tick_params(labelsize=9.5)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8.5, ncol=1, loc="lower left", framealpha=0.9)
    fig.tight_layout()
    for fmt in ("png", "svg"):
        fig.savefig(OUT_DIR / f"rate_vs_ed.{fmt}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def make_fidelity_plot(series: dict[str, list[tuple[float, float, float]]]) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for variant in VARIANT_ORDER:
        pts = series[variant]
        ax.plot(
            [p[0] for p in pts], [p[1] for p in pts],
            markersize=5.5, linewidth=1.6, **STYLE[variant],
        )
    ax.axhline(0.9, color="black", linestyle=":", linewidth=1.1, label="$f_{\\min}=0.9$")
    ax.set_xlabel("Depolarizing error $e_d$", fontsize=11)
    ax.set_ylabel("Fidelity $F$", fontsize=11)
    ax.tick_params(labelsize=9.5)
    ax.grid(alpha=0.3)
    ax.legend(
        fontsize=8.5, ncol=2, loc="upper center",
        bbox_to_anchor=(0.5, -0.16), frameon=False,
    )
    fig.tight_layout()
    for fmt in ("png", "svg"):
        fig.savefig(OUT_DIR / f"fidelity_vs_ed.{fmt}", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    series = _read_series()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_rate_plot(series)
    make_fidelity_plot(series)
    print(f"Wrote regenerated e_d-sweep figures to {OUT_DIR}")


if __name__ == "__main__":
    main()

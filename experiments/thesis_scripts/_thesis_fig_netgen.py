"""
experiments/_thesis_fig_netgen.py
====================================
One-off regeneration of the Chapter 6 network-generalization figure
(promoted to a full-width single figure, since this is the thesis's
headline "paper schedule breaks, optimizer doesn't" result).

Does NOT rerun any search or touch underlying data: reads the already-
computed `outputs/sweep_network_sensitivity/results.csv`. Labels are
translated to plain English (no snake_case config/variant identifiers
baked into the legend).

Usage
-----
    .venv/bin/python3 experiments/_thesis_fig_netgen.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import matplotlib.pyplot as plt

OUT_DIR = _PROJECT_ROOT / "thesis" / "figures" / "results"
CSV_PATH = _PROJECT_ROOT / "outputs" / "sweep_network_sensitivity" / "results.csv"

FIGSIZE = (7.2, 4.2)
DPI = 200
F_MIN = 0.9

CONFIG_ORDER = ["paper_ideal", "nonzero_inner_arm18", "nonzero_inner_arm6"]
CONFIG_LABELS = {
    "paper_ideal": "Paper's reference\nconfig (ideal)",
    "nonzero_inner_arm18": "Non-ideal inner\nerror, 18 arms",
    "nonzero_inner_arm6": "Non-ideal inner\nerror, 6 arms",
}
VARIANT_ORDER = ["paper_baseline", "optimizer_matched_cost", "optimizer_budget_relaxed"]
VARIANT_STYLE = {
    "paper_baseline": dict(color="#7f7f7f", label="Paper schedule"),
    "optimizer_matched_cost": dict(color="#1f77b4", label="Optimizer (matched cost)"),
    "optimizer_budget_relaxed": dict(
        color="#d62728", label="Optimizer (budget-relaxed)"
    ),
}


def _read_rows() -> dict[str, dict[str, dict]]:
    by_config: dict[str, dict[str, dict]] = {}
    with CSV_PATH.open() as f:
        for row in csv.DictReader(f):
            by_config.setdefault(row["config_name"], {})[row["variant"]] = row
    return by_config


def main() -> None:
    by_config = _read_rows()
    fig, ax = plt.subplots(figsize=FIGSIZE)

    x = list(range(len(CONFIG_ORDER)))
    width = 0.26
    for i, variant in enumerate(VARIANT_ORDER):
        offsets = [xi + (i - 1) * width for xi in x]
        heights = [float(by_config[cfg][variant]["fidelity"]) for cfg in CONFIG_ORDER]
        feasible = [
            by_config[cfg][variant]["meets_floor"] == "True" for cfg in CONFIG_ORDER
        ]
        bars = ax.bar(offsets, heights, width, **VARIANT_STYLE[variant])
        # Hatch infeasible bars so the "paper schedule breaks" point reads
        # from the figure itself, not just the caption/table.
        for bar, ok in zip(bars, feasible):
            if not ok:
                bar.set_hatch("////")
                bar.set_edgecolor("black")

    ax.axhline(
        F_MIN,
        color="black",
        linestyle=":",
        linewidth=1.2,
        label=f"$f_{{\\min}}={F_MIN}$",
    )
    ax.set_xticks(x)
    ax.set_xticklabels([CONFIG_LABELS[c] for c in CONFIG_ORDER], fontsize=10)
    ax.set_ylabel("Fidelity $F$", fontsize=11)
    ax.set_ylim(0.6, 1.0)
    ax.grid(alpha=0.3, axis="y")
    ax.tick_params(labelsize=9.5)
    ax.legend(fontsize=9, ncol=2, loc="lower left")
    fig.tight_layout()
    for fmt in ("png", "svg"):
        fig.savefig(OUT_DIR / f"fidelity_by_config.{fmt}", dpi=DPI, bbox_inches="tight")
    print(f"Wrote regenerated network-generalization figure to {OUT_DIR}")


if __name__ == "__main__":
    main()

"""
experiments/thesis_scripts/_thesis_fig_timing_gamma.py
=========================================================
Re-export of the Chapter 6 / Appendix B gamma-sensitivity figures
(fidelity vs. gamma, rate vs. gamma) for the three canonical schedules.

Does NOT rerun any sweep: reads the already-computed
`outputs/sweep_gamma_and_tau_emit/gamma_canonical.csv`.

Usage
-----
    .venv/bin/python3 experiments/thesis_scripts/_thesis_fig_timing_gamma.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = _PROJECT_ROOT / "thesis" / "figures" / "results"
DATA_DIR = _PROJECT_ROOT / "outputs" / "sweep_gamma_and_tau_emit"

FIGSIZE = (7.2, 4.4)
DPI = 200

SCHEDULE_STYLE = {
    "raw": dict(color="#7f7f7f", label="Raw chain (no purification)"),
    "flexible_optimistic": dict(color="#1f77b4", label="Optimistic pumping"),
    "baseline_heralded_pumping": dict(color="#ff7f0e", label="Heralded pumping"),
}
SCHEDULE_ORDER = ["raw", "flexible_optimistic", "baseline_heralded_pumping"]


def _read_by_schedule() -> dict[str, list[tuple[float, float, float]]]:
    rows = list(csv.DictReader((DATA_DIR / "gamma_canonical.csv").open()))
    by_schedule: dict[str, list[tuple[float, float, float]]] = {}
    for r in rows:
        gamma = float(r["param_value"])
        if gamma <= 0:
            continue  # log-scale x-axis cannot show gamma=0
        by_schedule.setdefault(r["schedule"], []).append(
            (gamma, float(r["fidelity"]), float(r["rate"]))
        )
    for pts in by_schedule.values():
        pts.sort()
    return by_schedule


def make_fidelity_figure(
    by_schedule: dict[str, list[tuple[float, float, float]]],
) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for name in SCHEDULE_ORDER:
        gammas, fids, _ = zip(*by_schedule[name])
        ax.plot(gammas, fids, marker="o", **SCHEDULE_STYLE[name])
    ax.axhline(
        0.25,
        color="black",
        linewidth=0.8,
        linestyle=":",
        label="Maximally mixed ($F=0.25$)",
    )
    ax.set_xscale("log")
    ax.set_xlabel(r"Memory dephasing rate $\gamma$ (log scale)", fontsize=12)
    ax.set_ylabel("Fidelity $F$", fontsize=12)
    ax.set_title(r"Fidelity vs. $\gamma$", fontsize=13)
    ax.tick_params(axis="both", labelsize=11)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=11, loc="best")
    fig.tight_layout()
    for fmt in ("png", "svg"):
        fig.savefig(OUT_DIR / f"gamma_fidelity.{fmt}", dpi=DPI, bbox_inches="tight")


def make_rate_figure(by_schedule: dict[str, list[tuple[float, float, float]]]) -> None:
    fig, ax = plt.subplots(figsize=FIGSIZE)
    for name in SCHEDULE_ORDER:
        gammas, _, rates = zip(*by_schedule[name])
        ax.plot(gammas, rates, marker="o", **SCHEDULE_STYLE[name])
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(r"Memory dephasing rate $\gamma$ (log scale)", fontsize=12)
    ax.set_ylabel("Rate (log scale)", fontsize=12)
    ax.set_title(r"Rate vs. $\gamma$", fontsize=13)
    ax.tick_params(axis="both", labelsize=11)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=11, loc="best")
    fig.tight_layout()
    for fmt in ("png", "svg"):
        fig.savefig(OUT_DIR / f"gamma_rate.{fmt}", dpi=DPI, bbox_inches="tight")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_schedule = _read_by_schedule()
    make_fidelity_figure(by_schedule)
    make_rate_figure(by_schedule)
    print(f"Wrote regenerated gamma timing figures to {OUT_DIR}")


if __name__ == "__main__":
    main()

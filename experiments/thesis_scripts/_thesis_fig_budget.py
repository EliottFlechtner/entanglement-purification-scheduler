"""
experiments/thesis_scripts/_thesis_fig_budget.py
===================================================
Regeneration of the Chapter 6 budget-scaling figure (Figure 6.6),
extending the plotted N-domain from the measured range (N=10-28) out to
N in [5, 40] so the reader can see the paper's linear formula and the
fitted power law visibly diverge over a wider, easier-to-read range.

Does NOT invent new measured data points: the only real data plotted is
the already-computed `outputs/sweep_min_budget_vs_n/results.csv` (12
points, N=10-28), shown as solid markers. The fitted power law
(re-derived here from those same 12 points, matching the formula quoted
in the thesis text) and the paper's own exact linear formula (e_max=10N)
are both closed-form curves that are well-defined at every N -- plotting
them outside N=10-28 is a mathematical extrapolation of an already-real
fit, not fabricated data, and is drawn with a lighter/dashed style and a
distinct legend entry ("extrapolated") to keep this distinction visible
on the figure itself, not just in the caption.

Usage
-----
    .venv/bin/python3 experiments/thesis_scripts/_thesis_fig_budget.py
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import matplotlib.pyplot as plt

OUT_DIR = _PROJECT_ROOT / "thesis" / "figures" / "results"
CSV_PATH = _PROJECT_ROOT / "outputs" / "sweep_min_budget_vs_n" / "results.csv"

FIGSIZE = (7.0, 4.5)
DPI = 200

# Plotted domain for the two closed-form reference curves. The measured
# data only covers N=10-28; everything outside that is extrapolation.
N_PLOT_MIN = 5
N_PLOT_MAX = 40
MEASURED_N_MIN = 10
MEASURED_N_MAX = 28


def _read_measured() -> list[tuple[int, int]]:
    """[(N, min_feasible_e_max), ...] from the real sweep output."""
    rows = []
    with CSV_PATH.open() as f:
        for row in csv.DictReader(f):
            rows.append((int(row["N"]), int(row["min_feasible_e_max"])))
    return sorted(rows)


def _power_law_fit(points: list[tuple[int, int]]) -> tuple[float, float]:
    """Least-squares fit of e_max_min ~ a * N^b on log-log data."""
    xs = [math.log(n) for n, _ in points]
    ys = [math.log(v) for _, v in points]
    n = len(points)
    sum_x, sum_y = sum(xs), sum(ys)
    sum_xx = sum(x * x for x in xs)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    b = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
    log_a = (sum_y - b * sum_x) / n
    return math.exp(log_a), b


def main() -> None:
    measured = _read_measured()
    a, b = _power_law_fit(measured)
    print(f"Re-derived fit from real data: a={a:.3f}, b={b:.3f}")

    full_range = list(range(N_PLOT_MIN, N_PLOT_MAX + 1))
    measured_range = [n for n in full_range if MEASURED_N_MIN <= n <= MEASURED_N_MAX]
    extrap_low = [n for n in full_range if n < MEASURED_N_MIN]
    extrap_high = [n for n in full_range if n > MEASURED_N_MAX]

    fig, ax = plt.subplots(figsize=FIGSIZE)

    # Paper's exact linear formula: well-defined at every N, no fitting
    # involved, so it is drawn as a single solid line across the whole
    # extended domain.
    ax.plot(
        full_range,
        [10 * n for n in full_range],
        linestyle="--",
        color="black",
        linewidth=1.3,
        label="Paper's formula: $E_{max}=10N$",
    )

    # Fitted power law: solid over the measured range, dotted/lighter
    # where it is an extrapolation beyond the tested N.
    ax.plot(
        measured_range,
        [a * (n**b) for n in measured_range],
        linestyle="-",
        color="tab:blue",
        linewidth=1.6,
        label=f"Power-law fit (measured range): ${a:.2f}\\cdot N^{{{b:.2f}}}$",
    )
    for seg in (extrap_low, extrap_high):
        if not seg:
            continue
        # include the nearest measured endpoint so the extrapolated
        # segment visually connects to the fitted curve.
        anchor = MEASURED_N_MIN if seg is extrap_low else MEASURED_N_MAX
        pts = sorted(seg + [anchor])
        ax.plot(
            pts,
            [a * (n**b) for n in pts],
            linestyle=":",
            color="tab:blue",
            linewidth=1.6,
            alpha=0.6,
        )
    # One dedicated legend entry for the extrapolated portions.
    ax.plot(
        [],
        [],
        linestyle=":",
        color="tab:blue",
        alpha=0.6,
        label="Power-law fit (extrapolated beyond N=10--28)",
    )

    ax.scatter(
        [n for n, _ in measured],
        [v for _, v in measured],
        color="tab:red",
        marker="o",
        s=32,
        zorder=3,
        label="Minimum feasible $E_{max}$ (measured, N=10--28)",
    )

    ax.set_xlabel("Number of hops $N$", fontsize=11)
    ax.set_ylabel("Minimum feasible resource cost $E_{max}$", fontsize=11)
    ax.tick_params(labelsize=9.5)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8.5, loc="upper left")
    fig.tight_layout()
    for fmt in ("png",):
        fig.savefig(OUT_DIR / f"min_budget_vs_n.{fmt}", dpi=DPI, bbox_inches="tight")
    print(f"Wrote regenerated budget-scaling figure to {OUT_DIR}")


if __name__ == "__main__":
    main()

"""
One-off: real bisection runs for the N values missing from
outputs/sweep_min_budget_vs_n/results.csv within N<=20 (11,13,15,17,19).
Appends real rows to the existing CSV (does not touch or reinterpret any
existing row) and regenerates the plot/README via the existing
sweep_min_budget_vs_n module functions.

N>20 gaps (25, 27) are intentionally NOT computed here per explicit
instruction; the existing fitted curve already visually covers them as
an approximation, not as measured points.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

import experiments.sweeps.sweep_min_budget_vs_n as m

MISSING_N = [11, 13, 15, 17, 19]


def main() -> None:
    existing = {r.N: r for r in m.read_results_csv(m.OUTPUT_DIR / "results.csv")}
    t0 = time.time()
    new_rows = []
    for N in MISSING_N:
        if N in existing:
            print(f"N={N}: already present, skipping", flush=True)
            continue
        print(f"N={N}: starting bisection for minimum feasible e_max...", flush=True)
        new_rows.append(m.find_min_budget(N))

    all_rows = sorted(list(existing.values()) + new_rows, key=lambda r: r.N)
    m.write_results_csv(all_rows, m.OUTPUT_DIR / "results.csv")
    fit = m.make_plot(all_rows)
    total_elapsed = time.time() - t0
    m.write_readme(all_rows, fit, total_elapsed)
    print(f"\nDone in {total_elapsed:.1f}s. New fit: a={fit[0]:.3f}, b={fit[1]:.3f}")


if __name__ == "__main__":
    main()

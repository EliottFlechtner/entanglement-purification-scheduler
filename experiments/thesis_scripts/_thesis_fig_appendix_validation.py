"""
experiments/thesis_scripts/_thesis_fig_appendix_validation.py
================================================================
Regenerates Appendix Table A.1 (evaluator fidelity vs. e_d for the three
canonical schedules) as a figure instead, per the `TRANSFORM_TABLE`
marker in `thesis/chapters/appendix.tex`.

Recomputes the exact same curves as `experiments/fig5_fidelity_vs_noise.py`
directly from `src/hrgs_scheduler` (not by re-reading that script's
console output), at N=10 across e_d in [0, 0.01].

Usage
-----
    .venv/bin/python3 experiments/thesis_scripts/_thesis_fig_appendix_validation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from hrgs_scheduler.models import NetworkConfig
from hrgs_scheduler.reporting import new_figure, plot_lines, save_figure
from hrgs_scheduler.schedule import Evaluator, ScheduleDAG

N_HOPS = 10
N_PUR = 5
N_POINTS = 20

OUT_DIR = _PROJECT_ROOT / "thesis" / "figures" / "appendix"

_VARIANT_LABELS = {
    "raw": "Raw (no purification)",
    "baseline": "Baseline (heralded pumping)",
    "flexible": "Flexible (optimistic pumping)",
}


def compute_curves() -> dict[str, list[tuple[float, float]]]:
    curves: dict[str, list[tuple[float, float]]] = {
        "raw": [],
        "baseline": [],
        "flexible": [],
    }
    for i in range(N_POINTS):
        e_d = i * 0.01 / (N_POINTS - 1)
        cfg = NetworkConfig.integrating_paper_config(e_d=e_d)
        ev = Evaluator(cfg)
        curves["raw"].append(
            (e_d, ev.evaluate(ScheduleDAG.raw_chain(N=N_HOPS)).fidelity)
        )
        curves["baseline"].append(
            (
                e_d,
                ev.evaluate(
                    ScheduleDAG.baseline_end_node_pumping(N=N_HOPS, n_pur=N_PUR)
                ).fidelity,
            )
        )
        curves["flexible"].append(
            (e_d, ev.evaluate(ScheduleDAG.flexible_paper_schedule(N=N_HOPS)).fidelity)
        )
    return curves


def main() -> None:
    curves = compute_curves()
    fig, ax = new_figure()
    plot_lines(
        ax,
        curves,
        xlabel="Depolarizing error probability $e_d$",
        ylabel="Fidelity $F$",
        title=f"Evaluator fidelity vs. $e_d$ ($N={N_HOPS}$)",
        style_overrides={k: {"label": v} for k, v in _VARIANT_LABELS.items()},
    )
    save_figure(fig, OUT_DIR / "fidelity_vs_ed_validation")
    print(f"Wrote appendix validation figure to {OUT_DIR}")


if __name__ == "__main__":
    main()

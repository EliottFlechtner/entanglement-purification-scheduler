"""
experiments/thesis_scripts/_thesis_fig_runtime_pumping.py
============================================================
Re-export of the Appendix B search wall-clock runtime vs. N figure
(dp_search vs. beam_search, same-span pumping enabled).

Does NOT rerun any search: reads the already-computed
`outputs/sweep_timing_pumping/results.csv`.

Usage
-----
    .venv/bin/python3 experiments/thesis_scripts/_thesis_fig_runtime_pumping.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = _PROJECT_ROOT / "thesis" / "figures" / "appendix"
DATA_CSV = _PROJECT_ROOT / "outputs" / "sweep_timing_pumping" / "results.csv"

FIGSIZE = (7.2, 4.4)
DPI = 200
TIMEOUT_S = 300

METHOD_STYLE = {
    "dp_search": dict(color="#9467bd", label="Exact dynamic program"),
    "beam_search": dict(color="#1f77b4", label="Beam search"),
}


def main() -> None:
    rows = list(csv.DictReader(DATA_CSV.open()))

    fig, ax = plt.subplots(figsize=FIGSIZE)
    for method, style in METHOD_STYLE.items():
        ok_pts = [
            (int(r["N"]), float(r["elapsed_s"]))
            for r in rows
            if r["method"] == method and r["status"] == "ok"
        ]
        capped_pts = [
            (int(r["N"]), TIMEOUT_S)
            for r in rows
            if r["method"] == method and r["status"] == "exceeded_cap"
        ]
        if ok_pts:
            xs, ys = zip(*sorted(ok_pts))
            ax.plot(xs, ys, marker="o", linestyle="-", **style)
        if capped_pts:
            xs, ys = zip(*sorted(capped_pts))
            ax.scatter(
                xs,
                ys,
                marker="x",
                s=90,
                color=style["color"],
                label=f"{style['label']} (exceeded {TIMEOUT_S:g} s cap)",
                zorder=5,
            )

    ax.set_yscale("log")
    ax.set_xlabel("N (number of hops)", fontsize=14)
    ax.set_ylabel("Wall-clock time (s, log scale)", fontsize=14)
    ax.tick_params(axis="both", labelsize=13)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=12)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for fmt in ("png", "svg"):
        fig.savefig(
            OUT_DIR / f"runtime_vs_n_pumping.{fmt}", dpi=DPI, bbox_inches="tight"
        )
    print(f"Wrote regenerated runtime-vs-N figure to {OUT_DIR}")


if __name__ == "__main__":
    main()

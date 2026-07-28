# Minimum Required Budget vs. N (the scaling-law question)

Per [docs/Roadmap_Derisk_and_Reframe.md](../../docs/Roadmap_Derisk_and_Reframe.md), §2: at each `N`, find the smallest `e_max` at which `beam_search` (unioned with `brute_force_search`'s fixed families, as in every other sweep in this report) finds ANY schedule clearing the fidelity floor `f_min=0.9`, rather than assuming the paper's own `e_max = 10*N` cost formula is sufficient.

**Scoping note (required by §2.2, carried over from §1's result):** [outputs/excluded_move_n14_n18/README.md](../excluded_move_n14_n18/README.md) found that the excluded same-span-purification move (out of scope for `dp_search`/`beam_search`) rescues feasibility at `N=18` at exactly the paper's own budget (`e_max=180`, `F=0.928596`). So any row below reporting `min_feasible_e_max > paper_e_max` describes a limitation of the schedule families `beam_search` can reach, **not** a true lower bound on what any valid schedule needs at that `N`. This is a claim about this codebase's searched families, consistent with the hedge used throughout [docs/Optimality Scope.md](../../docs/Optimality%20Scope.md).

## Results

| N | Paper's $e_{max}=10N$ | Min. feasible $e_{max}$ (this sweep) | Ratio | Best F at min. budget | Best label |
|---|---|---|---|---|---|
| 10 | 100 | 60 | 0.600x | 0.9063 | end_optimistic.n3.YY_ZX |
| 12 | 120 | 73 | 0.608x | 0.9222 | link.n3.YY_ZX |
| 14 | 140 | 84 | 0.600x | 0.9104 | link.n3.YY_ZX |
| 16 | 160 | 128 | 0.800x | 0.9003 | link.n4.YY_ZX_YY |
| 18 | 180 | 162 | 0.900x | 0.9030 | beam.span.(pump[YY](hop0.n3.YY_ZX,hop0.n3.YY_ZX)+(pump[YY](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[YY](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[YY](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+(pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+(pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)+(pump[YY](hop6.n3.YY_ZX,hop6.n3.YY_ZX)+(pump[YY](hop7.n3.YY_ZX,hop7.n3.YY_ZX)+(pump[YY](hop8.n3.YY_ZX,hop8.n3.YY_ZX)+(pump[YY](hop9.n3.YY_ZX,hop9.n3.YY_ZX)+(pump[YY](hop10.n3.YY_ZX,hop10.n3.YY_ZX)+(pump[YY](hop11.n3.YY_ZX,hop11.n3.YY_ZX)+(hop12.n3.ZX_YY+(hop13.n2.YY+((hop14+hop15)+(hop16+hop17)))))))))))))))) |
| 20 | 200 | 187 | 0.935x | 0.9026 | beam.span.(pump[YY](hop0.n3.YY_ZX,hop0.n3.YY_ZX)+(pump[YY](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[YY](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[YY](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+(pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+(pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)+(pump[YY](hop6.n3.YY_ZX,hop6.n3.YY_ZX)+(pump[YY](hop7.n3.YY_ZX,hop7.n3.YY_ZX)+(pump[YY](hop8.n3.YY_ZX,hop8.n3.YY_ZX)+(pump[YY](hop9.n3.YY_ZX,hop9.n3.YY_ZX)+(pump[YY](hop10.n3.YY_ZX,hop10.n3.YY_ZX)+(pump[YY](hop11.n3.YY_ZX,hop11.n3.YY_ZX)+(pump[YY](hop12.n3.YY_ZX,hop12.n3.YY_ZX)+(pump[YY](hop13.n3.YY_ZX,hop13.n3.YY_ZX)+(hop14.n3.ZX_YY+(hop15.n2.YY+((hop16+hop17)+(hop18+hop19)))))))))))))))))) |

**Descriptive power-law fit** (least squares on log-log data, valid points only): $e_{max}^{min} \approx 0.995 \cdot N^{1.742}$. The fitted exponent exceeds 1, i.e. the minimum required budget within this sweep's searched families grows faster than the paper's own linear `10*N` formula.

This fit is descriptive, not a rigorous asymptotic claim -- it is over a small number of points (6) and is sensitive to the specific N values tested.

## Details

- **N=10**: paper's `e_max`=100, min. feasible `e_max`=60, best schedule found there: `end_optimistic.n3.YY_ZX`, F=0.9063, success_prob=0.6196, rate=6195.9511, cost=60. (7 `beam_search` calls, 79.2s.)
- **N=12**: paper's `e_max`=120, min. feasible `e_max`=73, best schedule found there: `link.n3.YY_ZX`, F=0.9222, success_prob=0.5285, rate=4403.9523, cost=72. (7 `beam_search` calls, 159.7s.)
- **N=14**: paper's `e_max`=140, min. feasible `e_max`=84, best schedule found there: `link.n3.YY_ZX`, F=0.9104, success_prob=0.4752, rate=3394.1664, cost=84. (7 `beam_search` calls, 290.1s.)
- **N=16**: paper's `e_max`=160, min. feasible `e_max`=128, best schedule found there: `link.n4.YY_ZX_YY`, F=0.9003, success_prob=0.3095, rate=1934.3196, cost=128. (8 `beam_search` calls, 571.4s.)
- **N=18**: paper's `e_max`=180, min. feasible `e_max`=162, best schedule found there: `beam.span.(pump[YY](hop0.n3.YY_ZX,hop0.n3.YY_ZX)+(pump[YY](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[YY](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[YY](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+(pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+(pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)+(pump[YY](hop6.n3.YY_ZX,hop6.n3.YY_ZX)+(pump[YY](hop7.n3.YY_ZX,hop7.n3.YY_ZX)+(pump[YY](hop8.n3.YY_ZX,hop8.n3.YY_ZX)+(pump[YY](hop9.n3.YY_ZX,hop9.n3.YY_ZX)+(pump[YY](hop10.n3.YY_ZX,hop10.n3.YY_ZX)+(pump[YY](hop11.n3.YY_ZX,hop11.n3.YY_ZX)+(hop12.n3.ZX_YY+(hop13.n2.YY+((hop14+hop15)+(hop16+hop17))))))))))))))))`, F=0.9030, success_prob=0.2186, rate=1214.4122, cost=162. (8 `beam_search` calls, 915.7s.)
- **N=20**: paper's `e_max`=200, min. feasible `e_max`=187, best schedule found there: `beam.span.(pump[YY](hop0.n3.YY_ZX,hop0.n3.YY_ZX)+(pump[YY](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[YY](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[YY](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+(pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+(pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)+(pump[YY](hop6.n3.YY_ZX,hop6.n3.YY_ZX)+(pump[YY](hop7.n3.YY_ZX,hop7.n3.YY_ZX)+(pump[YY](hop8.n3.YY_ZX,hop8.n3.YY_ZX)+(pump[YY](hop9.n3.YY_ZX,hop9.n3.YY_ZX)+(pump[YY](hop10.n3.YY_ZX,hop10.n3.YY_ZX)+(pump[YY](hop11.n3.YY_ZX,hop11.n3.YY_ZX)+(pump[YY](hop12.n3.YY_ZX,hop12.n3.YY_ZX)+(pump[YY](hop13.n3.YY_ZX,hop13.n3.YY_ZX)+(hop14.n3.ZX_YY+(hop15.n2.YY+((hop16+hop17)+(hop18+hop19))))))))))))))))))`, F=0.9026, success_prob=0.1719, rate=859.6317, cost=186. (8 `beam_search` calls, 1230.7s.)

## Method caveats

- Bisection assumes feasibility is monotonically non-decreasing in `e_max`. This holds for the exact DP frontier by construction, but `beam_search`'s beam-pruning is a heuristic on top of that -- no non-monotonicity was observed in this run's cached probe history (see `results.csv` for the final endpoints), but this was not exhaustively verified at every intermediate probe.
- The minimum feasible `e_max` is pinned down to within `+/- 2`, not exactly, consistent with `e_max` being discretized by Gen-node counts anyway.

## Reproducing

```bash
cd /home/shark/Documents/hrgs-purification-scheduler
source .venv/bin/activate
PYTHONPATH=src python3 -u experiments/sweep_min_budget_vs_n.py
```

Total wall-clock time: ~3247s.

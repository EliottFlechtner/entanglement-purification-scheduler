# Alternative Objective Presets

Roadmap item 9 ([docs/archive/Roadmap Remaining Work.md](../../docs/archive/Roadmap%20Remaining%20Work.md)): exercises `ObjectiveConfig.maximize_fidelity_with_rate_floor` and `ObjectiveConfig.minimize_cost_with_constraints` for the first time against real data, at the paper's own headline config (N=10, e_d=0.01), demonstrating the "objective substitution" framing ([docs/Justification of Implementation.md, §6.3](../../docs/Justification%20of%20Implementation.md)).

Reference rates (from the standard preset): paper baseline rate = 4055.92, optimizer matched-cost rate = 4158.14. `e_max=200` throughout (generous, above the ~50-100 cost range seen elsewhere so it never binds unless the objective itself wants a low cost).

## Results

| Preset | Formula | Feasible | Cost | Fidelity | Success prob | Rate |
|---|---|---|---|---|---|---|
| `maximize_rate_with_fidelity_floor` | maximize R s.t. F >= 0.9 | yes | 60 | 0.9063 | 0.6196 | 6195.95 |
| `maximize_fidelity_with_rate_floor(paper_rate)` | maximize F s.t. R >= 4055.92 (paper baseline's own rate) | yes | 80 | 0.9351 | 0.4805 | 4804.58 |
| `maximize_fidelity_with_rate_floor(matched_rate)` | maximize F s.t. R >= 4158.14 (optimizer matched-cost rate) | yes | 80 | 0.9351 | 0.4805 | 4804.58 |
| `minimize_cost_with_constraints(f_min_only)` | minimize C s.t. F >= 0.9 | yes | 60 | 0.9063 | 0.6196 | 1239.19 |
| `minimize_cost_with_constraints(f_min_and_r_min)` | minimize C s.t. F >= 0.9 and R >= 4055.92 | yes | 60 | 0.9063 | 0.6196 | 6195.95 |

## Cross-check against the bisected minimum budget

`minimize_cost_with_constraints(f_min=0.9)` finds cost=60 directly via the objective's own scoring (no external bisection loop) -- compare against `outputs/sweep_min_budget_vs_ed/`'s independently bisected minimum budget at e_d=0.01, N=10.

## Takeaways

- Swapping the objective's *primary* metric from rate to fidelity (while holding a rate floor instead of a fidelity floor) is a one-line change (`ObjectiveConfig.maximize_fidelity_with_rate_floor(r_min=...)`) and yields a genuinely different top schedule: fidelity 0.9351 at cost 80 when only required to match the paper's own rate, versus fidelity 0.9351 at cost 80 under the stricter matched-cost rate floor.
- Swapping the primary metric to cost (`minimize_cost_with_constraints`) directly answers a "cheapest hardware that still works" question the rate- maximizing preset cannot answer on its own: cost=60 suffices to clear F>=0.9 alone, while meeting both F>=0.9 and R>=4055.92 simultaneously needs 60.
- None of this required touching the search algorithms themselves -- `beam_search` and `dp_search` are already objective-agnostic (they only ever call `objective.score(...)` and `objective.is_feasible(...)`); every result above came from swapping the `ObjectiveConfig` argument alone.

- **Gotcha, worth flagging explicitly**: the `f_min`-only cost-minimizing preset returns a cost=60 schedule with rate=1239.19 -- *below* the paper's own rate (4055.92) -- even though a *different* cost=60 schedule satisfying both F>=0.9 and R>=4055.92 exists (found by the `f_min_and_r_min` preset above). `minimize_cost_with_constraints` has no secondary preference over rate once the cost floor is met, so among tied-cost feasible candidates it returns whichever one happens first in `beam_search`'s internal ordering -- not necessarily the best one by any other metric. Anyone using this preset who also cares about rate should add an explicit `r_min`, as the last preset does.

Full data: [`results.csv`](results.csv).

## Reproducing

```bash
cd /home/shark/Documents/entanglement-purification-scheduler
source .venv/bin/activate
python3 experiments/alternative_objectives.py
```

Total wall-clock time: ~134s (5 `beam_search` calls).

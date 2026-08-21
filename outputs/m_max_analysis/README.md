# M_max Analysis: Concurrent Open Branches vs. N, and a Bisection at N=10

Explores `M_max` (max concurrent open branches, `ResourceBudget.m_max`, [Validated Formal Model Def, §5]), now enforced via `ScheduleDAG.max_concurrent_branches()` (Sethi-Ullman register allocation, on the `feature/enforce-m-max` branch) and wired into `ObjectiveConfig.m_max`. This was previously an unenforced model-only field ([Repository State & Progress.md](../../docs/Repository%20State%20&%20Progress.md) §5).

## Part 1: M(Σ) vs. N

M(Σ) computed for the three canonical structural builders (`raw_chain`, `baseline_end_node_pumping(n_pur=5)`, and `flexible_paper_schedule` at N=10 only, since it is only defined there) plus the optimizer's own best schedule at each N (matched cost / budget-relaxed, `beam_search` at `e_max=10*N`, matching [sweep_hop_count.py](../../experiments/sweep_hop_count.py)'s own methodology).

| N | Family | M(Σ) | Resource cost |
|---|---|---|---|
| 2 | `raw` | 3 | 4 |
| 2 | `baseline_end_node_pumping` | 4 | 20 |
| 2 | `optimizer_budget_relaxed` | 3 | 4 |
| 2 | `optimizer_matched_cost` | 4 | 20 |
| 4 | `raw` | 3 | 8 |
| 4 | `baseline_end_node_pumping` | 4 | 40 |
| 4 | `optimizer_budget_relaxed` | 4 | 8 |
| 4 | `optimizer_matched_cost` | 4 | 40 |
| 6 | `raw` | 3 | 12 |
| 6 | `baseline_end_node_pumping` | 4 | 60 |
| 6 | `optimizer_budget_relaxed` | 4 | 18 |
| 6 | `optimizer_matched_cost` | 4 | 60 |
| 8 | `raw` | 3 | 16 |
| 8 | `baseline_end_node_pumping` | 4 | 80 |
| 8 | `optimizer_budget_relaxed` | 4 | 32 |
| 8 | `optimizer_matched_cost` | 4 | 80 |
| 10 | `raw` | 3 | 20 |
| 10 | `baseline_end_node_pumping` | 4 | 100 |
| 10 | `paper_baseline` | 5 | 100 |
| 10 | `optimizer_budget_relaxed` | 4 | 60 |
| 10 | `optimizer_matched_cost` | 4 | 100 |
| 14 | `raw` | 3 | 28 |
| 14 | `baseline_end_node_pumping` | 4 | 140 |
| 14 | `optimizer_budget_relaxed` | 4 | 84 |
| 14 | `optimizer_matched_cost` | 4 | 140 |
| 18 | `raw` | 3 | 36 |
| 18 | `baseline_end_node_pumping` | 4 | 180 |
| 18 | `optimizer_budget_relaxed` | 5 | 162 |
| 18 | `optimizer_matched_cost` | 4 | 180 |

**Observation:** `raw` stays at M∈[3] and `baseline_end_node_pumping` at M∈[4] across the entire N∈[2, 4, 6, 8, 10, 14, 18] range -- both bounded by the depth of their fixed pumping/join structure, never by N itself (matches [tests/test_dag.py](../../tests/test_dag.py)'s `raw_chain(N=1..20)` regression, which already showed this bound directly). The optimizer's own budget-relaxed best schedule ranges over M∈[3, 4, 5] across the sweep -- it is not fixed to one structural family, so its M varies with which span-partition the search actually selects at each N, but it stays in the same small single-digit range as the fixed baselines rather than growing with N. **No family examined here shows M(Σ) scaling with N** -- the register-allocation bound is governed by DAG *depth/branching shape*, not by hop count.

Full data: [`m_vs_n.csv`](m_vs_n.csv). Figure: [`m_vs_n.png`](m_vs_n.png).

## Part 2: m_max bisection at N=10, e_d=0.01, e_max=100 (paper's own budget)

Starting from the unconstrained optimum's own M and stepping `m_max` down by 1 until infeasible, at the paper's own headline configuration ([outputs/headline_experiment_n10](../headline_experiment_n10)):

| m_max | Feasible | Best schedule | Rate | Fidelity | Actual M |
|---|---|---|---|---|---|
| unconstrained | yes | `end_optimistic.n3.YY_ZX` | 6195.95 | 0.9063 | 4 |
| 4 | yes | `end_optimistic.n3.YY_ZX` | 6195.95 | 0.9063 | 4 |
| 3 | no | `beam.span.(hop0.n2.ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+pump[ZX]((pump[YY](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[YY](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+(hop4.n3.ZX_YY+(hop5.n2.YY+((hop6+hop7)+(hop8+hop9)))))),(pump[YY](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[YY](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+(hop4.n3.ZX_YY+(hop5.n2.YY+((hop6+hop7)+(hop8+hop9)))))))))` | 3967.69 | 0.9290 | 6 |

**Observation:** the unconstrained rate-optimal schedule at N=10 needs M=4 concurrent open branches. Every `m_max` down to 4 still finds a feasible schedule at the *same* rate/fidelity (the same `end_optimistic.n3.YY_ZX` candidate already has M=4 <= 4, so it remains selectable). At `m_max=3`, no candidate in the beam-searched frontier clears both the rate/fidelity objective and the branch budget: the best schedule the search can still offer (`beam.span.(hop0.n2.ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+pump[ZX]((pump[YY](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[YY](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+(hop4.n3.ZX_YY+(hop5.n2.YY+((hop6+hop7)+(hop8+hop9)))))),(pump[YY](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[YY](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+(hop4.n3.ZX_YY+(hop5.n2.YY+((hop6+hop7)+(hop8+hop9)))))))))`) needs M=6 > 3, so it is reported infeasible (score = -inf) despite its fidelity (0.9290) still clearing the f_min floor. This shows `M_max` **can** become the actual binding constraint (distinct from `E_max`/`f_min`) once tightened below the unconstrained optimum's own M -- but at the paper's own parameterization, it is not a binding concern until tightened noticeably past that point.

Full data: [`m_max_bisection_n10.csv`](m_max_bisection_n10.csv).

## Reproducing

```bash
cd /home/shark/Documents/entanglement-purification-scheduler
source .venv/bin/activate
python3 experiments/m_max_analysis.py
```

Total wall-clock time: ~248s.

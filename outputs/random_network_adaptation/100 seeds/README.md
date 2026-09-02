# Random Heterogeneous Network Adaptation

Does the optimizer's own schedule adapt to a non-uniform, per-hop heterogeneous network configuration -- without any in-flight, closed-loop (RL-style) adaptation mechanism? The schedule is still fixed in advance for the whole configuration [Validated Formal Model Def §8]; what varies here is only *which* fixed schedule the search picks for a given, already-known, non-uniform config, compared to a fixed uniform "same recipe at every hop" convention. `hrgs_scheduler.models.random_network.random_network_config` draws each hop's length, inner-qubit error rates, and arm count independently at random, producing genuinely heterogeneous `NetworkConfig` instances -- every convenience constructor used elsewhere in this repo (`NetworkConfig.uniform`, `integrating_paper_config`) gives every hop identical parameters.

## Part 1: a single designed "weak link" contrast

N=5 hops, all near-ideal (`p_x_inner=p_z_inner=0.001`) except hop 2, deliberately set to `p_x_inner=p_z_inner=0.015` -- a 11.9x higher end-to-end inner-qubit error rate than every other hop (`HopConfig.inner_error_per_hop`, [Bridging eq. (10)]). Same `e_d=0.01`, `arm_count=18`, `length=2.0` km at every hop, so only the inner-qubit noise varies -- isolating the effect this section is about.

| Per-hop inner-qubit error | hop 0 | hop 1 | hop 2 | hop 3 | hop 4 |
|---|---|---|---|---|---|
| value | 0.0177 | 0.0177 | 0.2110 | 0.0177 | 0.0177 |

| Schedule | Label | Cost | Fidelity | Meets f_min=0.9? | Rate |
|---|---|---|---|---|---|
| Optimizer's own (adaptive) | `beam.span.(pump[ZX](hop0.n2.YY,hop0.n2.YY)+(pump[ZX](hop1.n2` | 38 | 0.9007 | Yes | 1798.57 |
| Best uniform link-level recipe | `link.n4.XZ_YY_XZ` | 40 | 0.8821 | **No** | 1738.32 |

**Headline finding:** at this budget, *every* uniform link-level candidate (the same purification circuit sequence applied identically at every hop -- the "reasonable default a practitioner would pick" without doing any per-hop optimization) fails to clear the f_min=0.9 floor at all; the best one only reaches F=0.8821. The optimizer's own schedule, free to shape itself differently per hop, clears the floor at F=0.9007 -- and at a **lower** resource cost (38 vs. 40 Gen nodes) and a higher rate (1798.57 vs. 1738.32). A uniform, non-adaptive convention is not just suboptimal here -- it is *infeasible* at any cost this search considered, while a per-hop-aware schedule both restores feasibility and costs less.

### Per-hop resource allocation

| Hop | Inner-qubit error | Optimizer's Gen count | Uniform recipe's Gen count |
|---|---|---|---|
| 0 | 0.0177 | 8 | 8 |
| 1 | 0.0177 | 8 | 8 |
| 2 **<- weak hop** | 0.2110 | 8 | 8 |
| 3 | 0.0177 | 6 | 8 |
| 4 | 0.0177 | 8 | 8 |

The uniform recipe spends the *same* Gen-node count at every hop by construction (it is defined as "the same circuit sequence applied identically at every hop"); the optimizer's own schedule is free to -- and does -- spend unevenly, without being told to. This is the sense in which the schedule the search picks "adapts" to the given, fixed network config: not by reacting to intermediate measurement outcomes in flight, but by shaping the fixed schedule differently depending on which network it is handed.

Full per-hop data: [`weak_link_gen_allocation.csv`](weak_link_gen_allocation.csv). Figure: [`weak_link_allocation.png`](weak_link_allocation.png).

## Part 2: randomized sweep for statistical power

100 independently random heterogeneous N=6 networks (`random_network_config(N=6, seed=0..99)`, default `RandomNetworkSpec` bounds, `e_d=0.01`, `e_max=60` matching the paper's own budget convention). For each network, `beam_search` (default settings, `beam_width=25`) is run once with `maximize_rate_with_fidelity_floor(f_min=0.9)`; the best feasible candidate overall ("optimizer") is compared against the best *feasible* uniform link-level candidate ("uniform baseline") at the same network and budget.

- Of 100 random networks with at least one feasible schedule, 0 had **no** uniform link-level candidate clear the fidelity floor at all (a feasibility rescue like Part 1's, excluded from the rate-improvement statistics below since there is no uniform rate to compare against).
- Among the remaining 100 networks where both sides are feasible: mean rate improvement of the optimizer over the uniform baseline = +20.37%, median = +23.01%, range = [+0.00%, +47.81%], and 80/100 networks show a strictly positive improvement (the remainder are ties, where the search's own uniform link-level family already happened to be its best candidate).
- Pearson correlation between per-hop noise heterogeneity (coefficient of variation of `inner_error_per_hop` across hops) and rate improvement: 0.020 across this sample -- weak/inconclusive at this sample size; the magnitude of benefit does not appear to scale cleanly with this particular heterogeneity metric, though the *sign* of the benefit (optimizer >= uniform baseline, never worse) holds throughout.

Full per-seed data: [`random_sweep_results.csv`](random_sweep_results.csv). Figure: [`random_sweep_improvement_vs_heterogeneity.png`](random_sweep_improvement_vs_heterogeneity.png).

## Caveats

- `beam_search` is beam-limited (`beam_width=25`), not a certified exact Pareto frontier -- both the "optimizer" and "uniform baseline" numbers here are what this specific beam width finds, matching every other beam-search-based script in this report.
- "Uniform link-level baseline" means `link_level_pumped_chain`: the same purification circuit sequence applied identically at every hop. It is not the only conceivable non-adaptive convention (the paper's own hand-picked `flexible_paper` schedule is another, but it is only defined at N=10 and does not generalize to arbitrary random N here).
- Part 2's heterogeneity metric (coefficient of variation of `inner_error_per_hop`) is one reasonable summary of "how non-uniform is this network", not the only one; length and arm-count heterogeneity are not separately isolated here.

## Reproducing

```bash
cd /home/shark/Documents/entanglement-purification-scheduler
source .venv/bin/activate
python3 experiments/random_network_adaptation.py
```

Total wall-clock time: ~262s.

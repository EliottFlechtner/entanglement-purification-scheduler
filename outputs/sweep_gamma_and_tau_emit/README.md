# Sweep: gamma (memory decoherence) and tau_emit (generation timing) sensitivity

Quantifies how much the two previously-inert `NetworkConfig` fields `gamma` and `tau_emit` move F/R now that they are wired into `Evaluator` (see `schedule/evaluator.py::_sync_to_common_time` for gamma, `_eval_gen` for tau_emit, and `outputs/sweep_network_sensitivity/README.md` for the original "dead field" finding this supersedes).

Network shape: N=10, l=2 km/hop, branching=(16,14,1), arm_count=18, e_d=0.01, c=2e5 -- the paper's own config, only gamma/tau_emit varied one at a time (the other held at its inert default: gamma=0.0 / tau_emit=None).

## Key findings

- **gamma "how bad it gets"**: `baseline_end_node_pumping`'s fidelity collapses from 0.9168 (gamma=0, matches historical) to 0.2500 (maximally mixed) as gamma sweeps 0 -> 1e5, entirely from the sacrificial copies' in-memory wait during heralded round-trips. `raw_chain`/`flexible_paper_schedule` are bit-for-bit flat across the whole sweep -- confirming gamma only fires where the schedule actually has an asymmetric-timing combine.
- **`beam_search` never picks the gamma-sensitive schedule here**: at every gamma value tested, `optimizer_matched_cost`/`optimizer_budget_relaxed` both land on `end_optimistic.*` candidates (no intermediate Heralds -- the same optimistic/no-wait family as `flexible_paper`), never on a heralded-pumping candidate. So the optimizer's own headline numbers are unaffected by gamma in this configuration -- not because gamma doesn't matter, but because the search was already avoiding the schedule shape gamma penalizes (optimistic pumping strictly dominates heralded pumping here even before gamma is considered). This is a reassuring result, not a null one.
- **tau_emit hits the lowest-baseline-latency schedule hardest, in relative terms**: rate for all three canonical schedules falls monotonically as tau_emit grows, but `flexible_optimistic` (1x L/c baseline latency) and `baseline_heralded_pumping` (9x L/c) cross over around tau_emit=0.01 -- above that point the heralded schedule's *larger* fixed latency actually makes it *less* sensitive to the added generation delay, matching `timing.py`'s documented canonical-timing insight.

## Part 1: gamma sweep

Three fixed canonical schedules, re-evaluated at each gamma (no search): `raw_chain` (no purification, no waits), `flexible_paper_schedule` (optimistic pumping, no intermediate Heralds between Purify rounds -> no asymmetric waits anywhere), and `baseline_end_node_pumping` (heralded pumping, n_pur=5 -> sacrificial copies wait for the primary branch's accumulated round-trip Herald confirmations before being purified).

| gamma | Schedule | Fidelity | Rate |
|---|---|---|---|
| 0 | raw | 0.8234 | 10000.00 |
| 0 | flexible_optimistic | 0.9295 | 4055.92 |
| 0 | baseline_heralded_pumping | 0.9168 | 462.02 |
| 1 | raw | 0.8234 | 10000.00 |
| 1 | flexible_optimistic | 0.9295 | 4055.92 |
| 1 | baseline_heralded_pumping | 0.9166 | 461.73 |
| 10 | raw | 0.8234 | 10000.00 |
| 10 | flexible_optimistic | 0.9295 | 4055.92 |
| 10 | baseline_heralded_pumping | 0.9148 | 459.18 |
| 100 | raw | 0.8234 | 10000.00 |
| 100 | flexible_optimistic | 0.9295 | 4055.92 |
| 100 | baseline_heralded_pumping | 0.8969 | 434.86 |
| 1000 | raw | 0.8234 | 10000.00 |
| 1000 | flexible_optimistic | 0.9295 | 4055.92 |
| 1000 | baseline_heralded_pumping | 0.7100 | 278.46 |
| 10000 | raw | 0.8234 | 10000.00 |
| 10000 | flexible_optimistic | 0.9295 | 4055.92 |
| 10000 | baseline_heralded_pumping | 0.2540 | 118.71 |
| 100000 | raw | 0.8234 | 10000.00 |
| 100000 | flexible_optimistic | 0.9295 | 4055.92 |
| 100000 | baseline_heralded_pumping | 0.2500 | 110.04 |

**Only `baseline_heralded_pumping` is gamma-sensitive** -- `raw`/`flexible_optimistic` are exactly flat across the whole sweep (as expected: neither ever combines two branches with different `current_time`). This confirms the fix is scoped correctly: gamma only matters where a real asynchronous wait exists in the schedule.

### Optimizer sensitivity (`beam_search`, same framing as `sweep_ed.py`)

| gamma | Variant | Label | Cost | Fidelity | Rate | Meets floor? |
|---|---|---|---|---|---|---|
| 0 | paper_baseline | flexible_paper | 100 | 0.9295 | 4055.92 | yes |
| 0 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 4158.14 | yes |
| 0 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 6195.95 | yes |
| 1 | paper_baseline | flexible_paper | 100 | 0.9295 | 4055.92 | yes |
| 1 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 4158.14 | yes |
| 1 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 6195.95 | yes |
| 10 | paper_baseline | flexible_paper | 100 | 0.9295 | 4055.92 | yes |
| 10 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 4158.14 | yes |
| 10 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 6195.95 | yes |
| 100 | paper_baseline | flexible_paper | 100 | 0.9295 | 4055.92 | yes |
| 100 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 4158.14 | yes |
| 100 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 6195.95 | yes |
| 1000 | paper_baseline | flexible_paper | 100 | 0.9295 | 4055.92 | yes |
| 1000 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 4158.14 | yes |
| 1000 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 6195.95 | yes |
| 10000 | paper_baseline | flexible_paper | 100 | 0.9295 | 4055.92 | yes |
| 10000 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 4158.14 | yes |
| 10000 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 6195.95 | yes |
| 100000 | paper_baseline | flexible_paper | 100 | 0.9295 | 4055.92 | yes |
| 100000 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 4158.14 | yes |
| 100000 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 6195.95 | yes |

Full per-point data: [`gamma_canonical.csv`](gamma_canonical.csv), [`gamma_optimizer.csv`](gamma_optimizer.csv).

Figures: [`gamma_fidelity.png`](gamma_fidelity.png) (canonical schedules), [`gamma_optimizer_rate.png`](gamma_optimizer_rate.png) (`beam_search` variants).

## Part 2: tau_emit sweep

Same three canonical schedules and `beam_search` framing, varying `tau_emit` instead (with `gamma=0.0`). `tau_emit` adds a uniform generation-latency offset tau_half = tau_emit * (log2(16) + log2(14)) = tau_emit * 7.807 to every Gen node (branching is uniform across hops here), so every schedule's absolute latency grows by the same amount -- the *relative* rate hit is largest for the schedule with the smallest baseline latency (`flexible_optimistic`, 1x L/c) and smallest for the largest baseline latency (`baseline_heralded_pumping`, 9x L/c at n_pur=5), matching `timing.py`'s documented canonical-timing insight.

| tau_emit | Schedule | Rate | Latency |
|---|---|---|---|
| 0 | raw | 10000.00 | 0.0001 |
| 0 | flexible_optimistic | 4055.92 | 0.0001 |
| 0 | baseline_heralded_pumping | 462.02 | 0.0009 |
| 1e-07 | raw | 9922.53 | 0.000100781 |
| 1e-07 | flexible_optimistic | 4024.50 | 0.000100781 |
| 1e-07 | baseline_heralded_pumping | 461.62 | 0.000900781 |
| 1e-06 | raw | 9275.80 | 0.000107807 |
| 1e-06 | flexible_optimistic | 3762.20 | 0.000107807 |
| 1e-06 | baseline_heralded_pumping | 458.04 | 0.000907807 |
| 1e-05 | raw | 5615.66 | 0.000178074 |
| 1e-05 | flexible_optimistic | 2277.67 | 0.000178074 |
| 1e-05 | baseline_heralded_pumping | 425.14 | 0.000978074 |
| 0.0001 | raw | 1135.41 | 0.000880735 |
| 0.0001 | flexible_optimistic | 460.52 | 0.000880735 |
| 0.0001 | baseline_heralded_pumping | 247.40 | 0.00168074 |
| 0.001 | raw | 126.46 | 0.00790735 |
| 0.001 | flexible_optimistic | 51.29 | 0.00790735 |
| 0.001 | baseline_heralded_pumping | 47.75 | 0.00870735 |
| 0.01 | raw | 12.79 | 0.0781735 |
| 0.01 | flexible_optimistic | 5.19 | 0.0781735 |
| 0.01 | baseline_heralded_pumping | 5.27 | 0.0789735 |

### Optimizer sensitivity (`beam_search`)

| tau_emit | Variant | Label | Cost | Fidelity | Rate | Meets floor? |
|---|---|---|---|---|---|---|
| 0 | paper_baseline | flexible_paper | 100 | 0.9295 | 4055.92 | yes |
| 0 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 4158.14 | yes |
| 0 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 6195.95 | yes |
| 1e-07 | paper_baseline | flexible_paper | 100 | 0.9295 | 4024.50 | yes |
| 1e-07 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 4125.93 | yes |
| 1e-07 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 6147.95 | yes |
| 1e-06 | paper_baseline | flexible_paper | 100 | 0.9295 | 3762.20 | yes |
| 1e-06 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 3857.01 | yes |
| 1e-06 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 5747.24 | yes |
| 1e-05 | paper_baseline | flexible_paper | 100 | 0.9295 | 2277.67 | yes |
| 1e-05 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 2335.07 | yes |
| 1e-05 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 3479.43 | yes |
| 0.0001 | paper_baseline | flexible_paper | 100 | 0.9295 | 460.52 | yes |
| 0.0001 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 472.12 | yes |
| 0.0001 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 703.50 | yes |
| 0.001 | paper_baseline | flexible_paper | 100 | 0.9295 | 51.29 | yes |
| 0.001 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 52.59 | yes |
| 0.001 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 78.36 | yes |
| 0.01 | paper_baseline | flexible_paper | 100 | 0.9295 | 5.19 | yes |
| 0.01 | optimizer_matched_cost | end_optimistic.n5.XZ_XZ_XZ_XZ | 100 | 0.9168 | 5.32 | yes |
| 0.01 | optimizer_budget_relaxed | end_optimistic.n3.YY_ZX | 60 | 0.9063 | 7.93 | yes |

Full per-point data: [`tau_emit_canonical.csv`](tau_emit_canonical.csv), [`tau_emit_optimizer.csv`](tau_emit_optimizer.csv).

Figures: [`tau_emit_rate.png`](tau_emit_rate.png) (canonical schedules, log-log), [`tau_emit_optimizer_rate.png`](tau_emit_optimizer_rate.png) (`beam_search` variants).

## Reproducing

```bash
cd /home/shark/Documents/entanglement-purification-scheduler
source .venv/bin/activate
python3 experiments/sweep_gamma_and_tau_emit.py
```

Total wall-clock time: ~201s (14 `beam_search` calls total, plus cheap direct evaluator calls for the canonical schedules).

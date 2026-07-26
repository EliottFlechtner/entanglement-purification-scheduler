# Pareto Frontiers: Fidelity vs. Cost, Fidelity vs. Rate

Roadmap item 8 ([docs/archive/Roadmap Remaining Work.md](../../docs/archive/Roadmap%20Remaining%20Work.md)): exposes the optimizer's full cost-quality tradeoff curve directly, instead of only ever reporting the three cherry-picked points (paper baseline / matched-cost / budget-relaxed) used elsewhere in this repo (`outputs/headline_experiment_n10/`, `outputs/sweep_ed_n10/`).

Method: `beam_search(net, obj, e_max, beam_width=25)` with a permissive objective (`f_min=0.0`) returns every evaluated candidate, sorted best-first; every candidate's `(resource_cost, fidelity, rate)` is extracted and the non-dominated subset computed under two objective pairs: (minimize cost, maximize fidelity) and (maximize rate, maximize fidelity). Caveat: `beam_search`'s own frontier is beam-limited (`beam_width=25`), so this is an *inner bound* on the true Pareto frontier, not a certified-exact one, at N=10 -- the same documented scope limit as every other N=10 result in this repo.

## `n10_ed0p01`

Paper's own N=10 config at the headline noise point e_d=0.01. `e_max=150`.

180 candidates evaluated; 43 on the F-vs-C frontier, 52 on the F-vs-R frontier.

Paper baseline: cost=100, F=0.9295, R=4055.92. On F-vs-C frontier: no. On F-vs-R frontier: no.

F-vs-C frontier (sorted by cost):

| Cost | Fidelity | Label |
|---|---|---|
| 20 | 0.8234 | `beam.span.(((hop0+hop1)+(hop2+hop3))+((hop4+hop5)+((hop6+hop7)+(hop8+hop9))))` |
| 20 | 0.8234 | `beam.span.(((hop0+hop1)+(hop2+hop3))+(((hop4+hop5)+(hop6+hop7))+(hop8+hop9)))` |
| 20 | 0.8234 | `beam.span.(((hop0+hop1)+((hop2+hop3)+(hop4+hop5)))+((hop6+hop7)+(hop8+hop9)))` |
| 20 | 0.8234 | `beam.span.((((hop0+hop1)+(hop2+hop3))+(hop4+hop5))+((hop6+hop7)+(hop8+hop9)))` |
| 22 | 0.8284 | `beam.span.((hop0.n2.YY+(hop1+hop2))+(hop3+((hop4+hop5)+((hop6+hop7)+(hop8+hop9)))))` |
| 22 | 0.8284 | `beam.span.((hop0.n2.YY+(hop1+hop2))+(hop3+(((hop4+hop5)+(hop6+hop7))+(hop8+hop9))))` |
| 22 | 0.8284 | `beam.span.((hop0.n2.YY+(hop1+hop2))+(((hop3+hop4)+((hop5+hop6)+(hop7+hop8)))+hop9))` |
| 22 | 0.8284 | `beam.span.((hop0.n2.YY+(hop1+hop2))+((((hop3+hop4)+(hop5+hop6))+(hop7+hop8))+hop9))` |
| 22 | 0.8284 | `beam.span.((hop0.n2.ZX+(hop1+hop2))+(hop3+((hop4+hop5)+((hop6+hop7)+(hop8+hop9)))))` |
| 22 | 0.8284 | `beam.span.((hop0.n2.ZX+(hop1+hop2))+(hop3+(((hop4+hop5)+(hop6+hop7))+(hop8+hop9))))` |
| 22 | 0.8284 | `beam.span.((hop0.n2.ZX+(hop1+hop2))+(((hop3+hop4)+((hop5+hop6)+(hop7+hop8)))+hop9))` |
| 22 | 0.8284 | `beam.span.((hop0.n2.ZX+(hop1+hop2))+((((hop3+hop4)+(hop5+hop6))+(hop7+hop8))+hop9))` |
| 22 | 0.8284 | `beam.span.((hop0.n2.XZ+(hop1+hop2))+(hop3+((hop4+hop5)+((hop6+hop7)+(hop8+hop9)))))` |
| 40 | 0.8800 | `link.n2.YY` |
| 40 | 0.8800 | `link.n2.ZX` |
| 40 | 0.8800 | `link.n2.XZ` |
| 60 | 0.9343 | `link.n3.YY_ZX` |
| 60 | 0.9343 | `link.n3.YY_XZ` |
| 60 | 0.9343 | `link.n3.ZX_YY` |
| 60 | 0.9343 | `link.n3.ZX_ZX` |
| 60 | 0.9343 | `link.n3.XZ_YY` |
| 60 | 0.9343 | `link.n3.XZ_XZ` |
| 80 | 0.9351 | `link.n4.YY_ZX_YY` |
| 80 | 0.9351 | `link.n4.YY_ZX_ZX` |
| 80 | 0.9351 | `link.n4.YY_XZ_YY` |
| 80 | 0.9351 | `link.n4.YY_XZ_XZ` |
| 80 | 0.9351 | `link.n4.ZX_YY_ZX` |
| 80 | 0.9351 | `link.n4.ZX_YY_XZ` |
| 80 | 0.9351 | `link.n4.ZX_ZX_YY` |
| 80 | 0.9351 | `link.n4.ZX_ZX_ZX` |
| 80 | 0.9351 | `link.n4.XZ_YY_ZX` |
| 80 | 0.9351 | `link.n4.XZ_YY_XZ` |
| 80 | 0.9351 | `link.n4.XZ_XZ_YY` |
| 80 | 0.9351 | `link.n4.XZ_XZ_XZ` |
| 100 | 0.9355 | `link.n5.ZX_ZX_ZX_ZX` |
| 100 | 0.9355 | `link.n5.YY_ZX_YY_XZ` |
| 100 | 0.9355 | `link.n5.XZ_XZ_XZ_XZ` |
| 120 | 0.9355 | `link.n6.ZX_ZX_ZX_ZX_ZX` |
| 120 | 0.9355 | `link.n6.XZ_XZ_XZ_XZ_XZ` |
| 120 | 0.9355 | `link.n6.YY_ZX_YY_XZ_YY` |
| 140 | 0.9355 | `link.n7.ZX_ZX_ZX_ZX_ZX_ZX` |
| 140 | 0.9355 | `link.n7.YY_ZX_YY_XZ_YY_ZX` |
| 140 | 0.9355 | `link.n7.XZ_XZ_XZ_XZ_XZ_XZ` |

Full data: [`points_n10_ed0p01.csv`](points_n10_ed0p01.csv).

Figures: [`fidelity_vs_cost_n10_ed0p01.png`](fidelity_vs_cost_n10_ed0p01.png), [`fidelity_vs_rate_n10_ed0p01.png`](fidelity_vs_rate_n10_ed0p01.png).

## `n6_ed0p01`

Same physics, shorter chain N=6, e_d=0.01. `e_max=90`.

180 candidates evaluated; 55 on the F-vs-C frontier, 64 on the F-vs-R frontier.

Paper baseline: cost=60, F=0.9590, R=9608.16. On F-vs-C frontier: no. On F-vs-R frontier: no.

F-vs-C frontier (sorted by cost):

| Cost | Fidelity | Label |
|---|---|---|
| 12 | 0.8884 | `beam.span.((hop0+hop1)+((hop2+hop3)+(hop4+hop5)))` |
| 12 | 0.8884 | `beam.span.(((hop0+hop1)+(hop2+hop3))+(hop4+hop5))` |
| 14 | 0.8940 | `beam.span.((hop0+hop1.n2.YY)+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((hop0+hop1.n2.ZX)+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((hop0+hop1.n2.XZ)+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((hop0+pump[YY](hop1,hop1))+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((hop0+pump[ZX](hop1,hop1))+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((hop0+pump[XZ](hop1,hop1))+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((hop0.n2.YY+hop1)+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((hop0.n2.ZX+hop1)+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((hop0.n2.XZ+hop1)+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((pump[YY](hop0,hop0)+hop1)+((hop2+hop3)+(hop4+hop5)))` |
| 14 | 0.8940 | `beam.span.((pump[ZX](hop0,hop0)+hop1)+((hop2+hop3)+(hop4+hop5)))` |
| 24 | 0.9242 | `link.n2.YY` |
| 24 | 0.9242 | `link.n2.ZX` |
| 24 | 0.9242 | `link.n2.XZ` |
| 36 | 0.9595 | `link.n3.YY_ZX` |
| 36 | 0.9595 | `link.n3.YY_XZ` |
| 36 | 0.9595 | `link.n3.ZX_YY` |
| 36 | 0.9595 | `link.n3.ZX_ZX` |
| 36 | 0.9595 | `link.n3.XZ_YY` |
| 36 | 0.9595 | `link.n3.XZ_XZ` |
| 48 | 0.9600 | `link.n4.YY_ZX_YY` |
| 48 | 0.9600 | `link.n4.YY_ZX_ZX` |
| 48 | 0.9600 | `link.n4.YY_XZ_YY` |
| 48 | 0.9600 | `link.n4.YY_XZ_XZ` |
| 48 | 0.9600 | `link.n4.ZX_YY_ZX` |
| 48 | 0.9600 | `link.n4.ZX_YY_XZ` |
| 48 | 0.9600 | `link.n4.ZX_ZX_YY` |
| 48 | 0.9600 | `link.n4.ZX_ZX_ZX` |
| 48 | 0.9600 | `link.n4.XZ_YY_ZX` |
| 48 | 0.9600 | `link.n4.XZ_YY_XZ` |
| 48 | 0.9600 | `link.n4.XZ_XZ_YY` |
| 48 | 0.9600 | `link.n4.XZ_XZ_XZ` |
| 60 | 0.9603 | `link.n5.ZX_ZX_ZX_ZX` |
| 60 | 0.9603 | `link.n5.YY_ZX_YY_XZ` |
| 60 | 0.9603 | `link.n5.XZ_XZ_XZ_XZ` |
| 72 | 0.9603 | `link.n6.ZX_ZX_ZX_ZX_ZX` |
| 72 | 0.9603 | `link.n6.XZ_XZ_XZ_XZ_XZ` |
| 72 | 0.9603 | `link.n6.YY_ZX_YY_XZ_YY` |
| 84 | 0.9603 | `link.n7.ZX_ZX_ZX_ZX_ZX_ZX` |
| 84 | 0.9603 | `link.n7.YY_ZX_YY_XZ_YY_ZX` |
| 84 | 0.9603 | `link.n7.XZ_XZ_XZ_XZ_XZ_XZ` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)),(pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)),(pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.ZX_ZX)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)),(pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_XZ,hop5.n3.YY_XZ)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)),(pump[YY](hop4.n3.YY_ZX,hop4.n3.ZX_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)),(pump[YY](hop4.n3.YY_ZX,hop4.n3.ZX_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.ZX_ZX)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.ZX_ZX)),(pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.ZX_ZX)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.ZX_ZX)),(pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_XZ,hop5.n3.YY_XZ)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.YY_ZX)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.YY_ZX)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.YY_ZX)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.ZX_ZX)),(pump[YY](hop4.n3.YY_ZX,hop4.n3.ZX_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.ZX_YY)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.ZX_YY)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.ZX_YY)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)),(pump[ZX](hop4.n3.YY_ZX,hop4.n3.ZX_YY)+pump[ZX](hop5.n3.YY_ZX,hop5.n3.ZX_YY)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.ZX_YY)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.ZX_YY)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.ZX_YY)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.YY_ZX)),(pump[ZX](hop4.n3.YY_ZX,hop4.n3.ZX_YY)+pump[ZX](hop5.n3.YY_ZX,hop5.n3.XZ_YY)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.ZX_YY)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.ZX_YY)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.ZX_YY)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.ZX_ZX)),(pump[ZX](hop4.n3.YY_ZX,hop4.n3.ZX_YY)+pump[ZX](hop5.n3.YY_ZX,hop5.n3.ZX_YY)))))))` |
| 90 | 0.9923 | `beam.span.(hop0.n3.YY_ZX+(pump[ZX](hop1.n3.YY_ZX,hop1.n3.ZX_YY)+(pump[ZX](hop2.n3.YY_ZX,hop2.n3.ZX_YY)+(pump[ZX](hop3.n3.YY_ZX,hop3.n3.ZX_YY)+pump[ZX]((pump[YY](hop4.n3.YY_ZX,hop4.n3.YY_ZX)+pump[YY](hop5.n3.YY_ZX,hop5.n3.ZX_ZX)),(pump[ZX](hop4.n3.YY_ZX,hop4.n3.ZX_YY)+pump[ZX](hop5.n3.YY_ZX,hop5.n3.XZ_YY)))))))` |

Full data: [`points_n6_ed0p01.csv`](points_n6_ed0p01.csv).

Figures: [`fidelity_vs_cost_n6_ed0p01.png`](fidelity_vs_cost_n6_ed0p01.png), [`fidelity_vs_rate_n6_ed0p01.png`](fidelity_vs_rate_n6_ed0p01.png).

## Reproducing

```bash
cd /home/shark/Documents/entanglement-purification-scheduler
source .venv/bin/activate
python3 experiments/pareto_frontiers.py
```

Total wall-clock time: ~31s.

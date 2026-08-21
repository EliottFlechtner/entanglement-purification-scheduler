# Entanglement Purification Scheduler

This repository contains the simulator, schedule representation, and search
tools developed for an internship thesis on purification scheduling in
half-repeater-graph-state (HRGS) all-photonic quantum-repeater networks.

The central question is not whether a particular purification circuit works,
but where, when, and in what order purification should be applied across an
end-to-end repeater chain. Given a network model and a resource budget, the
project constructs non-adaptive schedules, evaluates their physical metrics,
and searches for schedules that satisfy a fidelity requirement while optimizing
another objective, usually entanglement-generation rate.

The implementation is grounded in the HRGS architecture and purification
protocols described by the source papers. The full mathematical translation and
its assumptions are documented in
[Validated Formal Model Def.md](docs/instructions/Validated%20Formal%20Model%20Def.md).

## What Is In This Repository

At its core, a schedule is a rooted directed acyclic graph (DAG),
$\Sigma = (T, \phi)$. Its leaves generate half-RGS resources; its internal
nodes establish links, join adjacent spans, purify independent copies, model
waiting and heralding, and apply the final Pauli correction. A single
bottom-up evaluation of a valid DAG computes:

- **Fidelity** $F(\Sigma)$ from the terminal Bell-diagonal error vector.
- **Success probability** $P_{\mathrm{success}}(\Sigma)$ across all
    probabilistic purification steps.
- **Resource cost** $C(\Sigma)$ as the number of generated half-RGS resources.
- **Latency** $L(\Sigma)$ from the operation and heralding structure.
- **Rate** $R(\Sigma)=P_{\mathrm{success}}(\Sigma)/L(\Sigma)$ under a
    full-restart renewal model.

The main optimization form is

$$
\max_{\Sigma} R(\Sigma)
\quad\text{subject to}\quad
F(\Sigma) \geq F_{\min},\qquad C(\Sigma) \leq e_{\max}.
$$

The model also supports fidelity-, cost-, and latency-oriented objectives.

## Research Scope

This is a research optimizer, not a claim that arbitrary quantum-network
policies have been solved exactly.

- Schedules are fixed in advance: they do not adapt future decisions to
    intermediate measurement outcomes.
- Every result returned by a search tier is a concrete `ScheduleDAG`, validated
    structurally and evaluated with the same physical evaluator.
- Search coverage is bounded. `brute_force_search` is exhaustive only within
    its configured fixed families; default DP and beam search prune or cap their
    frontiers, especially for same-span pumping. Therefore, a found schedule is
    positive evidence that a feasible construction exists. A schedule not found
    is not proof that no legal schedule exists.
- `e_max` constrains generated-resource count. The separate concurrent-branch
    resource limit $M_{\max}$ is represented in the model but is not currently
    enforced.

Read [Optimality Scope.md](docs/Optimality%20Scope.md) before interpreting
optimality or infeasibility claims. It records a concrete excluded-move example
and the corresponding production-scale feasibility check. The current search
guarantees, recommended uses, and known limits are consolidated in
[Optimizer Status.md](docs/Optimizer%20Status.md).

## Quick Start

### Requirements

- Python 3.11 or newer
- `pip`
- Graphviz `dot` only when rendering schedule images
- Node.js and npm only for the optional architecture viewer
- TeX Live, `latexmk`, and Biber only for the thesis

Create an isolated environment and install the editable package with test and
plotting dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev,plotting]'
```

Run the test suite from the repository root:

```bash
.venv/bin/python -m pytest -q
```

The package itself has no mandatory third-party runtime dependency; `pytest`
and `matplotlib` are optional development and plotting extras.

## Run A Search

The primary command-line entry point is
[experiments/search_results.py](experiments/search_results.py). It prints
ranked candidates and can export summary tables or loadable DAG artifacts.

```bash
# Structured baseline families on the source-paper N=10 configuration.
.venv/bin/python experiments/search_results.py --top 10

# DP on a small configurable network. Suitable for inspection and cross-checks.
.venv/bin/python experiments/search_results.py \
    --algorithm dp --uniform --N 4 --e_max 24 --top 10

# Beam search for larger bounded searches.
.venv/bin/python experiments/search_results.py \
    --algorithm beam --uniform --N 10 --e_max 100 --beam-width 25 --top 10
```

The three tiers share the same DAG constructors, validation, evaluator, and
result type:

| Tier | Entry point | Best use | Guarantee |
|---|---|---|---|
| Structured brute force | `brute_force_search` | Named baselines and small fixed families | Exhaustive within its configured family and circuit grid |
| Span DP | `dp_search` | Small-instance exploration and reference comparisons | Default mode is bounded when pumping is enabled; `exact_pumping=True` is only practical on very small cases |
| Beam search | `beam_search` | Paper-scale and wider bounded searches | Heuristic frontier coverage controlled by `beam_width` |

Both DP and beam search include the structured baseline families by default, so
a single call can compare native candidates with raw, end-node, uniform-link,
and paper-structure baselines. See [CLI Command Reference.md](docs/CLI%20Command%20Reference.md)
for all flags and tuning parameters.

### Save And Inspect A Found Schedule

CSV and JSON result exports contain metrics only. Use `--save-top` when the
actual DAG must be kept, checked, or visualized.

```bash
# Save complete DAG and network artifacts.
.venv/bin/python experiments/search_results.py \
    --algorithm dp --uniform --N 4 --e_max 24 \
    --save-top 3 --save-dir outputs/schedules/example_n4

# Re-evaluate an artifact, compare stored metrics, and inspect its node counts.
.venv/bin/python experiments/load_schedule.py \
    outputs/schedules/example_n4/rank_001_*.json --verify --print-nodes

# Render an annotated SVG; requires Graphviz's `dot` executable.
.venv/bin/python experiments/load_schedule.py \
    outputs/schedules/example_n4/rank_001_*.json \
    --render outputs/schedules/example_n4/rank_001.svg --annotate
```

## Reproduce And Explore Results

The [`experiments/`](experiments) directory contains scripts that generate the
CSV, figure, and schedule artifacts under [`outputs/`](outputs). Output files
are generated research artifacts, not package inputs.

Useful starting points:

| Goal | Script or output |
|---|---|
| Reproduce fidelity versus depolarizing noise | [fig5_fidelity_vs_noise.py](experiments/fig5_fidelity_vs_noise.py) |
| Reproduce the timing/rate-ratio comparison | [fig6_rate_ratio.py](experiments/fig6_rate_ratio.py) |
| Compare paper baseline and optimizer over $e_d$ | [sweep_ed.py](experiments/sweep_ed.py) and [outputs/sweep_ed_n10](outputs/sweep_ed_n10) |
| Examine minimum searched budget over hop count | [sweep_min_budget_vs_n.py](experiments/sweep_min_budget_vs_n.py) |
| Measure memory-dephasing and emission-time sensitivity | [sweep_gamma_and_tau_emit.py](experiments/sweep_gamma_and_tau_emit.py) |
| Inspect a real pumping schedule | [visualize_pumping_schedule.py](experiments/visualize_pumping_schedule.py) |
| Build a small, annotated N=2 DAG example | [worked_example_n2_dag.py](experiments/worked_example_n2_dag.py) |

Most scripts can be invoked directly with `.venv/bin/python` from the repository
root. Some searches are intentionally expensive; their corresponding output
README explains the configuration, runtime, and scope of each result. In
particular, do not infer global scaling laws or universal budget lower bounds
from a bounded search sweep.

## Repository Map

```text
src/hrgs_scheduler/       Python package
    models/                 Network, state, error-vector, stage, and budget types
    operations/             Generation, backbone, and purification physics
    schedule/               DAG nodes, validation, evaluator, persistence, visualization
    search/                 Brute-force, DP, beam-search, and reporting utilities
    cost_functions.py       Feasibility constraints and objective scoring

tests/                    Unit, regression, and search/evaluator validation tests
experiments/              Reproducible research scripts
outputs/                  Generated tables, figures, and serialized schedules
docs/                     Formal model, scope, design rationale, and command reference
architecture/             Interactive optimizer architecture viewer
thesis/                   LaTeX internship report and its figures
```

## Read The Model And Design Rationale

The most useful documentation depends on what you want to do:

- [Validated Formal Model Def.md](docs/instructions/Validated%20Formal%20Model%20Def.md):
    authoritative schedule-as-DAG model, operation catalog, timing, and objectives.
- [Optimizer Status.md](docs/Optimizer%20Status.md): current implementation
    status, search-tier behavior, verification coverage, and known limitations.
- [Optimality Scope.md](docs/Optimality%20Scope.md): exactness boundaries and
    why a bounded search cannot establish non-existence.
- [Design Principles.md](docs/Design%20Principles.md): implementation decisions
    and reproducibility considerations, including pumping behavior.
- [CLI Command Reference.md](docs/CLI%20Command%20Reference.md): search,
    serialization, verification, and Graphviz commands.
- [thesis/README.md](thesis/README.md): build instructions for the report.

## Architecture Viewer

The optional browser-based atlas visualizes the system map, UML model, search
sequence, and memoized frontier lifecycle. It supports pan/zoom, element
inspection, Mermaid source inspection, and SVG export.

```bash
cd architecture/optimizer-viewer
npm install
npm run dev -- --host 127.0.0.1
```

Open the address printed by Vite, normally `http://127.0.0.1:5173/`. Details
and production-build instructions are in
[architecture/optimizer-viewer/README.md](architecture/optimizer-viewer/README.md).

## Thesis

The accompanying report explains the physical background, formal model, search
methods, experiments, and the limits of the claims in a linear narrative.

```bash
cd thesis
make
```

The resulting PDF is written to `thesis/main.pdf`. The thesis can be built
independently of the Python package once its TeX dependencies are installed.

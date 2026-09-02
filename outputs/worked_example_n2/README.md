# Worked example: N=2 purification schedule (§9, Validated Formal Model Def)

Implements the N=2 schedule from
`docs/instructions/Validated Formal Model Def.md` §9 verbatim,
as a `ScheduleDAG` built from first principles using the node API.

## Schedule structure

Two independent trials (A and B) are built and then combined by
end-node purification (optimistic: Herald follows Purify).

Each trial:
- **Hop 0** (RGSS-level purification): two same-side Gen nodes are
  purified with a YY circuit at κ=RGSS before the outer-photon Join.
  The purified anchor is then combined with a raw right-side anchor
  at the ABSA to produce a Span(0,1) edge.
- **Hop 1** (raw): two Gen nodes combined directly by Join → Span(1,2).
- **Swap** of both hop edges → Span(0,2).

End-node combination:
- **Purify-XZ**(trial_A, trial_B) at κ=Span(0,2)
- **Herald** (optimistic placement: after Purify, not before)
- **PauliCorrect** (root)

## Resource cost

C(Σ) = 10 Gen nodes
(3 per trial for hop 0 × 2 trials + 2 per trial for hop 1 × 2 trials = 10).

## Evaluation (N=2 paper config, e_d=0.01)

- Fidelity: 0.972820
- Success probability: 0.949090
- Rate: 0.9491
- Resource cost C: 10
- Latency: 1.0000

## Files

| File | Contents |
|---|---|
| `dag.dot` | Graphviz DOT source |
| `dag.png` | PNG render (bottom-to-top data-flow layout) |
| `dag.svg` | SVG render |

## Reproducing

```bash
cd /home/shark/Documents/entanglement-purification-scheduler
source .venv/bin/activate
PYTHONPATH=src python3 experiments/worked_example_n2_dag.py
```

## Node type legend

| Color | Shape | Node type | Role |
|---|---|---|---|
| light blue | ellipse | GenNode | leaf; fresh RGSS resource |
| orange | box | JoinNode | outer-photon BSM at ABSA |
| green | box | SwapNode | entanglement swap / stitching |
| purple | box | PurifyNode | 2→1 purification circuit |
| yellow | diamond | HeraldNode | heralding resolution |
| red | doublecircle | PauliCorrectNode | root; final Pauli correction |
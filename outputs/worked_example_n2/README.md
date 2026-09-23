# Worked example: N=2 purification schedule (§9, Validated Formal Model Def)

Implements the N=2 schedule from
`docs/instructions/Validated Formal Model Def.md` §9 verbatim,
as a `ScheduleDAG` built from first principles using the node API.

## Schedule structure

Two independent copies (A and B) are built with deliberately
different internal structure, then combined by end-node
purification (optimistic: Herald follows Purify).

Copy A:
- **Join hop 1 (0, 1)** (RGSS-level purification): two Gen nodes at
  Station 0 are purified with a YY circuit at κ=RGSS before the
  outer-photon Join. The purified anchor is then combined with a
  raw Gen at Station 1 at the ABSA to produce a (0, 1) edge.
- **Join hop 2 (1, 2)** (raw): Gen@Station 1 and Gen@Station 2
  combined directly by Join → (1, 2).
- **Swap** of both hop edges → (0, 2).

Copy B:
- **Join hop 1 (0, 1)** (raw, synchronized): Gen@Station 0 and
  Gen@Station 1 combined by Join → (0, 1); the Station-1 Gen idles
  until t=1 to model a synchronization wait.
- **Join hop 2 (1, 2)** (RGSS-level purification): two Gen nodes at
  Station 1 are purified with an XZ circuit at κ=RGSS before the
  outer-photon Join. The purified anchor is then combined with a
  raw Gen at Station 2 at the ABSA to produce a (1, 2) edge.
- **Swap** of both hop edges → (0, 2).

End-node combination:
- **Purify-XZ**(Copy A, Copy B) at κ=(0, 2)
- **Herald** (optimistic placement: after Purify, not before)
- **PauliCorrect** (root)

## Resource cost

C(Σ) = 10 Gen nodes
(3 per copy for the purified hop + 2 per copy for the raw hop, ×2 copies = 10).

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
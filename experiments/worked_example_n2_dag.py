"""
experiments/worked_example_n2_dag.py
======================================
Builds and renders the N=2 worked-example schedule from
docs/instructions/Validated Formal Model Def.md §9.

The example is chosen to exercise every mechanism in the formal model
(§3-§5) without being optimized for fidelity:

    N=2, B = (n_pur=2, e_max=12, M_max=6)

Structure
---------
Two independent trials (trial_A, trial_B), each built the same way:

  Hop 0 — RGSS-level purification on the left side:
    Gen(hop=0) ×2 → Purify-YY [κ=RGSS] → purified left-side anchor
    Gen(hop=0)    → raw right-side anchor
    AbsaBsm(purified_left, raw_right, hop=0) → edge [κ=(0,1)]

  Hop 1 — raw (no purification):
    Gen(hop=1) ×2 → AbsaBsm(hop=1) → edge [κ=(1,2)]

  Join(hop0_edge, hop1_edge) → trial [κ=(0,2)]

End-node purification (optimistic — Herald comes after Purify):
  Purify-XZ(trial_A, trial_B) → merged [κ=(0,2)]
  Herald(merged)
  PauliCorrect → root

Resource cost C(Σ) = 10 Gen nodes (3 per trial for hop 0, 2 per trial
for hop 1, ×2 trials), matching the §9 formula.

Outputs
-------
    outputs/worked_example_n2/dag.dot
    outputs/worked_example_n2/dag.png
    outputs/worked_example_n2/dag.svg
    outputs/worked_example_n2/README.md

Usage
-----
    PYTHONPATH=src python3 experiments/worked_example_n2_dag.py
"""

from __future__ import annotations

import html as _html
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from hrgs_scheduler.models.network_config import NetworkConfig
from hrgs_scheduler.models.stage import RGSS, RGSSStage, Span
from hrgs_scheduler.operations.purification import PurificationCircuit
from hrgs_scheduler.schedule.dag import ScheduleDAG
from hrgs_scheduler.schedule.evaluator import Evaluator
from hrgs_scheduler.schedule.node import (
    AbsaBsmNode,
    GenNode,
    HeraldNode,
    NodeId,
    PauliCorrectNode,
    PurifyNode,
    JoinNode,
)
from hrgs_scheduler.schedule.visualize import render, save_dot

# ---------------------------------------------------------------------------
# Thesis-quality DAG rendering: simplified labels, no node IDs, larger font
# ---------------------------------------------------------------------------

_THESIS_NODE_STYLE: dict = {
    GenNode: ("#AED6F1", "ellipse", "filled"),
    AbsaBsmNode: ("#F5B041", "box", "filled"),
    JoinNode: ("#82E0AA", "box", "filled"),
    PurifyNode: ("#C39BD3", "box", "filled"),
    HeraldNode: ("#F7DC6F", "diamond", "filled"),
    PauliCorrectNode: ("#F1948A", "doublecircle", "filled"),
}


def _thesis_label(node: object) -> str:
    """Simplified node label: no ID, no redundant timing fields."""
    if isinstance(node, GenNode):
        return f"Gen\\nhop {node.hop_index}"
    if isinstance(node, AbsaBsmNode):
        s = node.output_stage
        stage = "RGSS" if isinstance(s, RGSSStage) else f"({s.a},{s.b})"
        return f"BSM\\nhop {node.hop_index}\\n\u03ba={stage}"
    if isinstance(node, JoinNode):
        s = node.output_stage
        stage = "RGSS" if isinstance(s, RGSSStage) else f"({s.a},{s.b})"
        return f"Join\\n\u03ba={stage}"
    if isinstance(node, PurifyNode):
        s = node.output_stage
        stage = "RGSS" if isinstance(s, RGSSStage) else f"({s.a},{s.b})"
        return f"Purify-{node.circuit.name}\\n\u03ba={stage}"
    if isinstance(node, HeraldNode):
        return "Herald"
    if isinstance(node, PauliCorrectNode):
        return "PauliCorrect\\n(root)"
    return type(node).__name__


def to_dot_thesis(dag: ScheduleDAG) -> str:
    """DOT source with simplified labels and larger font for thesis figures."""
    lines = [
        "digraph Sigma_N2_thesis {",
        '    rankdir="BT";',
        '    node [fontname="Helvetica", fontsize=16];',
        '    edge [fontname="Helvetica", color="#555555"];',
    ]
    for nid, node in dag.nodes.items():
        label = _thesis_label(node)
        fillcolor, shape, style = _THESIS_NODE_STYLE.get(
            type(node), ("#FFFFFF", "box", "filled")
        )
        penwidth = "3" if nid == dag.root_id else "1"
        label_escaped = _html.escape(label).replace("\\n", "<BR/>")
        lines.append(
            f"    n{nid} [label=<{label_escaped}>, shape={shape}, "
            f'style="{style}", fillcolor="{fillcolor}", penwidth={penwidth}];'
        )
    for nid, node in dag.nodes.items():
        children = getattr(node, "children", ())
        for child_id in children:
            lines.append(f"    n{child_id} -> n{nid};")
    lines.append("}")
    return "\n".join(lines)


def render_thesis_png(dag: ScheduleDAG, path: str, dpi: int = 200) -> None:
    """Render thesis-quality PNG using simplified labels at *dpi* resolution."""
    dot_src = to_dot_thesis(dag)
    proc = subprocess.run(
        ["dot", "-Tpng", f"-Gdpi={dpi}", "-o", path],
        input=dot_src.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode, proc.args, output=proc.stdout, stderr=proc.stderr
        )


OUTPUT_DIR = _PROJECT_ROOT / "outputs" / "worked_example_n2"
N = 2


def _build_trial(
    nodes: dict[NodeId, object],
    nid: int,
) -> tuple[NodeId, int]:
    """Build one independent trial (trial_A or trial_B) of the N=2 example.

    Returns (join_node_id, next_free_nid).

    Hop 0: RGSS-level purification (3 Gen nodes)
      Gen(hop=0) ×2 → Purify-YY [κ=RGSS]
      Gen(hop=0)    → raw right
      AbsaBsm(purified, raw_right, hop=0) → Span(0,1)

    Hop 1: raw (2 Gen nodes)
      Gen(hop=1) ×2 → AbsaBsm(hop=1) → Span(1,2)

    Join(hop0_edge, hop1_edge) → Span(0,2)
    """
    # --- Hop 0: RGSS-level purification ---
    g0a = GenNode(node_id=nid, hop_index=0)
    nid += 1
    g0b = GenNode(node_id=nid, hop_index=0)
    nid += 1
    nodes[g0a.node_id] = g0a
    nodes[g0b.node_id] = g0b

    pur_rgss = PurifyNode(
        node_id=nid,
        children=(g0a.node_id, g0b.node_id),
        circuit=PurificationCircuit.YY,
        output_stage=RGSS,
    )
    nid += 1
    nodes[pur_rgss.node_id] = pur_rgss

    g0c = GenNode(node_id=nid, hop_index=0)  # raw right-side anchor
    nid += 1
    nodes[g0c.node_id] = g0c

    bsm0 = AbsaBsmNode(
        node_id=nid,
        children=(pur_rgss.node_id, g0c.node_id),
        hop_index=0,
    )
    nid += 1
    nodes[bsm0.node_id] = bsm0

    # --- Hop 1: raw ---
    g1a = GenNode(node_id=nid, hop_index=1)
    nid += 1
    g1b = GenNode(node_id=nid, hop_index=1)
    nid += 1
    nodes[g1a.node_id] = g1a
    nodes[g1b.node_id] = g1b

    bsm1 = AbsaBsmNode(
        node_id=nid,
        children=(g1a.node_id, g1b.node_id),
        hop_index=1,
    )
    nid += 1
    nodes[bsm1.node_id] = bsm1

    # --- Join the two hop edges ---
    join = JoinNode(
        node_id=nid,
        children=(bsm0.node_id, bsm1.node_id),
        output_stage=Span(0, 2),
    )
    nid += 1
    nodes[join.node_id] = join

    return join.node_id, nid


def build_n2_worked_example() -> ScheduleDAG:
    """Construct the N=2 worked-example DAG from §9."""
    nodes: dict[NodeId, object] = {}
    nid = 0

    trial_a_id, nid = _build_trial(nodes, nid)
    trial_b_id, nid = _build_trial(nodes, nid)

    # End-node purification: Purify-XZ(trial_A, trial_B)
    pur_end = PurifyNode(
        node_id=nid,
        children=(trial_a_id, trial_b_id),
        circuit=PurificationCircuit.XZ,
        output_stage=Span(0, N),
    )
    nid += 1
    nodes[pur_end.node_id] = pur_end

    # Herald (optimistic: comes after Purify, not before)
    herald = HeraldNode(
        node_id=nid,
        children=(pur_end.node_id,),
        propagation_time=1.0,
    )
    nid += 1
    nodes[herald.node_id] = herald

    # PauliCorrect (root)
    root = PauliCorrectNode(
        node_id=nid,
        children=(herald.node_id,),
        N=N,
    )
    nodes[root.node_id] = root
    root_id = root.node_id

    dag = ScheduleDAG(nodes=nodes, root_id=root_id, N=N)
    dag.validate()
    return dag


def write_readme(dag: ScheduleDAG, network: NetworkConfig) -> None:
    result = Evaluator(network).evaluate(dag)
    lines = [
        "# Worked example: N=2 purification schedule (§9, Validated Formal Model Def)",
        "",
        "Implements the N=2 schedule from",
        "`docs/instructions/Validated Formal Model Def.md` §9 verbatim,",
        "as a `ScheduleDAG` built from first principles using the node API.",
        "",
        "## Schedule structure",
        "",
        "Two independent trials (A and B) are built and then combined by",
        "end-node purification (optimistic: Herald follows Purify).",
        "",
        "Each trial:",
        "- **Hop 0** (RGSS-level purification): two same-side Gen nodes are",
        "  purified with a YY circuit at κ=RGSS before the outer-photon BSM.",
        "  The purified anchor is then combined with a raw right-side anchor",
        "  at the ABSA to produce a Span(0,1) edge.",
        "- **Hop 1** (raw): two Gen nodes combined directly by AbsaBsm → Span(1,2).",
        "- **Join** of both hop edges → Span(0,2).",
        "",
        "End-node combination:",
        "- **Purify-XZ**(trial_A, trial_B) at κ=Span(0,2)",
        "- **Herald** (optimistic placement: after Purify, not before)",
        "- **PauliCorrect** (root)",
        "",
        "## Resource cost",
        "",
        f"C(Σ) = {dag.gen_node_count} Gen nodes",
        "(3 per trial for hop 0 × 2 trials + 2 per trial for hop 1 × 2 trials = 10).",
        "",
        "## Evaluation (N=2 paper config, e_d=0.01)",
        "",
        f"- Fidelity: {result.fidelity:.6f}",
        f"- Success probability: {result.success_prob:.6f}",
        f"- Rate: {result.rate:.4f}",
        f"- Resource cost C: {result.resource_cost}",
        f"- Latency: {result.latency:.4f}",
        "",
        "## Files",
        "",
        "| File | Contents |",
        "|---|---|",
        "| `dag.dot` | Graphviz DOT source |",
        "| `dag.png` | PNG render (bottom-to-top data-flow layout) |",
        "| `dag.svg` | SVG render |",
        "",
        "## Reproducing",
        "",
        "```bash",
        "cd /home/shark/Documents/entanglement-purification-scheduler",
        "source .venv/bin/activate",
        "PYTHONPATH=src python3 experiments/worked_example_n2_dag.py",
        "```",
        "",
        "## Node type legend",
        "",
        "| Color | Shape | Node type | Role |",
        "|---|---|---|---|",
        "| light blue | ellipse | GenNode | leaf; fresh RGSS resource |",
        "| orange | box | AbsaBsmNode | outer-photon BSM at ABSA |",
        "| green | box | JoinNode | entanglement swap / stitching |",
        "| purple | box | PurifyNode | 2→1 purification circuit |",
        "| yellow | diamond | HeraldNode | heralding resolution |",
        "| red | doublecircle | PauliCorrectNode | root; final Pauli correction |",
    ]
    (OUTPUT_DIR / "README.md").write_text("\n".join(lines))


def main() -> None:
    print("Building N=2 worked-example DAG ...", flush=True)
    dag = build_n2_worked_example()
    print(
        f"DAG built and validated: {len(dag.nodes)} nodes, "
        f"{dag.gen_node_count} Gen nodes (C={dag.gen_node_count})",
        flush=True,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dot_path = str(OUTPUT_DIR / "dag.dot")
    png_path = str(OUTPUT_DIR / "dag.png")
    svg_path = str(OUTPUT_DIR / "dag.svg")

    save_dot(dag, dot_path, graph_name="Sigma_N2_example")
    print(f"DOT written: {dot_path}", flush=True)

    render(dag, png_path, fmt="png", graph_name="Sigma_N2_example")
    print(f"PNG rendered: {png_path}", flush=True)

    render(dag, svg_path, fmt="svg", graph_name="Sigma_N2_example")
    print(f"SVG rendered: {svg_path}", flush=True)

    # Thesis-quality version: simplified labels, no IDs, larger font
    thesis_png_path = str(OUTPUT_DIR / "dag_thesis.png")
    render_thesis_png(dag, thesis_png_path, dpi=200)
    print(f"Thesis PNG rendered: {thesis_png_path}", flush=True)

    # Evaluate against N=2 version of the paper config for the README
    network = NetworkConfig.uniform(
        N=N,
        length=2.0,
        branching=(16, 14, 1),
        arm_count=18,
        p_x_inner=0.0,
        p_z_inner=0.0,
        e_d=0.01,
        gamma=0.0,
        c=2e5,
    )
    write_readme(dag, network)
    print(f"README written: {OUTPUT_DIR / 'README.md'}", flush=True)
    print("Done.", flush=True)


if __name__ == "__main__":
    main()

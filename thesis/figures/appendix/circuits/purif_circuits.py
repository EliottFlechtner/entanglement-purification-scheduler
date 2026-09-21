from pathlib import Path

from qiskit import QuantumCircuit
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "thesis" / "figures" / "appendix"

# ============================================================
# Conventions
# ============================================================
#
# Alice:
#   q[0] = retained qubit (top)
#   q[1] = measured qubit (bottom)
#
# Bob:
#   q[2] = retained qubit (top)
#   q[3] = measured qubit (bottom)
#
# The measured qubits are q[1] and q[3].
#
# Classical bits:
#   c[0] = Alice measurement
#   c[1] = Bob measurement
#
# ============================================================


def make_zx_circuit():
    """
    Z_a X_b purification circuit.

    Alice performs the Z-parity measurement:
        CX(q0 -> q1), measure q1

    Bob performs the X-parity measurement:
        CX(q3 -> q2), H(q3), measure q3

    q0 and q2 are retained.
    """

    qc = QuantumCircuit(4, 2)

    # Alice: Z measurement
    qc.cx(0, 1)
    qc.measure(1, 0)

    # Bob: X measurement
    qc.cx(3, 2)
    qc.h(3)
    qc.measure(3, 1)

    return qc


def make_xz_circuit():
    """
    X_a Z_b purification circuit.

    This is obtained from Z_a X_b by exchanging
    the local circuits performed by Alice and Bob.

    Alice performs the X-parity measurement:
        CX(q1 -> q0), H(q1), measure q1

    Bob performs the Z-parity measurement:
        CX(q2 -> q3), measure q3

    q0 and q2 are retained.
    """

    qc = QuantumCircuit(4, 2)

    # Alice: X measurement
    qc.cx(1, 0)
    qc.h(1)
    qc.measure(1, 0)

    # Bob: Z measurement
    qc.cx(2, 3)
    qc.measure(3, 1)

    return qc


def make_yy_circuit():
    """
    Y_a Y_b purification circuit.

    Alice:
        H -> S† -> CX -> S -> H
        measure lower qubit

    Bob:
        S† -> CX -> S
        lower qubit: S† -> H
        measure lower qubit

    q0 and q2 are retained.
    """

    qc = QuantumCircuit(4, 2)

    # --------------------------------------------------------
    # Alice
    # --------------------------------------------------------
    qc.h(0)
    qc.sdg(0)

    qc.h(1)
    qc.sdg(1)

    qc.cx(0, 1)

    qc.s(0)
    qc.h(1)

    qc.measure(1, 0)

    # --------------------------------------------------------
    # Bob
    # --------------------------------------------------------
    qc.sdg(2)
    qc.sdg(3)

    qc.cx(2, 3)

    qc.s(2)
    qc.h(3)

    qc.measure(3, 1)

    return qc


# ============================================================
# Paper-style rendering
# ============================================================

circuits = {
    "C_ZX": make_zx_circuit(),
    "C_XZ": make_xz_circuit(),
    "C_YY": make_yy_circuit(),
}


for name, qc in circuits.items():

    fig = qc.draw(
        output="mpl",
        style="bw",
        fold=-1,
        scale=1.35,
        cregbundle=True,
        initial_state=False,
    )

    # Remove excess margins
    fig.tight_layout(pad=0.2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # High-resolution PNG
    fig.savefig(
        OUTPUT_DIR / f"{name}.png",
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.03,
        transparent=True,
    )

    # Also save PDF for direct LaTeX inclusion
    fig.savefig(
        OUTPUT_DIR / f"{name}.pdf",
        bbox_inches="tight",
        pad_inches=0.03,
        transparent=True,
    )

    plt.close(fig)

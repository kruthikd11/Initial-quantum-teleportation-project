import os
import sys
import shutil
import tempfile
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector, state_fidelity


# ============================================================
# 1. SETTINGS
# ============================================================

SHOTS = 1024

# Alice's input state |psi> = alpha|0> + beta|1>
alpha = 1 / np.sqrt(2)
beta = 1 / np.sqrt(2)

input_state = Statevector([alpha, beta])

# Images are first created in a temporary folder (always writable),
# then copied together into ONE final folder "Teleportation_Output".
# This avoids OneDrive / Desktop write problems on Windows.

try:
    BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_FOLDER = os.getcwd()

STAGING_FOLDER = tempfile.mkdtemp(prefix="teleportation_")

# Where the final images should end up (tried in this order)
DESTINATIONS = [
    os.path.join(BASE_FOLDER, "Teleportation_Output"),
    os.path.join(os.path.expanduser("~"), "Teleportation_Output"),
]


# ============================================================
# 2. TELEPORTATION TABLE (as in the textbook)
# ============================================================
# Alice measures q0 -> M1 and q1 -> M2.   Input string = "M1 M2".
#
#   M1M2   Bob's state before correction
#   00     alpha|0> + beta|1>
#   01     alpha|1> + beta|0>
#   10     alpha|0> - beta|1>
#   11     alpha|1> - beta|0>
#
# Bob applies  Z^M1 X^M2  (X first, then Z).

# text form, [amplitude of |0>, amplitude of |1>]
BOB_TABLE = {
    "00": ("α|0⟩ + β|1⟩", [alpha, beta]),
    "01": ("α|1⟩ + β|0⟩", [beta, alpha]),
    "10": ("α|0⟩ − β|1⟩", [alpha, -beta]),
    "11": ("α|1⟩ − β|0⟩", [-beta, alpha]),
}

CORRECTION_NAMES = {
    "00": "No correction",
    "01": "X",
    "10": "Z",
    "11": "X then Z",
}

CORRECTION_GATES = {
    "00": [],
    "01": ["X"],
    "10": ["Z"],
    "11": ["X", "Z"],
}


TERMS = {
    "00": [("+", "α", "0"), ("+", "β", "1")],
    "01": [("+", "α", "1"), ("+", "β", "0")],
    "10": [("+", "α", "0"), ("-", "β", "1")],
    "11": [("+", "α", "1"), ("-", "β", "0")],
}


def terms_text(key, numeric):
    """Bob's state before correction, in the textbook term order.
    numeric=False -> α|1⟩ + β|0⟩      numeric=True -> 0.707107|1⟩ + 0.707107|0⟩"""
    out = ""
    for i, (sign, name, ket) in enumerate(TERMS[key]):
        value = alpha if name == "α" else beta
        coeff = f"{value:.6f}" if numeric else name
        if i == 0:
            out += ("-" if sign == "-" else "") + f"{coeff}|{ket}⟩"
        else:
            out += f" {'−' if sign == '-' else '+'} {coeff}|{ket}⟩"
    return out


def fmt_state(a0, a1):
    sign = "+" if a1.real >= 0 else "-"
    return f"{a0.real:.6f}|0⟩ {sign} {abs(a1.real):.6f}|1⟩"


# ============================================================
# 3. USER INPUT
# ============================================================

print()
print("=" * 80)
print("                    QUANTUM TELEPORTATION")
print("=" * 80)
print()
print("Alice's input state:")
print("|ψ⟩ = α|0⟩ + β|1⟩")
print()
print(f"α = {alpha:.6f}")
print(f"β = {beta:.6f}")
print()
print("Bob's qubit before correction, for each of Alice's results:")
print()
print("  M1M2   Bob's state       With α, β values                      Correction")
print("  " + "-" * 76)

for key in ["00", "01", "10", "11"]:
    text, amps = BOB_TABLE[key]
    print(
        f"  {key}     {terms_text(key, False):<15}  "
        f"{terms_text(key, True):<34}  "
        f"{CORRECTION_NAMES[key]}"
    )

print()
print("M1 = measurement of q0,  M2 = measurement of q1")
print()
print("Enter Alice's measurement result (M1 M2):")
print("00, 01, 10, or 11")
print()

while True:
    measurement = input("Enter measurement: ").strip()
    if measurement in BOB_TABLE:
        break
    print()
    print("Invalid input.")
    print("Please enter only 00, 01, 10, or 11.")
    print()

correction = CORRECTION_NAMES[measurement]
state_text, state_amps = BOB_TABLE[measurement]

print()
print(f"Bob's state before correction : {state_text}")
print(f"                              = {terms_text(measurement, True)}")
print(f"Bob's correction              : {correction}")


# ============================================================
# 4. ONE COMPLETE CIRCUIT DEFINITION (ALICE + BOB)
# ============================================================
# Items:  ("H", q)   ("CX", control, target)   ("M", q, label)   ("G", label, q)
#
# q0 = Alice's |psi>, q1 = Alice's Bell half, q2 = Bob's Bell half

ALICE_COLUMNS = [
    [("H", 1)],
    [("CX", 1, 2)],
    [("CX", 0, 1)],
    [("H", 0)],
    [("M", 0, "M1"), ("M", 1, "M2")],
]

BOB_COLUMNS = [
    [("G", gate, 2)] for gate in CORRECTION_GATES[measurement]
]

if not BOB_COLUMNS:
    BOB_COLUMNS = [[]]

ALL_COLUMNS = ALICE_COLUMNS + BOB_COLUMNS
N_ALICE = len(ALICE_COLUMNS)


# ============================================================
# 5. TERMINAL CIRCUIT DRAWING
# ============================================================

def ascii_circuit(columns):

    W = 9
    prefixes = [
        "Alice  q0: |ψ⟩ ",
        "               ",
        "Alice  q1:     ",
        "               ",
        "Bob    q2:     ",
    ]

    rows = [p + "─" if p.strip() else p + " " for p in prefixes]

    for column in columns:

        cells = []
        for r in range(5):
            cells.append(" " * W if r % 2 == 1 else "─" * W)

        for item in column:

            kind = item[0]

            if kind == "H":
                cells[2 * item[1]] = "H".center(W, "─")

            elif kind == "M":
                cells[2 * item[1]] = item[2].center(W, "─")

            elif kind == "G":
                cells[2 * item[2]] = item[1].center(W, "─")

            elif kind == "CX":
                c, t = item[1], item[2]
                cells[2 * c] = "●".center(W, "─")
                cells[2 * t] = "⊕".center(W, "─")

                lo, hi = min(c, t), max(c, t)
                for r in range(2 * lo + 1, 2 * hi, 2):
                    cells[r] = (
                        " " * (W // 2) + "│" + " " * (W - W // 2 - 1)
                    )

        for r in range(5):
            rows[r] += cells[r]

    rows[0] += "──"
    rows[2] += "──"
    rows[4] += "── |ψ⟩"

    total_width = len(prefixes[0]) + 1 + len(columns) * W + 2

    footer = (
        "└"
        + " complete teleportation ".center(total_width - 2, "─")
        + "┘"
    )

    legend = (
        "Alice owns q0 and q1  |  Bob owns q2  |  "
        "Bob's correction is applied on q2"
    )

    return "\n".join(rows + ["", footer, "", legend])


print()
print("=" * 80)
print("                 COMPLETE TELEPORTATION CIRCUIT")
print("=" * 80)
print()
print(ascii_circuit(ALL_COLUMNS))
print()
print("Measurement selected :", measurement)
print("Bob correction       :", correction)


# ============================================================
# 6. SIMULATION CIRCUIT (used only for the numbers)
# ============================================================

def build_simulation_circuit(measure_alice):

    qc = QuantumCircuit(3, 2)

    qc.initialize([alpha, beta], 0)

    qc.h(1)
    qc.cx(1, 2)

    qc.cx(0, 1)
    qc.h(0)

    if measure_alice:
        qc.measure(0, 0)      # M1
        qc.measure(1, 1)      # M2

    return qc


# ============================================================
# 7. RUN 1024 SHOTS
# ============================================================

simulator = AerSimulator()

result = simulator.run(
    build_simulation_circuit(True),
    shots=SHOTS
).result()

raw_counts = result.get_counts()

counts = {"00": 0, "01": 0, "10": 0, "11": 0}

for bit_string, count in raw_counts.items():
    # Qiskit key = "c1 c0" = "M2 M1"  ->  reverse to get "M1 M2"
    key = bit_string.replace(" ", "")[-2:][::-1]
    counts[key] += count

print()
print("=" * 80)
print("                    MEASUREMENT RESULTS")
print("=" * 80)
print()
print(f"Actual measurement counts from {SHOTS} shots (M1M2):")
print()

for bit_string in ["00", "01", "10", "11"]:
    count = counts[bit_string]
    percentage = count / SHOTS * 100
    print(f"  {bit_string} : {count:4d} / {SHOTS} ({percentage:6.2f}%)")

print()
print("User selected measurement :", measurement)
print("Bob's correction          :", correction)


# ============================================================
# 8. BOB'S STATE (from the simulation) + CHECK AGAINST TABLE
# ============================================================

full_state = Statevector.from_instruction(
    build_simulation_circuit(False)
)

m1_value = int(measurement[0])      # q0
m2_value = int(measurement[1])      # q1

bob_amplitudes = np.zeros(2, dtype=complex)

for index, amplitude_value in enumerate(full_state.data):
    q0 = (index >> 0) & 1
    q1 = (index >> 1) & 1
    q2 = (index >> 2) & 1

    if q0 == m1_value and q1 == m2_value:
        bob_amplitudes[q2] = amplitude_value

norm = np.linalg.norm(bob_amplitudes)

if norm == 0:
    raise RuntimeError("Could not extract Bob's state.")

bob_amplitudes /= norm

table_match = state_fidelity(
    Statevector(bob_amplitudes),
    Statevector(state_amps)
)

bob_circuit = QuantumCircuit(1)
bob_circuit.initialize(bob_amplitudes, 0)

for gate in CORRECTION_GATES[measurement]:
    if gate == "X":
        bob_circuit.x(0)
    elif gate == "Z":
        bob_circuit.z(0)

bob_state = Statevector.from_instruction(bob_circuit)

fidelity = state_fidelity(input_state, bob_state)


# ============================================================
# 9. FINAL TERMINAL RESULT
# ============================================================

print()
print("=" * 80)
print("                         RESULT")
print("=" * 80)
print()
print(f"Alice input                   : {fmt_state(alpha, beta)}")
print()
print(f"Bob before correction (table) : {state_text}")
print(f"                              = {terms_text(measurement, True)}")
print(f"Simulation matches table      : {table_match:.6f}")
print()
print(f"Bob output after correction   : {fmt_state(bob_state.data[0], bob_state.data[1])}")
print()
print("Measurement :", measurement)
print("Correction  :", correction)
print()
print(f"Fidelity    : {fidelity:.6f}")
print()

if fidelity > 0.999999:
    print("✓ Alice input = Bob output")
    print("✓ TELEPORTATION SUCCESSFUL")
else:
    print("✗ Alice input does not match Bob output")


# ============================================================
# 10. SAVE COMPLETE CIRCUIT PNG
# ============================================================

def draw_circuit_png(columns, path):

    n_cols = len(columns)
    y_of = {0: 2.0, 1: 1.0, 2: 0.0}

    fig, ax = plt.subplots(figsize=(2 + 1.4 * n_cols, 4.2))

    x_left, x_right = 0.0, n_cols + 1.0

    ax.add_patch(Rectangle(
        (-1.6, 0.6), x_right + 1.9, 1.9,
        facecolor="#dbeafe", edgecolor="none", alpha=0.7, zorder=0
    ))
    ax.add_patch(Rectangle(
        (-1.6, -0.6), x_right + 1.9, 1.1,
        facecolor="#fde7c8", edgecolor="none", alpha=0.8, zorder=0
    ))

    for q in range(3):
        ax.plot([x_left + 0.3, x_right], [y_of[q], y_of[q]],
                color="black", linewidth=1.5, zorder=1)

    ax.text(x_left + 0.25, y_of[0], "Alice  q0: |ψ⟩", ha="right",
            va="center", fontsize=13)
    ax.text(x_left + 0.25, y_of[1], "Alice  q1:", ha="right",
            va="center", fontsize=13)
    ax.text(x_left + 0.25, y_of[2], "Bob  q2:", ha="right",
            va="center", fontsize=13)
    ax.text(x_right + 0.1, y_of[2], "|ψ⟩", ha="left",
            va="center", fontsize=13)

    def box(x, y, label):
        ax.add_patch(Rectangle(
            (x - 0.25, y - 0.22), 0.5, 0.44,
            facecolor="white", edgecolor="black",
            linewidth=1.5, zorder=3
        ))
        ax.text(x, y, label, ha="center", va="center",
                fontsize=12, fontweight="bold", zorder=4)

    for i, column in enumerate(columns):

        x = 1.0 + i

        for item in column:

            kind = item[0]

            if kind == "H":
                box(x, y_of[item[1]], "H")

            elif kind == "M":
                box(x, y_of[item[1]], item[2])

            elif kind == "G":
                box(x, y_of[item[2]], item[1])

            elif kind == "CX":
                c, t = item[1], item[2]
                ax.plot([x, x], [y_of[c], y_of[t]],
                        color="black", linewidth=1.5, zorder=2)
                ax.add_patch(Circle((x, y_of[c]), 0.07,
                                    color="black", zorder=4))
                ax.add_patch(Circle((x, y_of[t]), 0.16,
                                    facecolor="white", edgecolor="black",
                                    linewidth=1.5, zorder=3))
                ax.plot([x - 0.16, x + 0.16], [y_of[t], y_of[t]],
                        color="black", linewidth=1.5, zorder=4)
                ax.plot([x, x], [y_of[t] - 0.16, y_of[t] + 0.16],
                        color="black", linewidth=1.5, zorder=4)

    ax.plot([0.3, 0.3, x_right, x_right],
            [-0.75, -0.9, -0.9, -0.75],
            color="black", linewidth=1.2)
    ax.text((0.3 + x_right) / 2, -1.0,
            "complete teleportation",
            ha="center", va="top", fontsize=12, style="italic")

    ax.set_xlim(-1.6, x_right + 0.8)
    ax.set_ylim(-1.5, 2.6)
    ax.set_aspect("equal")
    ax.axis("off")

    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


print()
print("Creating images ...")
print()
print("Creating circuit.png ...")

draw_circuit_png(
    ALL_COLUMNS,
    os.path.join(STAGING_FOLDER, "circuit.png")
)


# ============================================================
# 11. SAVE MEASUREMENT HISTOGRAM
# ============================================================

print("Creating measurement_histogram.png ...")

labels = ["00", "01", "10", "11"]
values = [counts[k] for k in labels]
max_value = max(values)

plt.figure(figsize=(9, 6))
bars = plt.bar(labels, values)

plt.title("Quantum Teleportation Measurement Results", fontsize=16)
plt.xlabel("Alice's Measurement (M1 M2)", fontsize=12)
plt.ylabel("Counts", fontsize=12)
plt.ylim(0, max_value * 1.20)

for bar, value in zip(bars, values):
    percentage = value / SHOTS * 100
    plt.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + max_value * 0.02,
        f"{value}\n({percentage:.2f}%)",
        ha="center",
        va="bottom"
    )

plt.tight_layout()
plt.savefig(
    os.path.join(STAGING_FOLDER, "measurement_histogram.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.close()


# ============================================================
# 12. BLOCH SPHERE FUNCTIONS
# ============================================================

def bloch_coordinates(state):
    a = state.data[0]
    b = state.data[1]

    x = 2 * np.real(np.conjugate(a) * b)
    y = 2 * np.imag(np.conjugate(a) * b)
    z = abs(a) ** 2 - abs(b) ** 2

    return [x, y, z]


def draw_bloch_sphere(ax, vector, title):
    u = np.linspace(0, 2 * np.pi, 40)
    v = np.linspace(0, np.pi, 20)

    x = np.outer(np.cos(u), np.sin(v))
    y = np.outer(np.sin(u), np.sin(v))
    z = np.outer(np.ones(np.size(u)), np.cos(v))

    ax.plot_wireframe(x, y, z, alpha=0.15, linewidth=0.5)

    ax.plot([-1, 1], [0, 0], [0, 0], linewidth=1)
    ax.plot([0, 0], [-1, 1], [0, 0], linewidth=1)
    ax.plot([0, 0], [0, 0], [-1, 1], linewidth=1)

    ax.quiver(
        0, 0, 0,
        vector[0], vector[1], vector[2],
        linewidth=2,
        arrow_length_ratio=0.12
    )

    ax.text(1.1, 0, 0, "X")
    ax.text(0, 1.1, 0, "Y")
    ax.text(0, 0, 1.1, "|0⟩")
    ax.text(0, 0, -1.1, "|1⟩")

    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)
    ax.set_zlim(-1.1, 1.1)
    ax.set_box_aspect([1, 1, 1])
    ax.set_title(title, fontsize=13)


alice_bloch = bloch_coordinates(input_state)
bob_bloch = bloch_coordinates(bob_state)

ALICE_TITLE = "Alice's Input State |ψ⟩"
BOB_TITLE = f"Bob's Output State |ψ⟩\nMeasurement = {measurement}"


# ============================================================
# 13. SAVE BLOCH SPHERE IMAGES
# ============================================================

print("Creating bloch_spheres.png ...")

fig = plt.figure(figsize=(12, 6))
ax1 = fig.add_subplot(121, projection="3d")
ax2 = fig.add_subplot(122, projection="3d")

draw_bloch_sphere(ax1, alice_bloch, ALICE_TITLE)
draw_bloch_sphere(ax2, bob_bloch, BOB_TITLE)

fig.suptitle("Quantum Teleportation - Bloch Sphere Comparison", fontsize=16)
fig.subplots_adjust(left=0.03, right=0.97, bottom=0.05, top=0.88, wspace=0.12)

plt.savefig(
    os.path.join(STAGING_FOLDER, "bloch_spheres.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.close()


print("Creating alice_bloch_sphere.png ...")

fig = plt.figure(figsize=(6, 6))
ax = fig.add_subplot(111, projection="3d")
draw_bloch_sphere(ax, alice_bloch, ALICE_TITLE)
plt.savefig(
    os.path.join(STAGING_FOLDER, "alice_bloch_sphere.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.close()


print("Creating bob_bloch_sphere.png ...")

fig = plt.figure(figsize=(6, 6))
ax = fig.add_subplot(111, projection="3d")
draw_bloch_sphere(ax, bob_bloch, BOB_TITLE)
plt.savefig(
    os.path.join(STAGING_FOLDER, "bob_bloch_sphere.png"),
    dpi=300,
    bbox_inches="tight"
)
plt.close()


# ============================================================
# 14. COPY ALL IMAGES INTO ONE FINAL FOLDER
# ============================================================

FILES = [
    "circuit.png",
    "measurement_histogram.png",
    "bloch_spheres.png",
    "alice_bloch_sphere.png",
    "bob_bloch_sphere.png",
]


def publish_files(destinations):

    for folder in destinations:

        try:
            os.makedirs(folder, exist_ok=True)

            for name in FILES:

                source = os.path.join(STAGING_FOLDER, name)
                target = os.path.join(folder, name)

                if os.path.exists(target):
                    try:
                        os.remove(target)
                    except OSError:
                        pass

                shutil.copyfile(source, target)

                if os.path.getsize(target) == 0:
                    raise OSError("empty file written")

            return folder

        except OSError as error:
            print(f"Could not save into: {folder}")
            print(f"  reason: {error}")
            print("  trying the next location ...")
            print()

    return None


FINAL_FOLDER = publish_files(DESTINATIONS)

if FINAL_FOLDER is None:
    FINAL_FOLDER = STAGING_FOLDER
    print("Could not copy to any normal folder.")
    print("Your images are in this temporary folder instead:")
    print()


print()
print("=" * 80)
print("                       FILES SAVED")
print("=" * 80)
print()
print("Output folder:")
print(FINAL_FOLDER)
print()

all_ok = True

for number, name in enumerate(FILES, start=1):
    path = os.path.join(FINAL_FOLDER, name)
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"  {number}. ✓ {name}  ({size_kb:.0f} KB)")
    else:
        all_ok = False
        print(f"  {number}. ✗ {name}  NOT FOUND")

print()

if all_ok:
    print("✓ All images saved in one folder")
else:
    print("✗ Some images are missing - see above")

print()
print("=" * 80)

# Open the folder automatically (Windows / macOS / Linux)
try:
    if os.name == "nt":
        os.startfile(FINAL_FOLDER)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", FINAL_FOLDER])
    else:
        subprocess.Popen(["xdg-open", FINAL_FOLDER], stderr=subprocess.DEVNULL)
except Exception:
    pass
# Quantum Teleportation Using Qiskit

## About the Project
This project implements a simulation of Quantum Teleportation using Python and Qiskit.

Quantum Teleportation is a quantum communication protocol that transfers an unknown quantum state from Alice to Bob using quantum entanglement and classical communication.

## Project Objectives
- Implement the Quantum Teleportation protocol.
- Understand quantum entanglement.
- Perform Bell-state measurements.
- Apply quantum correction gates.
- Simulate quantum circuits using Qiskit Aer.
- Visualize results using measurement histograms and Bloch spheres.

## Qubit Configuration

| Qubit | Description |
|---|---|
| q0 | Alice's input qubit |
| q1 | Alice's entangled qubit |
| q2 | Bob's qubit |

## Teleportation Steps

1. Alice prepares the input quantum state.
2. Alice and Bob share an entangled pair.
3. Alice performs Bell-state measurements.
4. Alice obtains two classical measurement bits.
5. Bob applies the required correction gates.
6. Bob reconstructs the teleported quantum state.

## Measurement and Correction

| Measurement | Bob's Correction |
|---|---|
| 00 | No correction |
| 01 | Z gate |
| 10 | X gate |
| 11 | X and Z gates |

## Technologies Used
- Python
- Qiskit
- Qiskit Aer
- NumPy
- Matplotlib

## Installation

Install the required libraries:

```bash
pip install -r requirements.txt
```

## How to Run

Run the Python program:

```bash
python teleportation_project_final.py
```

Enter one of the supported measurement results:

- 00
- 01
- 10
- 11

## Output Files

Generated visualizations are saved in the `Teleportation_Output` folder.

| File | Description |
|---|---|
| circuit.png | Teleportation quantum circuit |
| measurement_histogram.png | Measurement distribution |
| bloch_spheres.png | Alice and Bob Bloch spheres |
| alice_bloch_sphere.png | Alice's input state |
| bob_bloch_sphere.png | Bob's output state |

## Simulation Configuration
- Number of qubits: 3
- Number of shots: 1024
- Input state: Equal superposition state

## Conclusion
This project demonstrates the Quantum Teleportation protocol through quantum circuit simulation, showing the role of entanglement, classical measurement, and quantum correction gates.

## Author
## Author
**(kruthikd11)**
# Virtual Camber App

An interactive visualization tool for the **virtual camber transformation** applied to cross-flow turbine (CFT) blades. Given a NACA airfoil and turbine operating conditions, the app maps the rotating blade geometry into an equivalent rectilinear (virtual) frame, revealing the effective camber and angle of attack seen by the blade at each azimuthal position.

## Physics background

A cross-flow turbine blade follows a circular path, so its effective inflow angle changes continuously with azimuthal position θ. The virtual camber transformation is a conformal mapping from the rotating polar frame to a rectilinear frame. In this virtual frame:

- The curved streamline the blade travels along becomes a straight line.
- The symmetric physical airfoil acquires an apparent camber — the **virtual camber**.
- The mapping depends on tip-speed ratio (λ = ωR/U∞) and chord-to-radius ratio (c/R).

## Features

- Real-time plot of the virtually-cambered airfoil profile at any azimuthal angle θ.
- Optional overlay of the camber line and (transformed + virtual) chord lines.
- Angle-of-attack vs. θ curve with a live marker at the current blade position.
- Animate button to sweep θ continuously and watch the virtual shape evolve.
- Save current frame as PNG/PDF/SVG or export a full 360° animation as a GIF.

## Requirements

| Package | Purpose |
|---------|---------|
| Python 3.9+ | |
| NumPy | Airfoil geometry & math |
| Matplotlib | Plotting backend |
| PySide6 | GUI framework |

Install dependencies:

```bash
pip install numpy matplotlib PySide6
```

## Usage

```bash
python virtual_camber_visuals.py
```

Two windows open:

- **Plot** — the virtually-cambered airfoil (left) and the α vs. θ curve (right).
- **Inputs** — controls described below.

### Controls

| Control | Description |
|---------|-------------|
| NACA XXXX | 4-digit NACA profile (e.g. `0018`, `2412`) |
| Tip-Speed Ratio (λ) | ωR/U∞; typical CFT range 1–4 |
| Chord-Radius Ratio (c/R) | Solidity proxy; 0–1 |
| Theta (θ) | Azimuthal blade position in degrees (0–360) |
| Camber line | Toggle camber line overlay |
| Chord line | Toggle transformed and virtual chord lines |
| Animate angle | Continuously sweep θ at ~30 fps |
| Legend | Toggle plot legend |
| Save image | Export current plot (PNG/PDF/SVG) |
| Save animation | Export full rotation as GIF |

## Project context

Developed as part of summer 2026 cross-flow turbine research at the Computational Flow Physics and Modeling Group at the University of Wisconsin–Madison. Python port of analysis originally written by Caelan.

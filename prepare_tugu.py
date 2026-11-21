"""Prepare the supplied Tugu Pahlawan OBJ for the Module 3 pipeline.

The source asset is Z-up and has a large, tiled UV coordinate range. This
script rotates it to Y-up, centers its horizontal footprint, puts the base at
Y=0, and scales its height to 2 world units. Vertex topology and UV indices
are preserved. The source files in data/source/ are never modified.

Run from the Module3 folder:
    python prepare_tugu.py
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "data" / "source" / "monumen_tugu_pahlawan_dan_museum_10_november.obj"
OUTPUT = ROOT / "data" / "mymodel.obj"

# Source coordinates are Z-up. Rotate +Z to +Y while retaining +X.
ROT_Z_UP_TO_Y_UP = np.array([
    [1.0,  0.0, 0.0],
    [0.0,  0.0, 1.0],
    [0.0, -1.0, 0.0],
])


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source OBJ not found: {SOURCE}")

    lines = SOURCE.read_text(encoding="utf-8", errors="replace").splitlines()
    positions: list[list[float]] = []
    for line in lines:
        if line.startswith("v "):
            values = [float(v) for v in line.split()[1:4]]
            positions.append(values)

    if not positions:
        raise ValueError("The source OBJ contains no vertex records ('v').")

    raw = np.asarray(positions, dtype=np.float64)
    rotated = (ROT_Z_UP_TO_Y_UP @ raw.T).T
    lo = rotated.min(axis=0)
    hi = rotated.max(axis=0)
    height = float(hi[1] - lo[1])
    if height <= 1e-9:
        raise ValueError("The source model has no measurable vertical extent after axis conversion.")

    scale_factor = 2.0 / height
    center_x = float((lo[0] + hi[0]) * 0.5)
    center_z = float((lo[2] + hi[2]) * 0.5)

    def transform_point(p: np.ndarray) -> np.ndarray:
        q = ROT_Z_UP_TO_Y_UP @ p
        q = np.array([q[0] - center_x, q[1] - lo[1], q[2] - center_z])
        return q * scale_factor

    def transform_normal(n: np.ndarray) -> np.ndarray:
        q = ROT_Z_UP_TO_Y_UP @ n
        length = np.linalg.norm(q)
        return q / length if length > 1e-12 else q

    output_lines: list[str] = [
        "# Module 3 Lab 1 - Tugu Pahlawan, prepared from the supplied OBJ",
        "# Axis converted Z-up -> Y-up; centered on X/Z; base Y=0; height=2.0 units",
        "# Geometry topology and all UV indices are preserved.",
    ]

    for line in lines:
        if line.startswith("mtllib "):
            output_lines.append("mtllib mymodel.mtl")
        elif line.startswith("v "):
            p = np.array([float(v) for v in line.split()[1:4]], dtype=np.float64)
            q = transform_point(p)
            output_lines.append("v " + " ".join(f"{v:.9f}" for v in q))
        elif line.startswith("vn "):
            n = np.array([float(v) for v in line.split()[1:4]], dtype=np.float64)
            q = transform_normal(n)
            output_lines.append("vn " + " ".join(f"{v:.9f}" for v in q))
        else:
            output_lines.append(line)

    OUTPUT.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

    new = np.asarray([transform_point(p) for p in raw])
    print(f"Source OBJ : {SOURCE.relative_to(ROOT)}")
    print(f"Output OBJ : {OUTPUT.relative_to(ROOT)}")
    print(f"Vertices   : {len(raw):,}")
    print(f"Scale      : {scale_factor:.9f}")
    print(f"Source bounds (XYZ): min={raw.min(axis=0)}, max={raw.max(axis=0)}")
    print(f"Prepared bounds (XYZ): min={new.min(axis=0)}, max={new.max(axis=0)}")
    print("UV coordinates and face indices: preserved")


if __name__ == "__main__":
    main()

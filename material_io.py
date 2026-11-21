"""Minimal MTL + PNG material reader. Pillow is used only for image I/O.
The renderer's transformations, clipping, rasterisation, sampling and ray
intersection remain implemented with NumPy.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image


def read_mtl(path: str | Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    materials: dict[str, dict] = {}
    current = None
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, *rest = line.split(maxsplit=1)
        value = rest[0] if rest else ""
        if key == "newmtl":
            current = value.strip()
            materials[current] = {"Kd": (0.7, 0.7, 0.7), "map_Kd": None}
        elif current is not None and key == "Kd":
            vals = tuple(float(x) for x in value.split()[:3])
            if len(vals) == 3:
                materials[current]["Kd"] = vals
        elif current is not None and key == "map_Kd":
            materials[current]["map_Kd"] = value.strip().split()[-1]
    return materials


def load_materials(obj_path: str | Path):
    """Return (textures, colors, metadata) indexed by material name."""
    obj_path = Path(obj_path)
    mtl_path = None
    for raw in obj_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.strip().startswith("mtllib "):
            mtl_path = obj_path.parent / raw.strip().split(maxsplit=1)[1]
            break
    if mtl_path is None:
        candidate = obj_path.with_suffix(".mtl")
        mtl_path = candidate if candidate.exists() else None
    materials = read_mtl(mtl_path) if mtl_path else {}
    textures: dict[str, np.ndarray] = {}
    colors: dict[str, tuple[float, float, float]] = {}
    for name, mat in materials.items():
        colors[name] = tuple(mat.get("Kd", (0.7, 0.7, 0.7)))
        texture_name = mat.get("map_Kd")
        if texture_name:
            image_path = (mtl_path.parent / texture_name).resolve()
            if not image_path.exists():
                # Some exporters write only a basename despite a nested path.
                image_path = obj_path.parent / Path(texture_name).name
            if image_path.exists():
                with Image.open(image_path) as im:
                    textures[name] = np.asarray(im.convert("RGB"), dtype=np.uint8)
    meta = {"mtl_path": str(mtl_path) if mtl_path else None,
            "material_count": len(materials),
            "textured_materials": sorted(textures),
            "materials": materials}
    return textures, colors, meta
